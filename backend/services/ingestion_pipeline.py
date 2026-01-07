"""
Unified Ingestion Pipeline.

This is the centralized processing pipeline that ALL data sources use.
Connectors only fetch raw content - this pipeline handles everything else:
- Validation & quota checks
- Progress tracking & notifications  
- Content parsing & chunking
- Embedding generation
- Vector storage
- Error handling & cleanup
"""

import logging
import tempfile
import os
from typing import AsyncIterator, Optional, Callable, Dict, Any
from uuid import UUID

from connectors.enhanced import SourceDocument, SourceType, QuotaExceededError, FileTooLargeError
from services.usage import check_can_upload
from services.parsers import DocumentProcessorFactory
from services.embeddings import generate_embeddings_batch
from core.db import get_supabase
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Constants
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
STAGING_BUCKET = "ephemeral-staging"


class IngestionPipeline:
    """
    Unified ingestion pipeline for ALL data sources.
    
    Usage:
        pipeline = IngestionPipeline(user_id, job_id, supabase)
        result = await pipeline.process_stream(document_stream, "google_drive")
    """
    
    def __init__(
        self,
        user_id: str,
        job_id: str,
        supabase_client,
        progress_callback: Optional[Callable] = None
    ):
        self.user_id = user_id
        self.job_id = job_id
        self.supabase = supabase_client
        self.progress_callback = progress_callback
        
        # Metrics
        self.total_docs = 0
        self.processed_docs = 0
        self.failed_docs = 0
        self.total_chunks = 0
        self.total_bytes = 0
    
    async def process_stream(
        self,
        document_stream: AsyncIterator[SourceDocument],
        source_type: str
    ) -> Dict[str, Any]:
        """
        Process a stream of documents through the full pipeline.
        
        Args:
            document_stream: Async iterator of SourceDocument
            source_type: Type of source ('file_upload', 'google_drive', etc.)
            
        Returns:
            Dict with processing results
        """
        import asyncio
        from asyncio import Semaphore
        
        logger.info(f"[Pipeline:{self.job_id}] Starting ingestion from {source_type}")
        
        # STEP 1: Initialize job
        self._update_job_status("processing", 0, f"Starting {source_type} ingestion...")
        self._create_notification(
            "Processing Started",
            f"Ingesting documents from {source_type.replace('_', ' ').title()}",
            "info"
        )
        
        # STEP 2: Collect documents (for accurate progress)
        documents = []
        try:
            async for doc in document_stream:
                documents.append(doc)
        except Exception as e:
            logger.error(f"[Pipeline:{self.job_id}] Failed to fetch documents: {e}")
            self._update_job_status("failed", 0, f"Failed to fetch: {str(e)}")
            self._create_notification(
                "Ingestion Failed",
                f"Failed to fetch documents: {str(e)}",
                "error"
            )
            raise
        
        self.total_docs = len(documents)
        logger.info(f"[Pipeline:{self.job_id}] Processing {self.total_docs} documents")
        
        if self.total_docs == 0:
            self._update_job_status("completed", 100, "No documents to process")
            return {
                "status": "completed",
                "message": "No documents to process",
                "total": 0,
                "processed": 0,
                "failed": 0
            }
        
        # Update job with total count
        self._update_job_total(self.total_docs)
        
        # STEP 3: Process documents in parallel with concurrency limit
        # Concurrency limit prevents overwhelming external APIs (LlamaParse, OpenAI)
        CONCURRENCY_LIMIT = 3
        semaphore = Semaphore(CONCURRENCY_LIMIT)
        
        async def process_with_limit(doc: SourceDocument, doc_number: int):
            """Process single document with concurrency control."""
            async with semaphore:
                try:
                    logger.info(f"[Pipeline:{self.job_id}] Processing {doc_number}/{self.total_docs}: {doc.filename}")
                    result = await self._process_single_document(doc, doc_number)
                    self.processed_docs += 1
                    return {"status": "success", "doc": doc, "result": result}
                    
                except QuotaExceededError as e:
                    logger.warning(f"[Pipeline:{self.job_id}] Quota exceeded: {e}")
                    self.failed_docs += 1
                    self._create_notification(
                        "Quota Exceeded",
                        str(e),
                        "warning"
                    )
                    return {"status": "quota_exceeded", "doc": doc, "error": str(e)}
                    
                except Exception as e:
                    logger.error(f"[Pipeline:{self.job_id}] Failed to process {doc.filename}: {e}")
                    self.failed_docs += 1
                    self._create_notification(
                        "Document Failed",
                        f"Failed to process {doc.filename}: {str(e)}",
                        "error"
                    )
                    return {"status": "failed", "doc": doc, "error": str(e)}
                
                finally:
                    # Update progress after each document
                    progress = int((self.processed_docs + self.failed_docs) / self.total_docs * 100)
                    self._update_job_status(
                        "processing",
                        progress,
                        f"Processed {self.processed_docs + self.failed_docs}/{self.total_docs} documents"
                    )
        
        # Process all documents in parallel
        tasks = [process_with_limit(doc, i + 1) for i, doc in enumerate(documents)]
        results = await asyncio.gather(*tasks, return_exceptions=False)
        
        # Check if we should stop (quota exceeded)
        if any(r.get("status") == "quota_exceeded" for r in results):
            logger.warning(f"[Pipeline:{self.job_id}] Stopping due to quota exceeded")
        
        # STEP 4: Finalize
        final_status = "completed" if self.failed_docs == 0 else "partial"
        self._update_job_status(final_status, 100, "Processing complete")
        
        success_msg = f"Processed {self.processed_docs}/{self.total_docs} documents ({self.total_chunks} chunks)"
        self._create_notification(
            "Processing Complete",
            success_msg,
            "success" if self.failed_docs == 0 else "warning"
        )
        
        logger.info(f"[Pipeline:{self.job_id}] Complete: {success_msg}")
        
        return {
            "status": final_status,
            "total": self.total_docs,
            "processed": self.processed_docs,
            "failed": self.failed_docs,
            "chunks": self.total_chunks,
            "bytes": self.total_bytes
        }
    
    
    async def _process_single_document(
        self, 
        doc: SourceDocument, 
        doc_number: int
    ) -> Dict[str, Any]:
        """Process a single document through the pipeline."""
        import time
        
        # Create file status tracker
        file_status_id = self._create_file_status(doc)
        local_path = None
        start_time = time.time()
        
        try:
            # STEP 1: Validate & quota check
            self._update_file_status(file_status_id, "uploading", 5, "Validating file...")
            await self._validate_document(doc)
            
            # STEP 2: Write to temp file
            self._update_file_status(file_status_id, "uploading", 15, "Preparing file...")
            local_path = self._write_to_temp(doc)
            
            # STEP 3: Parse & chunk
            self._update_file_status(file_status_id, "parsing", 25, "Extracting content (this may take 30-90s for PDFs)...")
            parse_start = time.time()
            chunks = await self._parse_and_chunk(local_path, doc.filename)
            parse_time = int(time.time() - parse_start)
            
            if not chunks:
                self._update_file_status(file_status_id, "skipped", 100,
                    message=f"No content extracted (completed in {parse_time}s)", chunks_total=0)
                return {"status": "skipped", "reason": "empty"}
            
            # Update: Chunking complete, starting embedding
            self._update_chunk_progress(
                file_status_id=file_status_id,
                chunks_processed=0,
                chunks_total=len(chunks),
                current_stage="chunking"
            )
            
            # STEP 4: Generate embeddings
            self._update_file_status(file_status_id, "embedding", 50, 
                f"Generating embeddings for {len(chunks)} chunks (est. {len(chunks)//100 * 2}s)...")
            embed_start = time.time()
            embeddings = await self._generate_embeddings(chunks)
            embed_time = int(time.time() - embed_start)
            
            # Update: Embedding complete, starting indexing
            self._update_chunk_progress(
                file_status_id=file_status_id,
                chunks_processed=len(chunks),
                chunks_total=len(chunks),
                current_stage="embedding"
            )
            
            # STEP 5: Store in database (atomic)
            self._update_file_status(file_status_id, "indexing", 75, "Storing in database...")
            
            # Update: Starting indexing
            self._update_chunk_progress(
                file_status_id=file_status_id,
                chunks_processed=len(chunks),
                chunks_total=len(chunks),
                current_stage="indexing"
            )
            
            doc_id = await self._store_document(doc, chunks, embeddings)
            
            # STEP 6: Success
            total_time = int(time.time() - start_time)
            self._update_file_status(file_status_id, "completed", 100,
                message=f"✅ Completed in {total_time}s (parse: {parse_time}s, embed: {embed_time}s)", 
                chunks_total=len(chunks))
            
            self.total_chunks += len(chunks)
            self.total_bytes += doc.size_bytes
            
            logger.info(f"[Pipeline] Processed {doc.filename}: {len(chunks)} chunks in {total_time}s")
            
            return {
                "status": "success",
                "doc_id": doc_id,
                "chunks": len(chunks),
                "time": total_time
            }
            
        except Exception as e:
            self._update_file_status(file_status_id, "failed", 0,
                message=f"❌ {str(e)}")
            raise
            
        finally:
            # Cleanup temp file
            if local_path and os.path.exists(local_path):
                try:
                    os.unlink(local_path)
                except Exception as e:
                    logger.warning(f"[Pipeline] Failed to delete temp file {local_path}: {e}")
    
    async def _validate_document(self, doc: SourceDocument):
        """Validate document size, type, quota."""
        
        # Check file size
        if doc.size_bytes > MAX_FILE_SIZE:
            raise FileTooLargeError(
                f"File '{doc.filename}' exceeds maximum size of {MAX_FILE_SIZE / 1024 / 1024}MB"
            )
        
        # Check quota
        quota = await check_can_upload(
            UUID(self.user_id), 
            doc.size_bytes,
            file_count=1
        )
        
        if not quota["allowed"]:
            raise QuotaExceededError(quota["reason"])
    
    def _write_to_temp(self, doc: SourceDocument) -> str:
        """Write document content to temporary file."""
        file_ext = os.path.splitext(doc.filename)[1] if doc.filename else ""
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp:
            if isinstance(doc.content, bytes):
                tmp.write(doc.content)
            else:
                tmp.write(doc.content.encode('utf-8'))
            return tmp.name
    
    async def _parse_and_chunk(self, file_path: str, filename: str) -> list:
        """Parse document and create chunks."""
        result = DocumentProcessorFactory.process(
            file_path=file_path,
            filename=filename
        )
        return result.chunks
    
    async def _generate_embeddings(self, chunks: list) -> list:
        """Generate embeddings for chunks with timeout protection."""
        from core.resilience import with_timeout, Timeouts
        
        chunk_texts = [chunk.content for chunk in chunks]
        
        # Generate embeddings with timeout
        embeddings = await with_timeout(
            generate_embeddings_batch(chunk_texts),
            Timeouts.EMBEDDING_BATCH * len(chunk_texts) / 100,  # Scale timeout by batch count
            f"Generating {len(chunk_texts)} embeddings"
        )
        
        return embeddings
    
    async def _store_document(self, doc: SourceDocument, chunks, embeddings) -> str:
        """Store document and chunks atomically using RPC."""
        # Prepare chunks for RPC
        chunks_data = []
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            chunks_data.append({
                "content": chunk.content,
                "embedding": embedding,
                "metadata": {
                    **chunk.metadata,
                    "chunk_index": i,
                    "source_id": doc.source_id,
                    "source_type": doc.source_type.value
                }
            })
        
        # Call RPC with parameters matching database function signature exactly
        # Function: ingest_document_with_chunks(p_user_id, p_doc_title, p_source_type, p_source_url, p_metadata, p_chunks, p_file_size_bytes)
        result = self.supabase.rpc("ingest_document_with_chunks", {
            "p_user_id": self.user_id,
            "p_doc_title": doc.filename,  # Database expects p_doc_title (not p_filename)
            "p_source_type": doc.source_type.value,
            "p_source_url": doc.metadata.get("source_url", ""),  # Required parameter
            "p_metadata": doc.metadata,  # Database expects p_metadata (not p_source_metadata)
            "p_chunks": chunks_data,
            "p_file_size_bytes": doc.size_bytes
        }).execute()
        
        if not result.data:
            raise Exception("Failed to store document")
        
        return result.data[0]["document_id"]
    
    # Helper methods for status tracking
    def _update_job_status(self, status: str, progress: int, message: str = ""):
        """Update job status in database."""
        try:
            self.supabase.table("ingestion_jobs").update({
                "status": status,
                "progress": progress,
                "status_message": message,
                "processed_files": self.processed_docs,
                "failed_files": self.failed_docs
            }).eq("id", self.job_id).execute()
        except Exception as e:
            logger.warning(f"[Pipeline] Failed to update job status: {e}")
    
    def _update_job_total(self, total: int):
        """Update total file count."""
        try:
            self.supabase.table("ingestion_jobs").update({
                "total_files": total
            }).eq("id", self.job_id).execute()
        except Exception as e:
            logger.warning(f"[Pipeline] Failed to update job total: {e}")
    
    def _create_file_status(self, doc: SourceDocument) -> str:
        """Create file status tracker."""
        try:
            result = self.supabase.table("ingestion_file_status").insert({
                "job_id": self.job_id,
                "user_id": self.user_id,
                "filename": doc.filename,
                "file_size_bytes": doc.size_bytes,  # Correct column name from database schema
                "status": "pending",
                "progress": 0
            }).execute()
            return result.data[0]["id"]
        except Exception as e:
            logger.warning(f"[Pipeline] Failed to create file status: {e}")
            return ""
    
    def _update_file_status(self, file_id: str, status: str, progress: int, message: str = "", **kwargs):
        """Update file status."""
        if not file_id:
            return
        
        try:
            update_data = {
                "status": status,
                "progress": progress,
                "status_message": message,
                **kwargs
            }
            self.supabase.table("ingestion_file_status").update(update_data).eq("id", file_id).execute()
        except Exception as e:
            logger.warning(f"[Pipeline] Failed to update file status: {e}")
    
    def _update_chunk_progress(
        self,
        file_status_id: str,
        chunks_processed: int,
        chunks_total: int,
        current_stage: str = "embedding"
    ):
        """
        Update chunk processing progress with stage information.
        
        Provides real-time updates for UI progress bars showing:
        - Current chunk being processed
        - Total chunks
        - Processing stage (parsing, chunking, embedding, indexing)
        - Calculated progress percentage
        
        Args:
            file_status_id: File status record ID
            chunks_processed: Number of chunks processed so far
            chunks_total: Total number of chunks for this file
            current_stage: Current processing stage
        """
        if not file_status_id:
            return
        
        try:
            # Calculate progress percentage
            progress = int((chunks_processed / chunks_total) * 100) if chunks_total > 0 else 0
            
            # Determine status based on stage
            status_map = {
                "parsing": "parsing",
                "chunking": "parsing",
                "embedding": "embedding",
                "indexing": "indexing"
            }
            status = status_map.get(current_stage, "parsing")
            
            # Create detailed status message
            stage_labels = {
                "parsing": "Parsing document",
                "chunking": "Splitting into chunks",
                "embedding": f"Embedding chunk {chunks_processed}/{chunks_total}",
                "indexing": f"Indexing chunk {chunks_processed}/{chunks_total}"
            }
            message = stage_labels.get(current_stage, f"Processing chunk {chunks_processed}/{chunks_total}")
            
            # Update database with chunk progress
            self.supabase.table("ingestion_file_status").update({
                "status": status,
                "progress": progress,
                "chunks_processed": chunks_processed,
                "chunks_total": chunks_total,
                "status_message": message,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }).eq("id", file_status_id).execute()
            
            logger.debug(
                f"📊 [Pipeline] Chunk progress: {chunks_processed}/{chunks_total} "
                f"({progress}%) - {current_stage}"
            )
            
        except Exception as e:
            logger.warning(f"[Pipeline] Failed to update chunk progress: {e}")
    
    def _create_notification(self, title: str, message: str, type: str):
        """Create user notification."""
        try:
            self.supabase.table("notifications").insert({
                "user_id": self.user_id,
                "title": title,
                "message": message,
                "type": type,
                "metadata": {"job_id": self.job_id}
            }).execute()
        except Exception as e:
            logger.warning(f"[Pipeline] Failed to create notification: {e}")

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
from core.hashing import compute_content_hash
from core.ingestion_utils import normalize_source_type

logger = logging.getLogger(__name__)

# Constants
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
STAGING_BUCKET = "ephemeral-staging"


def _sanitize_text(value: str) -> str:
    if not value:
        return value
    if "\x00" in value:
        return value.replace("\x00", "")
    return value


async def get_embeddings(texts, token_counts=None):
    return await generate_embeddings_batch(texts, token_counts=token_counts)


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
        self.supabase = supabase_client or get_supabase()
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
        source_type: str = "file_upload"
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
        
        source_type = normalize_source_type(source_type) or source_type
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
        if self.failed_docs == 0:
            final_status = "completed"
        elif self.processed_docs > 0:
            final_status = "completed"
        else:
            final_status = "failed"

        status_parts = [f"Processed {self.processed_docs}/{self.total_docs} documents"]
        if self.failed_docs:
            status_parts.append(f"{self.failed_docs} failed")
        if self.total_chunks:
            status_parts.append(f"{self.total_chunks} chunks")
        success_msg = ", ".join(status_parts)

        self._update_job_status(final_status, 100, success_msg)

        if final_status == "failed":
            notification_type = "error"
        elif self.failed_docs > 0:
            notification_type = "warning"
        else:
            notification_type = "success"

        self._create_notification(
            "Processing Complete" if final_status != "failed" else "Processing Failed",
            success_msg,
            notification_type
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
            result = await self._parse_and_chunk(local_path, doc.filename)
            parse_time = int(time.time() - parse_start)

            file_type = getattr(result, "file_type", None)
            result_metadata = getattr(result, "metadata", None) or {}

            if file_type == "unsupported":
                reason = result_metadata.get("unsupported_reason")
                message = "Unsupported file type"
                if reason == "binary_content":
                    message = "Unsupported binary file"
                self._update_file_status(
                    file_status_id,
                    "skipped",
                    100,
                    message=f"{message} (completed in {parse_time}s)",
                    chunks_total=0,
                )
                return {"status": "skipped", "reason": reason or "unsupported"}

            chunks = result.chunks

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
            embeddings, chunk_texts = await self._generate_embeddings(chunks)
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
            
            doc_id = await self._store_document(doc, chunks, embeddings, chunk_texts)
            
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
        quota = await self._check_quota(doc)
        if not quota["allowed"]:
            raise QuotaExceededError(quota["reason"])

    async def _check_quota(self, doc: SourceDocument) -> Dict[str, Any]:
        return await check_can_upload(
            UUID(self.user_id),
            doc.size_bytes,
            file_count=1
        )
    
    def _write_to_temp(self, doc: SourceDocument) -> str:
        """Write document content to temporary file."""
        file_ext = os.path.splitext(doc.filename)[1] if doc.filename else ""
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp:
            if isinstance(doc.content, bytes):
                tmp.write(doc.content)
            else:
                tmp.write(doc.content.encode('utf-8'))
            return tmp.name
    
    async def _parse_and_chunk(self, file_path: str, filename: str):
        """Parse document and return processed result."""
        return DocumentProcessorFactory.process(
            file_path=file_path,
            filename=filename
        )
    
    async def _generate_embeddings(self, chunks: list):
        """Generate embeddings for chunks with timeout protection."""
        from core.resilience import with_timeout, Timeouts
        
        chunk_texts = [_sanitize_text(chunk.content) for chunk in chunks]
        token_counts = [chunk.token_count for chunk in chunks]
        
        # Generate embeddings with timeout
        embeddings = await with_timeout(
            get_embeddings(chunk_texts, token_counts=token_counts),
            Timeouts.EMBEDDING_BATCH * len(chunk_texts) / 100,  # Scale timeout by batch count
            f"Generating {len(chunk_texts)} embeddings"
        )
        
        return embeddings, chunk_texts
    
    async def _store_document(self, doc: SourceDocument, chunks, embeddings, chunk_texts) -> str:
        """Store document and chunks using batched inserts (idempotent)."""
        from worker.tasks import ingest_document_batched

        raw_source_type = doc.source_type.value if hasattr(doc.source_type, "value") else str(doc.source_type)
        source_type = normalize_source_type(raw_source_type) or raw_source_type

        doc_metadata = {
            **(doc.metadata or {}),
            "source_id": doc.source_id,
            "source_type": source_type,
        }

        chunks_data = []
        for i, (chunk, embedding, chunk_text) in enumerate(zip(chunks, embeddings, chunk_texts)):
            if embedding is None:
                continue
            chunks_data.append({
                "content": chunk_text,
                "embedding": embedding,
                "chunk_index": i,
                "metadata": {
                    **chunk.metadata,
                    "chunk_index": i,
                },
            })

        if isinstance(doc.content, bytes):
            content_bytes = doc.content
        else:
            content_bytes = (doc.content or "").encode("utf-8")

        content_hash = compute_content_hash(content_bytes) if content_bytes else None

        doc_id = ingest_document_batched(
            supabase=self.supabase,
            user_id=self.user_id,
            doc_title=doc.filename,
            source_type=source_type,
            metadata=doc_metadata,
            chunks_payload=chunks_data,
            file_size_bytes=doc.size_bytes,
            source_url=doc_metadata.get("source_url", ""),
            content_hash=content_hash,
        )

        if not doc_id:
            raise Exception("Failed to store document")

        return doc_id
    
    # Helper methods for status tracking
    def _update_job_status(self, status: str, progress: int, message: str = ""):
        """Update job status in database."""
        try:
            self.supabase.table("ingestion_jobs").update({
                "status": status,
                "progress": progress,
                "message": message,
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

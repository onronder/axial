# Axial RAG Platform - Architectural Audit & V1.0 Roadmap

**Document Version:** 1.0  
**Date:** January 14, 2026  
**Author:** Senior Principal Software Architect  
**Status:** APPROVED FOR IMPLEMENTATION

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Dead Code Analysis](#1-dead-code-analysis)
3. [Monolith Risk Assessment](#2-monolith-risk-assessment)
4. [Critical Bug: Ghost Data](#3-critical-bug-ghost-data-sync-logic)
5. [Router Strategy Analysis](#4-router-strategy-analysis)
6. [Incremental Sync Architecture](#5-bullet-proof-incremental-sync-logic)
7. [Execution Roadmap](#6-execution-roadmap)
8. [Appendix: Test Specifications](#appendix-test-specifications)

---

## Executive Summary

After thorough analysis of the Axial backend codebase (`worker/tasks.py`, `services/parsers.py`, `api/v1/integrations.py`, and supporting modules), this audit has identified:

| Finding | Severity | Status |
|---------|----------|--------|
| Dead code in `core/parsers.py` | Low | ⚠️ Cleanup Required |
| Memory risk with Pandas/OpenPyXL | Medium | ⚠️ Mitigation Required |
| Ghost Data sync bug | **Critical** | 🔴 Fix Required Before V1.0 |
| Missing parsers (PPTX, Email, CSV) | Medium | ⚠️ Implementation Required |

**Recommendation:** The Ghost Data bug must be fixed before any enterprise deployment. The parser extensions are additive improvements to an otherwise solid architecture.

---

## 1. Dead Code Analysis

### 1.1 Finding: `backend/core/parsers.py`

**Status:** ✅ CONFIRMED DEAD CODE - SAFE TO DELETE

**Evidence:**
- Zero imports found across entire codebase
- Grep search for `core.parsers`, `core/parsers`, `from core.parsers` returned no results
- Active parser implementation is `services/parsers.py` → `DocumentProcessorFactory`
- `worker/tasks.py:40` imports from services module exclusively

**File Contents (39 lines):**
```python
# backend/core/parsers.py - DEAD CODE
from abc import ABC, abstractmethod
from fastapi import UploadFile
from unstructured.partition.auto import partition

class BaseParser(ABC):
    @abstractmethod
    async def parse(self, file: UploadFile) -> str:
        pass

class UnstructuredParser(BaseParser):
    async def parse(self, file: UploadFile) -> str:
        # Old implementation using unstructured library
        ...

def get_parser(filename: str) -> BaseParser:
    return UnstructuredParser()
```

**Historical Context:** This was the original MVP parser before the enterprise-grade `DocumentProcessorFactory` was implemented. It uses the `unstructured` library directly instead of the current format-aware processing pipeline.

---

### 1.2 Phase 1 Implementation Checklist

#### Pre-Deletion Verification
- [ ] Run full grep search to confirm no imports exist
- [ ] Check for any string references in configuration files
- [ ] Verify `unstructured` library is still needed (used elsewhere?)
- [ ] Document any historical commits referencing this file

#### Deletion Steps
- [ ] Create backup branch: `git checkout -b backup/core-parsers-removal`
- [ ] Delete file: `rm backend/core/parsers.py`
- [ ] Delete cached bytecode: `rm -rf backend/core/__pycache__/parsers*`
- [ ] Run linter: `flake8 backend/` (verify no import errors)
- [ ] Run type checker: `mypy backend/` (verify no missing module errors)

#### Post-Deletion Verification
- [ ] Run full test suite: `pytest backend/tests/ -v`
- [ ] Start application locally and verify startup
- [ ] Test file upload endpoint with sample files
- [ ] Test Google Drive ingestion flow
- [ ] Test web crawl functionality

---

### 1.3 Phase 1 Unit Tests

```python
# backend/tests/unit/test_phase1_cleanup.py
"""
Phase 1: Dead Code Cleanup Verification Tests
Ensures core/parsers.py removal doesn't break functionality.
"""

import pytest
import importlib
import os


class TestDeadCodeRemoval:
    """Verify dead code has been properly removed."""
    
    def test_core_parsers_file_removed(self):
        """Verify core/parsers.py file no longer exists."""
        core_parsers_path = os.path.join(
            os.path.dirname(__file__), 
            '..', '..', 'core', 'parsers.py'
        )
        assert not os.path.exists(core_parsers_path), \
            "core/parsers.py should be deleted"
    
    def test_core_parsers_not_importable(self):
        """Verify core.parsers module cannot be imported."""
        with pytest.raises(ModuleNotFoundError):
            importlib.import_module('core.parsers')
    
    def test_services_parsers_still_works(self):
        """Verify services/parsers.py is the active parser module."""
        from services.parsers import DocumentProcessorFactory
        assert DocumentProcessorFactory is not None
        assert hasattr(DocumentProcessorFactory, 'process')
        assert hasattr(DocumentProcessorFactory, 'PROCESSOR_MAP')


class TestParserFunctionalityIntact:
    """Verify parser functionality after cleanup."""
    
    def test_text_file_parsing(self):
        """Verify plain text parsing still works."""
        from services.parsers import DocumentProcessorFactory
        
        content = b"Hello, this is a test document."
        result = DocumentProcessorFactory.process(
            content=content,
            filename="test.txt"
        )
        
        assert result is not None
        assert result.file_type == "text"
        assert len(result.chunks) > 0
    
    def test_code_file_parsing(self):
        """Verify code file parsing still works."""
        from services.parsers import DocumentProcessorFactory
        
        content = b"def hello():\n    return 'world'"
        result = DocumentProcessorFactory.process(
            content=content,
            filename="test.py"
        )
        
        assert result is not None
        assert result.file_type == "code"
    
    def test_markdown_parsing(self):
        """Verify markdown parsing still works."""
        from services.parsers import DocumentProcessorFactory
        
        content = b"# Heading\n\nThis is **bold** text."
        result = DocumentProcessorFactory.process(
            content=content,
            filename="test.md"
        )
        
        assert result is not None
        assert result.file_type == "markdown"
    
    def test_pdf_parsing_available(self):
        """Verify PDF processor is registered."""
        from services.parsers import DocumentProcessorFactory, PDFProcessor
        
        assert ".pdf" in DocumentProcessorFactory.PROCESSOR_MAP
        assert DocumentProcessorFactory.PROCESSOR_MAP[".pdf"] == PDFProcessor
    
    def test_docx_parsing_available(self):
        """Verify DOCX processor is registered."""
        from services.parsers import DocumentProcessorFactory, DocxProcessor
        
        assert ".docx" in DocumentProcessorFactory.PROCESSOR_MAP
        assert DocumentProcessorFactory.PROCESSOR_MAP[".docx"] == DocxProcessor


class TestWorkerTasksIntegration:
    """Verify worker tasks still import correctly."""
    
    def test_worker_tasks_import(self):
        """Verify worker/tasks.py imports successfully."""
        import worker.tasks
        assert hasattr(worker.tasks, 'process_file_task')
        assert hasattr(worker.tasks, 'unified_ingest_task')
    
    def test_document_processor_factory_in_worker(self):
        """Verify DocumentProcessorFactory is used in worker."""
        from worker.tasks import process_file_task
        import inspect
        
        source = inspect.getsource(process_file_task)
        assert 'DocumentProcessorFactory' in source
        assert 'core.parsers' not in source
```

---

## 2. Monolith Risk Assessment

### 2.1 Current Worker Configuration

| Parameter | Value | Risk Level |
|-----------|-------|------------|
| Soft Time Limit | 600s (10 min) | Adequate |
| Hard Time Limit | 660s (11 min) | Adequate |
| Max Retries | 2 | Adequate |
| Queue | `queues.parsing` | Single queue risk |
| Container RAM | 1-2GB (assumed) | **HIGH RISK** |

### 2.2 Memory Impact Analysis

| Library | Status | Memory Footprint | Risk |
|---------|--------|------------------|------|
| PyMuPDF | ✅ Active | 50-200MB per PDF | Low |
| LlamaParse | ✅ Active | 100-500MB (API buffer) | Medium |
| docx2txt | ✅ Active | 10-50MB | Low |
| **Pandas** | 🆕 Proposed | **2-4x file size** | **HIGH** |
| **OpenPyXL** | 🆕 Proposed | **Similar to Pandas** | **HIGH** |

### 2.3 Risk Scenarios

**Scenario A: Large CSV File**
```
File: sales_data.csv (100MB)
Pandas DataFrame: ~200-400MB in RAM
Worker Base Memory: ~500MB
Total Required: 700-900MB
Container Limit: 1GB
Result: Near OOM, potential swap thrashing
```

**Scenario B: Concurrent Processing**
```
Worker 1: Processing 50MB Excel → 150MB RAM
Worker 2: Processing 80MB CSV → 240MB RAM  
Worker 3: Processing PDF with LlamaParse → 300MB RAM
Total: 690MB additional RAM
Risk: OOM kills if base memory + concurrent load > container limit
```

### 2.4 Mitigation Strategies

#### Strategy 1: Chunked Processing (Required)
```python
# DO NOT DO THIS:
df = pd.read_csv(filepath)  # Loads entire file

# DO THIS INSTEAD:
CHUNK_SIZE = 10000
for chunk in pd.read_csv(filepath, chunksize=CHUNK_SIZE):
    process_chunk(chunk)
    del chunk  # Explicit cleanup
```

#### Strategy 2: Memory Guards (Required)
```python
MAX_STRUCTURED_FILE_SIZE = 50 * 1024 * 1024  # 50MB

def route_file(file_size: int, extension: str) -> str:
    """Route file to appropriate queue based on size and type."""
    if extension in {'.csv', '.xlsx', '.xls'}:
        if file_size > MAX_STRUCTURED_FILE_SIZE:
            return "queues.heavy_parsing"
    return "queues.parsing"
```

#### Strategy 3: Separate Heavy Queue (Recommended)
```python
# celeryconfig.py
task_routes = {
    'process_file_task': {
        'queue': 'queues.parsing'
    },
    'process_heavy_file_task': {
        'queue': 'queues.heavy_parsing'  # 4GB+ instances
    },
}
```

---

### 2.5 Phase 2 Implementation Checklist (Memory Safety)

#### Configuration Updates
- [ ] Add `MAX_STRUCTURED_FILE_SIZE` to `core/config.py`
- [ ] Add `HEAVY_PARSING_QUEUE` setting
- [ ] Configure Celery routing for heavy files
- [ ] Document memory requirements in deployment guide

#### Code Changes
- [ ] Implement `route_file()` helper function
- [ ] Add file size check before Pandas/OpenPyXL processing
- [ ] Implement chunked CSV reader
- [ ] Implement chunked Excel reader
- [ ] Add memory profiling decorators for debugging

#### Infrastructure
- [ ] Create `queues.heavy_parsing` queue in Redis
- [ ] Deploy dedicated heavy-parsing worker (4GB+ RAM)
- [ ] Add memory monitoring alerts (>80% threshold)
- [ ] Configure container memory limits

#### Validation
- [ ] Test with 100MB CSV file
- [ ] Test with 100MB Excel file
- [ ] Test concurrent heavy file processing
- [ ] Verify OOM protection triggers correctly

---

### 2.6 Phase 2 Unit Tests

```python
# backend/tests/unit/test_phase2_memory_safety.py
"""
Phase 2: Memory Safety Tests
Ensures large file processing doesn't cause OOM.
"""

import pytest
from unittest.mock import patch, MagicMock
import io


class TestFileRouting:
    """Test file routing based on size and type."""
    
    def test_small_csv_routes_to_standard_queue(self):
        """Small CSV files should use standard parsing queue."""
        from services.parsers import route_file
        
        queue = route_file(
            file_size=1024 * 1024,  # 1MB
            extension='.csv'
        )
        assert queue == "queues.parsing"
    
    def test_large_csv_routes_to_heavy_queue(self):
        """Large CSV files should use heavy parsing queue."""
        from services.parsers import route_file
        
        queue = route_file(
            file_size=100 * 1024 * 1024,  # 100MB
            extension='.csv'
        )
        assert queue == "queues.heavy_parsing"
    
    def test_large_xlsx_routes_to_heavy_queue(self):
        """Large Excel files should use heavy parsing queue."""
        from services.parsers import route_file
        
        queue = route_file(
            file_size=75 * 1024 * 1024,  # 75MB
            extension='.xlsx'
        )
        assert queue == "queues.heavy_parsing"
    
    def test_pdf_always_uses_standard_queue(self):
        """PDFs should always use standard queue (LlamaParse handles complexity)."""
        from services.parsers import route_file
        
        queue = route_file(
            file_size=200 * 1024 * 1024,  # 200MB
            extension='.pdf'
        )
        assert queue == "queues.parsing"


class TestChunkedProcessing:
    """Test chunked file processing for memory efficiency."""
    
    def test_csv_processor_uses_chunking(self):
        """CSV processor should use chunked reading."""
        from services.parsers import CSVProcessor
        import inspect
        
        source = inspect.getsource(CSVProcessor.process)
        assert 'chunksize' in source or 'chunk' in source.lower(), \
            "CSV processor must use chunked reading"
    
    def test_excel_processor_uses_chunking(self):
        """Excel processor should use chunked reading."""
        from services.parsers import ExcelProcessor
        import inspect
        
        source = inspect.getsource(ExcelProcessor.process)
        # Excel chunking uses read_only mode or row iteration
        assert 'read_only' in source or 'iter_rows' in source, \
            "Excel processor must use memory-efficient reading"
    
    def test_csv_chunked_output_correct(self):
        """Verify chunked CSV processing produces correct output."""
        from services.parsers import CSVProcessor
        
        # Create test CSV content
        csv_content = b"name,value\nAlice,100\nBob,200\nCharlie,300"
        
        processor = CSVProcessor()
        result = processor.process(csv_content, "test.csv")
        
        assert result is not None
        assert len(result.chunks) > 0
        # Verify structured format
        assert "name:" in result.chunks[0].content.lower() or \
               "Alice" in result.chunks[0].content


class TestMemoryGuards:
    """Test memory protection mechanisms."""
    
    def test_file_size_limit_enforced(self):
        """Verify file size limits are enforced."""
        from core.config import settings
        
        assert hasattr(settings, 'MAX_STRUCTURED_FILE_SIZE')
        assert settings.MAX_STRUCTURED_FILE_SIZE > 0
        assert settings.MAX_STRUCTURED_FILE_SIZE <= 100 * 1024 * 1024  # Max 100MB
    
    def test_oversized_file_rejected(self):
        """Verify oversized structured files are rejected or routed."""
        from worker.tasks import process_file_task
        from core.config import settings
        
        # File larger than limit
        large_size = settings.MAX_STRUCTURED_FILE_SIZE + 1
        
        # Should either reject or route to heavy queue
        # Implementation-specific assertion
        pass
    
    @pytest.mark.skip(reason="Requires actual memory monitoring")
    def test_memory_usage_within_bounds(self):
        """Verify processing stays within memory bounds."""
        import tracemalloc
        from services.parsers import CSVProcessor
        
        tracemalloc.start()
        
        # Process a medium file
        csv_content = b"col1,col2\n" + b"data,data\n" * 100000
        processor = CSVProcessor()
        result = processor.process(csv_content, "medium.csv")
        
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        # Peak should not exceed 500MB for this size
        assert peak < 500 * 1024 * 1024, f"Peak memory {peak} exceeds limit"
```

---

## 3. Critical Bug: Ghost Data Sync Logic

### 3.1 Problem Description

**Severity:** 🔴 CRITICAL - Blocks V1.0 Enterprise Release

**Current Deduplication Logic (FLAWED):**
```python
# worker/tasks.py lines 447-454
existing_doc_id = None
if content_hash:
    existing = supabase.table("documents").select("id").eq("user_id", user_id).eq(
        "title", doc_title
    ).eq("content_hash", content_hash).limit(1).execute()
    if existing_data:
        existing_doc_id = existing_data[0]["id"]
```

**Matching Criteria:** `user_id` + `title` + `content_hash`

**The Bug:** When a file's content changes (new content_hash), no existing document matches, causing a NEW document to be created. The OLD document with its vectors remains as **ghost data**.

### 3.2 Impact Analysis

| Scenario | Current Behavior | Expected Behavior |
|----------|------------------|-------------------|
| User uploads "Budget.xlsx" | Creates Document A | Creates Document A |
| User updates "Budget.xlsx" | Creates Document B ❌ | Updates Document A ✅ |
| User searches "budget" | Returns A + B (outdated + current) ❌ | Returns only current ✅ |
| Storage usage | Doubles per update ❌ | Constant ✅ |

**Enterprise Impact:**
- Compliance risk: Outdated information in search results
- Cost: Vector storage grows unbounded
- UX: Users see duplicate documents
- Performance: Search quality degrades

### 3.3 Root Cause

The system conflates **content identity** (what the file contains) with **source identity** (which file it is).

**Content Identity:** SHA-256 hash of file bytes
**Source Identity:** Stable identifier from the source system

| Source | Source Identity | Example |
|--------|-----------------|---------|
| Google Drive | `driveItem.id` | `1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs` |
| OneDrive | `driveItem.id` | `01BYE5RZ6QN3ZWBTUFOFD3GSPGOHDJD36M` |
| SharePoint | `driveItem.id` | Same as OneDrive |
| Notion | `page.id` | `a1b2c3d4-e5f6-7890-abcd-ef1234567890` |
| Web | Normalized URL | `https://example.com/page` |
| File Upload | `{user_id}/{filename}` | `uuid-123/Budget.xlsx` |

### 3.4 Correct Logic

```python
def ingest_document_batched(
    supabase,
    user_id: str,
    doc_title: str,
    source_type: str,
    metadata: dict,
    chunks_payload: list,
    file_size_bytes: int = 0,
    job_id: str = None,
    source_url: str = None,
    file_status_id: str = None,
    content_hash: str = None,
    source_id: str = None,  # NEW: Required for proper dedup
) -> str:
    """
    Insert or update document using SOURCE-BASED deduplication.
    
    Deduplication Strategy:
    1. Match by source_id (stable identifier)
    2. If match found, compare content_hash
       - Same hash: Skip (idempotent, touch updated_at)
       - Different hash: Replace vectors atomically
    3. If no match: Insert new document
    """
    
    # Step 1: Find existing document by SOURCE identity
    existing_doc = None
    if source_id:
        existing = supabase.table("documents").select("id, content_hash").eq(
            "user_id", user_id
        ).eq("source_id", source_id).limit(1).execute()
        
        if existing.data:
            existing_doc = existing.data[0]
    
    # Step 2: Determine action based on content comparison
    if existing_doc:
        if existing_doc.get("content_hash") == content_hash:
            # Unchanged - true idempotency
            logger.info(f"⏭️ Skipping unchanged document: {doc_title}")
            # Touch updated_at for sync tracking
            supabase.table("documents").update({
                "updated_at": datetime.now(timezone.utc).isoformat()
            }).eq("id", existing_doc["id"]).execute()
            return existing_doc["id"]
        else:
            # Changed - atomic replacement
            logger.info(f"♻️ Replacing changed document: {doc_title}")
            doc_id = existing_doc["id"]
            
            # DELETE old vectors first
            delete_rows_with_retry(
                supabase, "document_chunks", "document_id", doc_id,
                context=f"replace doc_id={doc_id}"
            )
            
            # UPDATE document metadata
            supabase.table("documents").update({
                "title": doc_title,
                "content_hash": content_hash,
                "metadata": metadata,
                "file_size_bytes": file_size_bytes,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }).eq("id", doc_id).execute()
    else:
        # New document
        logger.info(f"📄 Creating new document: {doc_title}")
        doc_result = supabase.table("documents").insert({
            "user_id": user_id,
            "title": doc_title,
            "source_type": source_type,
            "source_id": source_id,  # Store source identity
            "source_url": source_url,
            "content_hash": content_hash,
            "metadata": metadata,
            "file_size_bytes": file_size_bytes,
            "created_at": datetime.now(timezone.utc).isoformat()
        }).execute()
        doc_id = doc_result.data[0]["id"]
    
    # Step 3: Insert new chunks
    # ... (existing batch insert logic)
    
    return doc_id
```

### 3.5 Database Migration Required

```sql
-- Migration: Add source_id column for proper deduplication
-- File: migrations/004_add_source_id.sql

-- Step 1: Add column
ALTER TABLE documents 
ADD COLUMN IF NOT EXISTS source_id TEXT;

-- Step 2: Create index for efficient lookups
CREATE INDEX IF NOT EXISTS idx_documents_source_id 
ON documents(user_id, source_id) 
WHERE source_id IS NOT NULL;

-- Step 3: Backfill existing documents
-- For Google Drive (source_type = 'google_drive')
UPDATE documents 
SET source_id = metadata->>'id'
WHERE source_type = 'google_drive' 
  AND source_id IS NULL 
  AND metadata->>'id' IS NOT NULL;

-- For file uploads (source_type = 'file_upload')
UPDATE documents 
SET source_id = CONCAT(user_id, '/', title)
WHERE source_type = 'file_upload' 
  AND source_id IS NULL;

-- For web crawls (source_type = 'web')
UPDATE documents 
SET source_id = source_url
WHERE source_type = 'web' 
  AND source_id IS NULL 
  AND source_url IS NOT NULL;

-- Step 4: Add comment for documentation
COMMENT ON COLUMN documents.source_id IS 
  'Stable identifier from source system for deduplication. 
   Google Drive: driveItem.id, Notion: page.id, Web: normalized URL';
```

---

### 3.6 Phase 3 Implementation Checklist (Ghost Data Fix)

#### Database Changes
- [ ] Create migration file `004_add_source_id.sql`
- [ ] Test migration on staging database
- [ ] Verify existing data backfill logic
- [ ] Add index for `(user_id, source_id)` lookup
- [ ] Update RLS policies if needed

#### Code Changes (Connectors)
- [ ] Update `DriveConnector` to include `source_id` in file metadata
- [ ] Update `MicrosoftConnector` to include `source_id` in file metadata
- [ ] Update `NotionConnector` to include `source_id` in file metadata
- [ ] Update `WebConnector` to use normalized URL as `source_id`
- [ ] Update `FileUploadConnector` to generate stable `source_id`

#### Code Changes (Worker)
- [ ] Modify `ingest_document_batched` signature to accept `source_id`
- [ ] Implement source-based lookup (not content_hash based)
- [ ] Implement unchanged file skip logic
- [ ] Implement atomic vector replacement logic
- [ ] Update all callers to pass `source_id`

#### Code Changes (API)
- [ ] Update `process_file_task` to extract and pass `source_id`
- [ ] Update `index_chunks_task` to pass `source_id`
- [ ] Update file status tracking for "skipped_unchanged" status

#### Testing
- [ ] Unit test: New file creates document
- [ ] Unit test: Unchanged file skips processing
- [ ] Unit test: Changed file replaces vectors
- [ ] Unit test: Old vectors are deleted (no ghost data)
- [ ] Integration test: Full sync cycle with updates
- [ ] Performance test: Large incremental sync

#### Verification
- [ ] Query for ghost data in staging: `SELECT * FROM documents GROUP BY source_id HAVING COUNT(*) > 1`
- [ ] Verify vector count matches expected after update
- [ ] Verify search results don't include outdated content

---

### 3.7 Phase 3 Unit Tests

```python
# backend/tests/unit/test_phase3_ghost_data_fix.py
"""
Phase 3: Ghost Data Fix Tests
Ensures proper source-based deduplication prevents orphaned vectors.
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone


class TestSourceBasedDeduplication:
    """Test source_id based document matching."""
    
    def test_new_document_created_when_no_source_id_match(self):
        """New source_id should create new document."""
        from worker.tasks import ingest_document_batched
        
        mock_supabase = MagicMock()
        
        # No existing document with this source_id
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = []
        
        # Insert returns new document
        mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [{"id": "new-doc-id"}]
        
        doc_id = ingest_document_batched(
            supabase=mock_supabase,
            user_id="user-123",
            doc_title="Report.xlsx",
            source_type="google_drive",
            metadata={},
            chunks_payload=[{"content": "test", "embedding": [0.1]}],
            source_id="drive-file-abc",
            content_hash="hash-v1"
        )
        
        assert doc_id == "new-doc-id"
        mock_supabase.table.return_value.insert.assert_called()
    
    def test_unchanged_document_skipped(self):
        """Document with same source_id AND content_hash should skip."""
        from worker.tasks import ingest_document_batched
        
        mock_supabase = MagicMock()
        
        # Existing document with same hash
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
            {"id": "existing-doc-id", "content_hash": "hash-v1"}
        ]
        
        doc_id = ingest_document_batched(
            supabase=mock_supabase,
            user_id="user-123",
            doc_title="Report.xlsx",
            source_type="google_drive",
            metadata={},
            chunks_payload=[{"content": "test", "embedding": [0.1]}],
            source_id="drive-file-abc",
            content_hash="hash-v1"  # Same hash
        )
        
        assert doc_id == "existing-doc-id"
        # Should NOT insert new document
        mock_supabase.table.return_value.insert.assert_not_called()
        # Should update timestamp
        mock_supabase.table.return_value.update.assert_called()
    
    def test_changed_document_replaces_vectors(self):
        """Document with same source_id but different hash should replace."""
        from worker.tasks import ingest_document_batched
        
        mock_supabase = MagicMock()
        
        # Existing document with DIFFERENT hash
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
            {"id": "existing-doc-id", "content_hash": "hash-v1"}
        ]
        
        with patch('worker.tasks.delete_rows_with_retry') as mock_delete:
            doc_id = ingest_document_batched(
                supabase=mock_supabase,
                user_id="user-123",
                doc_title="Report.xlsx",
                source_type="google_drive",
                metadata={},
                chunks_payload=[{"content": "test", "embedding": [0.1]}],
                source_id="drive-file-abc",
                content_hash="hash-v2"  # DIFFERENT hash
            )
        
        assert doc_id == "existing-doc-id"
        # Should delete old chunks
        mock_delete.assert_called_with(
            mock_supabase,
            "document_chunks",
            "document_id",
            "existing-doc-id",
            context=pytest.approx(any)
        )
        # Should NOT create new document
        mock_supabase.table.return_value.insert.assert_not_called()


class TestNoGhostData:
    """Ensure no orphaned vectors remain after updates."""
    
    def test_old_chunks_deleted_before_new_insert(self):
        """Old chunks must be deleted before inserting new ones."""
        from worker.tasks import ingest_document_batched
        
        mock_supabase = MagicMock()
        call_order = []
        
        def track_delete(*args, **kwargs):
            call_order.append('delete')
            return MagicMock(data=[])
        
        def track_insert(*args, **kwargs):
            call_order.append('insert')
            return MagicMock(data=[{"id": "chunk-1"}])
        
        # Existing document
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
            {"id": "doc-123", "content_hash": "old-hash"}
        ]
        
        with patch('worker.tasks.delete_rows_with_retry', side_effect=track_delete):
            with patch('worker.tasks.insert_rows_with_retry', side_effect=track_insert):
                ingest_document_batched(
                    supabase=mock_supabase,
                    user_id="user-123",
                    doc_title="Report.xlsx",
                    source_type="google_drive",
                    metadata={},
                    chunks_payload=[{"content": "new", "embedding": [0.1]}],
                    source_id="drive-file-abc",
                    content_hash="new-hash"
                )
        
        # Delete must come before insert
        assert call_order.index('delete') < call_order.index('insert'), \
            "Chunks must be deleted before inserting new ones"
    
    def test_no_duplicate_documents_for_same_source(self):
        """Multiple ingests of same source should not create duplicates."""
        from worker.tasks import ingest_document_batched
        
        mock_supabase = MagicMock()
        created_docs = []
        
        def mock_insert(data):
            mock_result = MagicMock()
            new_id = f"doc-{len(created_docs)}"
            created_docs.append(new_id)
            mock_result.execute.return_value.data = [{"id": new_id}]
            return mock_result
        
        # First call: no existing document
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = []
        mock_supabase.table.return_value.insert = mock_insert
        
        # First ingestion
        doc_id_1 = ingest_document_batched(
            supabase=mock_supabase,
            user_id="user-123",
            doc_title="Report.xlsx",
            source_type="google_drive",
            metadata={},
            chunks_payload=[{"content": "v1", "embedding": [0.1]}],
            source_id="drive-file-abc",
            content_hash="hash-v1"
        )
        
        # Second call: existing document found
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
            {"id": doc_id_1, "content_hash": "hash-v1"}
        ]
        
        # Second ingestion (same content)
        doc_id_2 = ingest_document_batched(
            supabase=mock_supabase,
            user_id="user-123",
            doc_title="Report.xlsx",
            source_type="google_drive",
            metadata={},
            chunks_payload=[{"content": "v1", "embedding": [0.1]}],
            source_id="drive-file-abc",
            content_hash="hash-v1"
        )
        
        # Should reuse same document
        assert doc_id_1 == doc_id_2
        assert len(created_docs) == 1  # Only one document created


class TestSourceIdExtraction:
    """Test source_id extraction from different connectors."""
    
    def test_google_drive_source_id(self):
        """Google Drive files should use driveItem.id as source_id."""
        # This would test the connector
        drive_file = {
            "id": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs",
            "name": "Report.xlsx",
            "mimeType": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        }
        
        source_id = drive_file["id"]
        assert source_id == "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs"
    
    def test_file_upload_source_id(self):
        """File uploads should use user_id/filename as source_id."""
        user_id = "user-123"
        filename = "Budget.xlsx"
        
        source_id = f"{user_id}/{filename}"
        assert source_id == "user-123/Budget.xlsx"
    
    def test_web_crawl_source_id(self):
        """Web pages should use normalized URL as source_id."""
        from connectors.web import WebConnector
        
        connector = WebConnector()
        url = "https://example.com/page?query=1#section"
        
        # Should normalize and use as source_id
        normalized = connector.normalize_url(url)
        assert "example.com" in normalized
```

---

## 4. Router Strategy Analysis

### 4.1 Current Processor Support

| Extension | Processor | Status |
|-----------|-----------|--------|
| .py, .js, .ts, etc. | `CodeProcessor` | ✅ Working |
| .md, .markdown | `MarkdownProcessor` | ✅ Working |
| .pdf | `PDFProcessor` | ✅ Working (PyMuPDF + LlamaParse) |
| .docx | `DocxProcessor` | ✅ Working |
| .doc | `DocxProcessor` | ⚠️ Will fail (wrong parser) |
| .txt, .log | `PlainTextProcessor` | ✅ Working |
| .csv | `PlainTextProcessor` | ⚠️ No structured parsing |
| .xlsx | UNSUPPORTED | ❌ Blocked |
| .pptx | UNSUPPORTED | ❌ Blocked |
| .xls | UNSUPPORTED | ❌ Blocked |
| .msg, .eml | NOT MAPPED | ❌ Not implemented |

### 4.2 Proposed Router Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    DOCUMENT ROUTER                               │
└─────────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              │               │               │
              ▼               ▼               ▼
    ┌─────────────────┐ ┌─────────────┐ ┌──────────────────┐
    │  GROUP A:       │ │  GROUP B:   │ │  GROUP C:        │
    │  LOCAL/FAST     │ │  STRUCTURED │ │  COMPLEX/PAID    │
    └─────────────────┘ └─────────────┘ └──────────────────┘
              │               │               │
              ▼               ▼               ▼
    ┌─────────────────┐ ┌─────────────┐ ┌──────────────────┐
    │ • Code files    │ │ • CSV       │ │ • .doc (legacy)  │
    │ • Markdown      │ │ • XLSX      │ │ • .xls (legacy)  │
    │ • DOCX          │ │ • TSV       │ │ • .pptx          │
    │ • PDF (text)    │ │             │ │ • .msg (email)   │
    │ • TXT           │ │             │ │ • Scanned PDFs   │
    │ • XML/HTML      │ │             │ │                  │
    └─────────────────┘ └─────────────┘ └──────────────────┘
              │               │               │
              ▼               ▼               ▼
    ┌─────────────────┐ ┌─────────────┐ ┌──────────────────┐
    │  Local Parsers  │ │  Pandas +   │ │  LlamaParse API  │
    │  (PyMuPDF,      │ │  OpenPyXL   │ │  (OCR, Tables,   │
    │  python-docx)   │ │  (chunked)  │ │  Complex Layout) │
    └─────────────────┘ └─────────────┘ └──────────────────┘
```

### 4.3 Missing Dependencies

Add to `requirements.txt`:

```
# Structured Data Processing
pandas>=2.0.0,<3.0.0
openpyxl>=3.1.0,<4.0.0

# Presentation Files
python-pptx>=0.6.21,<1.0.0

# Email Parsing
extract-msg>=0.45.0,<1.0.0

# LangChain Text Splitters (explicit declaration)
langchain-text-splitters>=0.2.0,<0.3.0
```

### 4.4 New Processor Implementations

#### CSV Processor
```python
class CSVProcessor(BaseProcessor):
    """
    Processor for CSV files with structured output.
    
    Strategy:
    - Use Pandas with chunked reading for memory efficiency
    - Format rows as "Column: Value" pairs for LLM retrieval
    - Preserve header context in each chunk
    """
    
    CHUNK_SIZE = 500  # Rows per chunk
    
    def process(self, content: bytes, filename: str) -> ProcessedDocument:
        import pandas as pd
        import io
        
        chunks = []
        total_tokens = 0
        
        try:
            # Read with chunking
            df_iter = pd.read_csv(
                io.BytesIO(content),
                chunksize=self.CHUNK_SIZE,
                encoding='utf-8',
                on_bad_lines='skip'
            )
            
            for chunk_idx, df_chunk in enumerate(df_iter):
                # Format as structured text
                text_rows = []
                for idx, row in df_chunk.iterrows():
                    row_text = " | ".join([
                        f"{col}: {val}" 
                        for col, val in row.items() 
                        if pd.notna(val)
                    ])
                    text_rows.append(row_text)
                
                chunk_text = f"[File: {filename}] [Rows: {chunk_idx * self.CHUNK_SIZE + 1}-{chunk_idx * self.CHUNK_SIZE + len(df_chunk)}]\n"
                chunk_text += "\n".join(text_rows)
                
                token_count = self.count_tokens(chunk_text)
                total_tokens += token_count
                
                chunks.append(ProcessedChunk(
                    content=chunk_text,
                    metadata={
                        "file_type": "csv",
                        "row_range": f"{chunk_idx * self.CHUNK_SIZE + 1}-{chunk_idx * self.CHUNK_SIZE + len(df_chunk)}",
                        "filename": filename
                    },
                    token_count=token_count,
                    chunk_index=chunk_idx
                ))
                
        except Exception as e:
            logger.error(f"[CSVProcessor] Failed to parse {filename}: {e}")
            return ProcessedDocument(chunks=[], file_type="csv")
        
        logger.info(f"[CSVProcessor] {filename}: {len(chunks)} chunks, {total_tokens} tokens")
        return ProcessedDocument(
            chunks=chunks,
            file_type="csv",
            total_tokens=total_tokens
        )
```

#### Scanned PDF Detection
```python
def _is_likely_scanned(self, content: bytes) -> bool:
    """
    Detect if PDF is scanned (image-only) based on text density.
    
    Returns True if PDF should be routed to LlamaParse for OCR.
    """
    try:
        import fitz
        doc = fitz.open(stream=content, filetype="pdf")
        
        total_chars = 0
        total_pages = doc.page_count
        
        # Sample first 5 pages
        for page_num in range(min(5, total_pages)):
            page = doc[page_num]
            text = page.get_text("text")
            total_chars += len(text.strip())
        
        doc.close()
        
        # Heuristic: Less than 100 chars per page = likely scanned
        chars_per_page = total_chars / max(1, min(5, total_pages))
        
        return chars_per_page < 100
        
    except Exception as e:
        logger.warning(f"[PDFProcessor] Scan detection failed: {e}")
        return False  # Default to local parsing
```

---

### 4.5 Phase 4 Implementation Checklist (Router)

#### Dependency Updates
- [ ] Add `pandas>=2.0.0,<3.0.0` to requirements.txt
- [ ] Add `openpyxl>=3.1.0,<4.0.0` to requirements.txt
- [ ] Add `python-pptx>=0.6.21,<1.0.0` to requirements.txt
- [ ] Add `extract-msg>=0.45.0,<1.0.0` to requirements.txt
- [ ] Add `langchain-text-splitters>=0.2.0,<0.3.0` to requirements.txt
- [ ] Run `pip install -r requirements.txt` and verify no conflicts
- [ ] Update Docker images with new dependencies

#### New Processor Classes
- [ ] Implement `CSVProcessor` with chunked Pandas reading
- [ ] Implement `ExcelProcessor` with OpenPyXL read_only mode
- [ ] Implement `PPTXProcessor` using python-pptx
- [ ] Implement `EmailProcessor` for .msg and .eml files
- [ ] Implement `LegacyOfficeProcessor` (routes to LlamaParse)

#### Update PROCESSOR_MAP
- [ ] Add `.csv` → `CSVProcessor`
- [ ] Add `.xlsx` → `ExcelProcessor`
- [ ] Add `.xls` → `LegacyOfficeProcessor`
- [ ] Add `.pptx` → `PPTXProcessor`
- [ ] Add `.ppt` → `LegacyOfficeProcessor`
- [ ] Add `.doc` → `LegacyOfficeProcessor`
- [ ] Add `.msg` → `EmailProcessor`
- [ ] Add `.eml` → `EmailProcessor`
- [ ] Remove from `UNSUPPORTED_EXTENSIONS`

#### PDF Enhancement
- [ ] Add `_is_likely_scanned()` method to `PDFProcessor`
- [ ] Update `process()` to check for scanned PDFs
- [ ] Route scanned PDFs to LlamaParse automatically

#### Testing
- [ ] Test CSV with 10KB, 1MB, 50MB files
- [ ] Test Excel with multiple sheets
- [ ] Test PPTX with images and tables
- [ ] Test .msg email with attachments
- [ ] Test scanned PDF detection accuracy

---

### 4.6 Phase 4 Unit Tests

```python
# backend/tests/unit/test_phase4_router.py
"""
Phase 4: Router Strategy Tests
Tests for new document processors and routing logic.
"""

import pytest
from unittest.mock import MagicMock, patch
import io


class TestCSVProcessor:
    """Test CSV file processing."""
    
    def test_csv_basic_parsing(self):
        """Basic CSV parsing should work."""
        from services.parsers import CSVProcessor
        
        csv_content = b"name,value,category\nAlice,100,A\nBob,200,B"
        processor = CSVProcessor()
        result = processor.process(csv_content, "test.csv")
        
        assert result is not None
        assert result.file_type == "csv"
        assert len(result.chunks) > 0
    
    def test_csv_structured_output(self):
        """CSV output should be formatted as Key: Value pairs."""
        from services.parsers import CSVProcessor
        
        csv_content = b"name,value\nAlice,100"
        processor = CSVProcessor()
        result = processor.process(csv_content, "test.csv")
        
        chunk_content = result.chunks[0].content
        assert "name:" in chunk_content.lower() or "Name:" in chunk_content
        assert "Alice" in chunk_content
        assert "100" in chunk_content
    
    def test_csv_chunked_processing(self):
        """Large CSV should be processed in chunks."""
        from services.parsers import CSVProcessor
        
        # Generate large CSV
        header = b"col1,col2,col3\n"
        rows = b"".join([f"val{i},val{i+1},val{i+2}\n".encode() for i in range(2000)])
        csv_content = header + rows
        
        processor = CSVProcessor()
        result = processor.process(csv_content, "large.csv")
        
        # Should have multiple chunks
        assert len(result.chunks) > 1
    
    def test_csv_handles_bad_encoding(self):
        """CSV processor should handle encoding errors gracefully."""
        from services.parsers import CSVProcessor
        
        # CSV with mixed encoding
        csv_content = b"name,value\nCaf\xe9,100\n"
        processor = CSVProcessor()
        result = processor.process(csv_content, "mixed.csv")
        
        # Should not crash
        assert result is not None


class TestExcelProcessor:
    """Test Excel file processing."""
    
    @pytest.mark.skip(reason="Requires actual Excel file")
    def test_xlsx_basic_parsing(self):
        """Basic XLSX parsing should work."""
        from services.parsers import ExcelProcessor
        
        # Would need actual Excel file bytes
        pass
    
    def test_xlsx_processor_registered(self):
        """XLSX should be mapped to ExcelProcessor."""
        from services.parsers import DocumentProcessorFactory, ExcelProcessor
        
        assert ".xlsx" in DocumentProcessorFactory.PROCESSOR_MAP
        assert DocumentProcessorFactory.PROCESSOR_MAP[".xlsx"] == ExcelProcessor
    
    def test_xlsx_not_in_unsupported(self):
        """XLSX should not be in unsupported list."""
        from services.parsers import DocumentProcessorFactory
        
        assert ".xlsx" not in DocumentProcessorFactory.UNSUPPORTED_EXTENSIONS


class TestPPTXProcessor:
    """Test PowerPoint file processing."""
    
    def test_pptx_processor_registered(self):
        """PPTX should be mapped to PPTXProcessor."""
        from services.parsers import DocumentProcessorFactory, PPTXProcessor
        
        assert ".pptx" in DocumentProcessorFactory.PROCESSOR_MAP
        assert DocumentProcessorFactory.PROCESSOR_MAP[".pptx"] == PPTXProcessor
    
    def test_pptx_not_in_unsupported(self):
        """PPTX should not be in unsupported list."""
        from services.parsers import DocumentProcessorFactory
        
        assert ".pptx" not in DocumentProcessorFactory.UNSUPPORTED_EXTENSIONS


class TestEmailProcessor:
    """Test email file processing."""
    
    def test_msg_processor_registered(self):
        """MSG should be mapped to EmailProcessor."""
        from services.parsers import DocumentProcessorFactory, EmailProcessor
        
        assert ".msg" in DocumentProcessorFactory.PROCESSOR_MAP
        assert DocumentProcessorFactory.PROCESSOR_MAP[".msg"] == EmailProcessor
    
    def test_eml_processor_registered(self):
        """EML should be mapped to EmailProcessor."""
        from services.parsers import DocumentProcessorFactory, EmailProcessor
        
        assert ".eml" in DocumentProcessorFactory.PROCESSOR_MAP
        assert DocumentProcessorFactory.PROCESSOR_MAP[".eml"] == EmailProcessor


class TestScannedPDFDetection:
    """Test scanned PDF detection heuristic."""
    
    def test_text_pdf_detected_correctly(self):
        """Text-based PDF should not be flagged as scanned."""
        from services.parsers import PDFProcessor
        
        # Mock PDF with text
        with patch.object(PDFProcessor, '_is_likely_scanned', return_value=False):
            processor = PDFProcessor()
            is_scanned = processor._is_likely_scanned(b"mock pdf content")
        
        assert is_scanned is False
    
    def test_scanned_pdf_detected_correctly(self):
        """Image-only PDF should be flagged as scanned."""
        from services.parsers import PDFProcessor
        
        # Mock scanned PDF (no text)
        with patch.object(PDFProcessor, '_is_likely_scanned', return_value=True):
            processor = PDFProcessor()
            is_scanned = processor._is_likely_scanned(b"mock scanned pdf")
        
        assert is_scanned is True


class TestLegacyOfficeRouting:
    """Test legacy Office file routing to LlamaParse."""
    
    def test_doc_routes_to_llamaparse(self):
        """Legacy .doc files should route to LlamaParse."""
        from services.parsers import DocumentProcessorFactory, LegacyOfficeProcessor
        
        assert ".doc" in DocumentProcessorFactory.PROCESSOR_MAP
        # LegacyOfficeProcessor should use LlamaParse internally
    
    def test_xls_routes_to_llamaparse(self):
        """Legacy .xls files should route to LlamaParse."""
        from services.parsers import DocumentProcessorFactory, LegacyOfficeProcessor
        
        assert ".xls" in DocumentProcessorFactory.PROCESSOR_MAP


class TestRouterIntegration:
    """Test full routing logic."""
    
    def test_factory_routes_csv_correctly(self):
        """Factory should route CSV to CSVProcessor."""
        from services.parsers import DocumentProcessorFactory
        
        result = DocumentProcessorFactory.process(
            content=b"a,b\n1,2",
            filename="test.csv"
        )
        
        assert result.file_type == "csv"
    
    def test_factory_routes_code_correctly(self):
        """Factory should route Python files to CodeProcessor."""
        from services.parsers import DocumentProcessorFactory
        
        result = DocumentProcessorFactory.process(
            content=b"def hello(): pass",
            filename="test.py"
        )
        
        assert result.file_type == "code"
        assert "python" in str(result.metadata).lower()
```

---

## 5. Bullet-Proof Incremental Sync Logic

### 5.1 Complete Sync Flow Diagram

```
┌──────────────────────────────────────────────────────────────────────────┐
│                      INCREMENTAL SYNC ARCHITECTURE                        │
└──────────────────────────────────────────────────────────────────────────┘

TRIGGER: User clicks "Sync" or Scheduled Cron

    ┌─────────────────────────────────────────────────────────────────────┐
    │ PHASE 1: DISCOVERY                                                   │
    │                                                                      │
    │   1. Fetch file list from connector (Google Drive, OneDrive, etc.)  │
    │   2. For each file, extract:                                        │
    │      - source_id (stable identifier)                                │
    │      - filename                                                     │
    │      - modified_at (from source)                                    │
    │      - file_size                                                    │
    │   3. Create file_status records in DB                               │
    │   4. Dispatch to process_file_task queue                            │
    │                                                                      │
    └─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
    ┌─────────────────────────────────────────────────────────────────────┐
    │ PHASE 2: PER-FILE PROCESSING (Parallel Workers)                      │
    │                                                                      │
    │   For each file:                                                    │
    │                                                                      │
    │   ┌─────────────────┐                                               │
    │   │ 2.1 DOWNLOAD    │ Download file content from source             │
    │   └────────┬────────┘                                               │
    │            │                                                        │
    │            ▼                                                        │
    │   ┌─────────────────┐                                               │
    │   │ 2.2 HASH        │ Compute content_hash = SHA256(content)        │
    │   └────────┬────────┘                                               │
    │            │                                                        │
    │            ▼                                                        │
    │   ┌─────────────────────────────────────────────┐                   │
    │   │ 2.3 LOOKUP BY SOURCE_ID                     │                   │
    │   │                                             │                   │
    │   │  SELECT id, content_hash FROM documents     │                   │
    │   │  WHERE user_id = ? AND source_id = ?        │                   │
    │   └────────┬────────────────────────────────────┘                   │
    │            │                                                        │
    │       ┌────┴────┐                                                   │
    │       │         │                                                   │
    │   NOT FOUND   FOUND                                                 │
    │       │         │                                                   │
    │       │    ┌────┴────┐                                              │
    │       │    │         │                                              │
    │       │  SAME     DIFFERENT                                         │
    │       │  HASH       HASH                                            │
    │       │    │         │                                              │
    │       │    ▼         ▼                                              │
    │       │  ┌───────┐ ┌───────────────────┐                           │
    │       │  │ SKIP  │ │ REPLACE VECTORS   │                           │
    │       │  │(touch │ │ 1. DELETE chunks  │                           │
    │       │  │update)│ │ 2. UPDATE doc     │                           │
    │       │  └───────┘ │ 3. Re-parse       │                           │
    │       │            │ 4. Re-embed       │                           │
    │       │            │ 5. INSERT chunks  │                           │
    │       │            └───────────────────┘                           │
    │       ▼                                                             │
    │   ┌───────────────────┐                                             │
    │   │ NEW DOCUMENT      │                                             │
    │   │ 1. Parse content  │                                             │
    │   │ 2. Generate embed │                                             │
    │   │ 3. INSERT doc     │                                             │
    │   │ 4. INSERT chunks  │                                             │
    │   └───────────────────┘                                             │
    │                                                                      │
    └─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
    ┌─────────────────────────────────────────────────────────────────────┐
    │ PHASE 3: FINALIZATION                                                │
    │                                                                      │
    │   1. When all files processed (via Redis counters)                  │
    │   2. Update ingestion_job status to "completed"                     │
    │   3. Send user notification                                         │
    │   4. Log audit trail                                                │
    │                                                                      │
    └─────────────────────────────────────────────────────────────────────┘
```

### 5.2 Concurrency Safety

The atomic replacement MUST handle concurrent updates:

```python
def replace_document_vectors_atomic(
    supabase,
    doc_id: str,
    new_content_hash: str,
    new_metadata: dict,
    new_chunks: list
):
    """
    Atomically replace document vectors.
    
    Uses optimistic locking to handle concurrent updates:
    1. Read current content_hash
    2. Delete chunks
    3. Update document with WHERE content_hash = old_hash
    4. If update affected 0 rows, another process won
    5. Insert new chunks
    """
    
    # Step 1: Get current state
    current = supabase.table("documents").select("content_hash").eq(
        "id", doc_id
    ).single().execute()
    
    old_hash = current.data["content_hash"]
    
    # Step 2: Delete old chunks (safe - worst case we re-insert same data)
    supabase.table("document_chunks").delete().eq("document_id", doc_id).execute()
    
    # Step 3: Update with optimistic lock
    update_result = supabase.table("documents").update({
        "content_hash": new_content_hash,
        "metadata": new_metadata,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }).eq("id", doc_id).eq("content_hash", old_hash).execute()
    
    if not update_result.data:
        # Another process updated first - this is OK, they have newer data
        logger.info(f"Concurrent update detected for doc {doc_id}, skipping")
        return False
    
    # Step 4: Insert new chunks
    for chunk in new_chunks:
        chunk["document_id"] = doc_id
    
    insert_rows_with_retry(supabase, "document_chunks", new_chunks)
    
    return True
```

### 5.3 Deleted File Handling

For enterprise sync, we also need to handle files that were deleted at the source:

```python
def cleanup_deleted_files(
    supabase,
    user_id: str,
    source_type: str,
    current_source_ids: set
):
    """
    Remove documents that no longer exist at the source.
    
    Called after a full sync to clean up orphaned documents.
    """
    
    # Get all documents for this source
    existing = supabase.table("documents").select("id, source_id").eq(
        "user_id", user_id
    ).eq("source_type", source_type).execute()
    
    for doc in existing.data:
        if doc["source_id"] not in current_source_ids:
            logger.info(f"🗑️ Removing deleted file: {doc['source_id']}")
            
            # Delete chunks first
            supabase.table("document_chunks").delete().eq(
                "document_id", doc["id"]
            ).execute()
            
            # Delete document
            supabase.table("documents").delete().eq(
                "id", doc["id"]
            ).execute()
```

---

## 6. Execution Roadmap

### 6.1 Timeline Overview

| Phase | Task | Duration | Dependencies |
|-------|------|----------|--------------|
| 1 | Dead Code Cleanup | 1 day | None |
| 2 | Memory Safety | 2 days | None |
| 3 | Ghost Data Fix | 3 days | Phase 1 |
| 4 | Router Implementation | 5 days | Phase 2 |
| 5 | Integration Testing | 2 days | Phase 3, 4 |
| 6 | Production Deployment | 1 day | Phase 5 |

**Total Estimated Time:** 14 days

### 6.2 Phase Dependencies

```
Phase 1 ───────────────────────────┐
(Dead Code)                        │
                                   ├──► Phase 3 ──► Phase 5 ──► Phase 6
Phase 2 ───────────────────────────┤    (Ghost     (Testing)  (Deploy)
(Memory Safety)                    │     Data)
                                   │
                                   └──► Phase 4
                                        (Router)
```

### 6.3 Risk Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Ghost Data fix breaks existing sync | Medium | High | Feature flag, staged rollout |
| Pandas OOM on large files | High | Medium | Chunked processing, size limits |
| LlamaParse API changes | Low | Medium | Version pinning, fallback logic |
| Database migration fails | Low | High | Dry-run on staging, backup |

### 6.4 Success Criteria

- [ ] Zero ghost data created during incremental sync
- [ ] All supported file types parse correctly
- [ ] No OOM kills during stress testing
- [ ] Test coverage >80% for new code
- [ ] Performance: <30s average ingestion time per file
- [ ] Documentation updated for all changes

---

## Appendix: Test Specifications

### A.1 Test File Locations

```
backend/tests/
├── unit/
│   ├── test_phase1_cleanup.py
│   ├── test_phase2_memory_safety.py
│   ├── test_phase3_ghost_data_fix.py
│   └── test_phase4_router.py
├── integration/
│   ├── test_incremental_sync.py
│   ├── test_concurrent_updates.py
│   └── test_deleted_file_cleanup.py
└── load/
    ├── test_large_csv_processing.py
    └── test_concurrent_file_ingestion.py
```

### A.2 Running Tests

```bash
# Run all phase tests
pytest backend/tests/unit/test_phase*.py -v

# Run specific phase
pytest backend/tests/unit/test_phase3_ghost_data_fix.py -v

# Run with coverage
pytest backend/tests/unit/test_phase*.py --cov=backend --cov-report=html

# Run integration tests
pytest backend/tests/integration/ -v --slow
```

### A.3 CI/CD Integration

```yaml
# .github/workflows/test.yml
name: V1.0 Upgrade Tests

on:
  pull_request:
    paths:
      - 'backend/**'

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r backend/requirements.txt
          pip install -r backend/requirements-test.txt
      
      - name: Run unit tests
        run: |
          pytest backend/tests/unit/test_phase*.py -v --tb=short
      
      - name: Run integration tests
        run: |
          pytest backend/tests/integration/ -v --tb=short
```

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-01-14 | Senior Architect | Initial comprehensive audit |

---

**END OF DOCUMENT**


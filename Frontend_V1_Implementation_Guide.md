# 📋 FRONTEND V1.0 IMPLEMENTATION GUIDE

**Document Version:** 1.0  
**Date:** January 14, 2026  
**Status:** REMEDIATION REQUIRED  
**Backend Version:** V1.0 (Streaming Ingestion, Extended File Support, Ghost Data Fix)

---

## 🔗 BACKEND ↔ FRONTEND INTEGRATION MAP

This section documents how the Backend V1.0 changes wire to the Frontend.

### Backend Changes Summary

| Backend Component | Change | Frontend Impact |
|-------------------|--------|-----------------|
| `backend/services/parsers.py` | Added 11 new processors (CSV, Excel, PPTX, Email, HTML, Image, LegacyOffice, LlamaParse) | Frontend must accept new file types |
| `backend/worker/tasks.py` | New status `skipped_unsupported` returned when file requires missing config or exceeds size limit | Frontend must display this status correctly |
| `backend/worker/tasks.py` | Atomic replacement using `source_id` instead of `content_hash` | Frontend cache invalidation remains compatible |
| `backend/core/config.py` | `MAX_STRUCTURED_FILE_SIZE = 50MB` for CSV/XLSX | Frontend should not block large files (backend handles rejection) |
| `supabase/migrations/20260114223000_add_documents_source_id.sql` | Added `source_id` column | No frontend changes needed (transparent) |

### API Contract: File Status Values

The backend `ingestion_file_status` table returns these status values:

| Status | Backend Meaning | Frontend Display |
|--------|-----------------|------------------|
| `pending` | Queued for processing | "Queued" (gray) |
| `uploading` | File being uploaded to storage | "Uploading..." (blue) |
| `parsing` | Document being parsed | "Parsing..." (amber) |
| `processing` | Legacy alias for parsing | "Parsing..." (amber) |
| `embedding` | Generating embeddings | "Embedding..." (purple) |
| `indexing` | Storing in vector DB | "Indexing..." (cyan) |
| `indexed` | Successfully indexed (legacy) | "Indexed" (green) |
| `completed` | Successfully completed | "Complete" (green) |
| `failed` | Processing failed | "Failed" (red) |
| `skipped` | Skipped (duplicate, etc.) | "Skipped" (amber) |
| `skipped_unsupported` | **NEW** - File type requires missing config or exceeds limits | "Unsupported" (orange) |
| `cancelled` | User cancelled | "Cancelled" (amber) |

### Backend File Type Support Matrix

The backend `DocumentProcessorFactory.PROCESSOR_MAP` now supports:

| Extension | Processor | MIME Type | LlamaParse Required? |
|-----------|-----------|-----------|---------------------|
| `.pdf` | PDFProcessor | `application/pdf` | Only for scanned PDFs |
| `.docx` | DocxProcessor | `application/vnd.openxmlformats-officedocument.wordprocessingml.document` | No |
| `.doc` | LegacyOfficeProcessor | `application/msword` | **Yes** |
| `.xlsx` | ExcelProcessor | `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` | No |
| `.xls` | LegacyOfficeProcessor | `application/vnd.ms-excel` | **Yes** |
| `.csv` | CSVProcessor | `text/csv` | No |
| `.tsv` | CSVProcessor | `text/tab-separated-values` | No |
| `.pptx` | PPTXProcessor | `application/vnd.openxmlformats-officedocument.presentationml.presentation` | No |
| `.ppt` | LegacyOfficeProcessor | `application/vnd.ms-powerpoint` | **Yes** |
| `.msg` | EmailProcessor | `application/vnd.ms-outlook` | Fallback only |
| `.eml` | EmailProcessor | `message/rfc822` | Fallback only |
| `.html` | HTMLProcessor | `text/html` | No |
| `.md` | MarkdownProcessor | `text/markdown` | No |
| `.txt` | PlainTextProcessor | `text/plain` | No |
| `.py`, `.js`, `.ts`, etc. | CodeProcessor | `text/plain` | No |
| `.jpg`, `.png`, `.tiff`, `.bmp` | ImageProcessor | `image/*` | **Yes** |

**When `skipped_unsupported` is returned:**
1. File extension requires LlamaParse but `LLAMA_CLOUD_API_KEY` is not configured
2. CSV/XLSX file exceeds `MAX_STRUCTURED_FILE_SIZE` (50MB)
3. File type is in `UNSUPPORTED_EXTENSIONS` set (`.numbers`, `.key`)

---

## 🚨 CRITICAL ISSUES IDENTIFIED

### Issue #1: FileUploadZone Blocks Valid Files
- **Severity:** CRITICAL
- **File:** `frontend-new/components/data-sources/FileUploadZone.tsx`
- **Lines:** 148-156
- **Impact:** Users cannot upload `.xlsx`, `.csv`, `.pptx`, `.xls`, `.doc`, `.ppt`, `.msg`, `.eml`, images, code files
- **Root Cause:** Hardcoded allowlist in `react-dropzone` accept prop only allows PDF, TXT, DOCX

### Issue #2: `skipped_unsupported` Creates Zombie State
- **Severity:** HIGH
- **Files:** `useFileStatus.ts`, `IngestionProgressModal.tsx`
- **Impact:** Files with `skipped_unsupported` status appear stuck in "Processing" state forever
- **Root Cause:** Status not included in terminal state checks at 7 locations

### Issue #3: Supabase SQL Filter Missing New Status
- **Severity:** MEDIUM
- **File:** `frontend-new/hooks/useFileStatus.ts`
- **Line:** 165
- **Impact:** `useAllActiveFiles()` hook will keep fetching `skipped_unsupported` files as "active"
- **Root Cause:** Raw SQL filter string doesn't include `skipped_unsupported`

---

## 📁 FILES REQUIRING MODIFICATION

| File | Changes Required | Priority |
|------|-----------------|----------|
| `frontend-new/components/data-sources/FileUploadZone.tsx` | Lines 148-156, 218 | 🔴 CRITICAL |
| `frontend-new/hooks/useFileStatus.ts` | Lines 10-22, 165, 198, 206, 239-253, 259-274 | 🔴 CRITICAL |
| `frontend-new/components/ingestion/IngestionProgressModal.tsx` | Lines 43-50, 205-209, 213-220, 249 | 🟠 HIGH |

---

## 🔧 IMPLEMENTATION DETAILS

### TASK 1: UNBLOCK FILE UPLOADS

**File:** `frontend-new/components/data-sources/FileUploadZone.tsx`

#### Change 1.1: Replace Accept Prop (Lines 148-156)

**CURRENT CODE (Lines 148-156):**
```typescript
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "application/pdf": [".pdf"],
      "text/plain": [".txt"],
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
    },
    disabled: isUploading || isOverLimit || disabled,
  });
```

**REPLACE WITH:**
```typescript
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      // Documents
      "application/pdf": [".pdf"],
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
      "application/msword": [".doc"],

      // Spreadsheets
      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": [".xlsx"],
      "application/vnd.ms-excel": [".xls"],
      "text/csv": [".csv"],

      // Presentations
      "application/vnd.openxmlformats-officedocument.presentationml.presentation": [".pptx"],
      "application/vnd.ms-powerpoint": [".ppt"],

      // Email
      "message/rfc822": [".eml"],
      "application/vnd.ms-outlook": [".msg"],

      // Text & Code
      "text/plain": [".txt", ".md", ".py", ".js", ".ts", ".json", ".yaml", ".yml", ".xml", ".html", ".css", ".sql", ".env"],
      "text/markdown": [".md"],
      "text/html": [".html", ".htm"],

      // Images (OCR via LlamaParse)
      "image/jpeg": [".jpg", ".jpeg"],
      "image/png": [".png"],
      "image/tiff": [".tiff", ".tif"],
      "image/bmp": [".bmp"],
    },
    disabled: isUploading || isOverLimit || disabled,
  });
```

#### Change 1.2: Update UI Hint Text (Line 218)

**CURRENT CODE (Line 216-219):**
```tsx
          <div className="flex items-center justify-center gap-2 text-xs text-muted-foreground">
            <FileText className="h-3 w-3" />
            PDF, TXT, DOCX
          </div>
```

**REPLACE WITH:**
```tsx
          <div className="flex items-center justify-center gap-2 text-xs text-muted-foreground">
            <FileText className="h-3 w-3" />
            PDF, Office, CSV, Code, Images & more
          </div>
```

---

### TASK 2: ADD `skipped_unsupported` STATUS TYPE

**File:** `frontend-new/hooks/useFileStatus.ts`

#### Change 2.1: Update FileStatusType (Lines 10-22)

**CURRENT CODE:**
```typescript
export type FileStatusType =
    | "pending"
    | "uploading"
    | "parsing"
    | "processing" // legacy alias for parsing
    | "embedding"
    | "indexing"
    | "indexed" // completed but still receives legacy status upstream
    | "completed"
    | "failed"
    | "skipped"
    | "cancelled"
    | (string & {});
```

**REPLACE WITH:**
```typescript
export type FileStatusType =
    | "pending"
    | "uploading"
    | "parsing"
    | "processing" // legacy alias for parsing
    | "embedding"
    | "indexing"
    | "indexed" // completed but still receives legacy status upstream
    | "completed"
    | "failed"
    | "skipped"
    | "skipped_unsupported" // NEW: Backend returns this for LlamaParse-required or oversized files
    | "cancelled"
    | (string & {});
```

#### Change 2.2: Update Supabase SQL Filter (Line 165)

**CURRENT CODE:**
```typescript
                .not("status", "in", '("completed","failed","skipped","cancelled","indexed")')
```

**REPLACE WITH:**
```typescript
                .not("status", "in", '("completed","failed","skipped","skipped_unsupported","cancelled","indexed")')
```

#### Change 2.3: Update INSERT Event Filter (Line 198)

**CURRENT CODE:**
```typescript
                        if (!["completed", "failed", "skipped", "cancelled", "indexed"].includes(newFile.status)) {
```

**REPLACE WITH:**
```typescript
                        if (!["completed", "failed", "skipped", "skipped_unsupported", "cancelled", "indexed"].includes(newFile.status)) {
```

#### Change 2.4: Update UPDATE Event Filter (Line 206)

**CURRENT CODE:**
```typescript
                            if (["completed", "failed", "skipped", "cancelled", "indexed"].includes(newFile.status)) {
```

**REPLACE WITH:**
```typescript
                            if (["completed", "failed", "skipped", "skipped_unsupported", "cancelled", "indexed"].includes(newFile.status)) {
```

#### Change 2.5: Update getStatusLabel (Lines 239-254)

**CURRENT CODE:**
```typescript
export function getStatusLabel(status: FileStatusType): string {
    const labels: Record<string, string> = {
        pending: "Queued",
        uploading: "Uploading...",
        parsing: "Parsing...",
        processing: "Parsing...",
        embedding: "Embedding...",
        indexing: "Indexing...",
        indexed: "Indexed",
        completed: "Complete",
        failed: "Failed",
        skipped: "Skipped",
        cancelled: "Cancelled",
    };
    return labels[status] || status;
}
```

**REPLACE WITH:**
```typescript
export function getStatusLabel(status: FileStatusType): string {
    const labels: Record<string, string> = {
        pending: "Queued",
        uploading: "Uploading...",
        parsing: "Parsing...",
        processing: "Parsing...",
        embedding: "Embedding...",
        indexing: "Indexing...",
        indexed: "Indexed",
        completed: "Complete",
        failed: "Failed",
        skipped: "Skipped",
        skipped_unsupported: "Unsupported",
        cancelled: "Cancelled",
    };
    return labels[status] || status;
}
```

#### Change 2.6: Update getStatusColor (Lines 259-274)

**CURRENT CODE:**
```typescript
export function getStatusColor(status: FileStatusType): string {
    const colors: Record<string, string> = {
        pending: "text-muted-foreground",
        uploading: "text-blue-500",
        parsing: "text-amber-500",
        processing: "text-amber-500",
        embedding: "text-purple-500",
        indexing: "text-cyan-500",
        indexed: "text-green-500",
        completed: "text-green-500",
        failed: "text-red-500",
        skipped: "text-amber-500",
        cancelled: "text-amber-500",
    };
    return colors[status] || "text-muted-foreground";
}
```

**REPLACE WITH:**
```typescript
export function getStatusColor(status: FileStatusType): string {
    const colors: Record<string, string> = {
        pending: "text-muted-foreground",
        uploading: "text-blue-500",
        parsing: "text-amber-500",
        processing: "text-amber-500",
        embedding: "text-purple-500",
        indexing: "text-cyan-500",
        indexed: "text-green-500",
        completed: "text-green-500",
        failed: "text-red-500",
        skipped: "text-amber-500",
        skipped_unsupported: "text-orange-500",
        cancelled: "text-amber-500",
    };
    return colors[status] || "text-muted-foreground";
}
```

---

### TASK 3: UPDATE PROGRESS MODAL UI

**File:** `frontend-new/components/ingestion/IngestionProgressModal.tsx`

#### Change 3.1: Update Skipped Files Counter (Line 45)

**CURRENT CODE:**
```typescript
    const skippedFiles = files.filter((f) => f.status === "skipped").length;
```

**REPLACE WITH:**
```typescript
    const skippedFiles = files.filter((f) => f.status === "skipped" || f.status === "skipped_unsupported").length;
```

#### Change 3.2: Update Processing Files Filter (Lines 46-48)

**CURRENT CODE:**
```typescript
    const processingFiles = files.filter(
        (f) => !["completed", "indexed", "failed", "skipped", "cancelled"].includes(f.status)
    ).length;
```

**REPLACE WITH:**
```typescript
    const processingFiles = files.filter(
        (f) => !["completed", "indexed", "failed", "skipped", "skipped_unsupported", "cancelled"].includes(f.status)
    ).length;
```

#### Change 3.3: Update isProcessing Check (Line 205)

**CURRENT CODE:**
```typescript
    const isProcessing = !["completed", "indexed", "failed", "skipped", "cancelled"].includes(file.status);
```

**REPLACE WITH:**
```typescript
    const isProcessing = !["completed", "indexed", "failed", "skipped", "skipped_unsupported", "cancelled"].includes(file.status);
```

#### Change 3.4: Update isSkipped Check (Line 208)

**CURRENT CODE:**
```typescript
    const isSkipped = file.status === "skipped";
```

**REPLACE WITH:**
```typescript
    const isSkipped = file.status === "skipped" || file.status === "skipped_unsupported";
```

#### Change 3.5: Add isUnsupported Variable (After Line 209)

**ADD NEW LINE AFTER Line 209:**
```typescript
    const isUnsupported = file.status === "skipped_unsupported";
```

#### Change 3.6: Update statusPillClass for Orange Color (Lines 213-220)

**CURRENT CODE:**
```typescript
    const statusPillClass = cn(
        "text-[11px] font-semibold px-2 py-0.5 rounded-full border",
        isCompleted && "text-green-400 border-green-500/25 bg-green-500/10",
        isFailed && "text-red-400 border-red-500/25 bg-red-500/10",
        isSkipped && "text-amber-400 border-amber-500/25 bg-amber-500/10",
        isCancelled && "text-amber-400 border-amber-500/25 bg-amber-500/10",
        isProcessing && "text-primary border-primary/25 bg-primary/10"
    );
```

**REPLACE WITH:**
```typescript
    const statusPillClass = cn(
        "text-[11px] font-semibold px-2 py-0.5 rounded-full border",
        isCompleted && "text-green-400 border-green-500/25 bg-green-500/10",
        isFailed && "text-red-400 border-red-500/25 bg-red-500/10",
        isUnsupported && "text-orange-400 border-orange-500/25 bg-orange-500/10",
        isSkipped && !isUnsupported && "text-amber-400 border-amber-500/25 bg-amber-500/10",
        isCancelled && "text-amber-400 border-amber-500/25 bg-amber-500/10",
        isProcessing && "text-primary border-primary/25 bg-primary/10"
    );
```

#### Change 3.7: Update getProcessingStages for skipped_unsupported (Line 249)

**CURRENT CODE:**
```typescript
        } else if (file.status === 'completed' || file.status === 'indexed' || file.status === 'skipped') {
```

**REPLACE WITH:**
```typescript
        } else if (file.status === 'completed' || file.status === 'indexed' || file.status === 'skipped' || file.status === 'skipped_unsupported') {
```

---

## 🔌 BACKEND API ENDPOINTS USED BY FRONTEND

### File Upload Flow

```
Frontend                           Backend
────────                           ───────
FileUploadZone.tsx
    │
    ├─► POST /api/v1/upload/url    → Returns presigned Supabase Storage URL
    │   Response: { upload_url, storage_path }
    │
    ├─► PUT {upload_url}           → Direct upload to Supabase Storage
    │
    └─► POST /api/v1/ingest/file   → Triggers ingestion task
        Request: { storage_path, filename, size, metadata }
        Response: { job_id, message }
```

### Ingestion Status Flow

```
Frontend                           Backend (Celery Worker)
────────                           ──────────────────────
useFileStatus.ts
    │
    ├─► SELECT * FROM ingestion_file_status WHERE job_id = ?
    │   (Supabase Realtime subscription)
    │
    └─► Receives UPDATE events with status:
        - pending → parsing → embedding → indexing → completed
        - pending → parsing → skipped_unsupported (if file type unsupported)
        - pending → parsing → failed (if error occurs)
```

### Document Management Flow

```
Frontend                           Backend
────────                           ───────
useDocuments.ts
    │
    ├─► GET /api/v1/documents      → Lists user documents
    │   Response: [{ id, title, source_type, source_id, created_at, ... }]
    │
    ├─► DELETE /api/v1/documents/{id}  → Deletes document + chunks
    │
    └─► React Query cache invalidation on ["documents"] key
```

### Backend Source Identity (Ghost Data Fix)

```
Backend Deduplication Logic (tasks.py):
─────────────────────────────────────────
1. Resolve source_id from:
   - source_id parameter (explicit)
   - metadata.source_id (fallback)
   - metadata.file_id (Google Drive)
   - metadata.storage_path (file uploads)
   - source_url (web crawl)

2. Query: SELECT id, content_hash FROM documents WHERE source_id = ?

3. Decision:
   - No match → INSERT new document
   - Match + same hash → SKIP (touch updated_at)
   - Match + different hash → DELETE old chunks, UPDATE document, INSERT new chunks

Frontend Impact: Document ID is PRESERVED on update, so React Query cache remains valid.
```

---

## ✅ VERIFICATION CHECKLIST

### FileUploadZone.tsx
- [ ] Accept prop includes all 15+ MIME types
- [ ] `.env` files can be uploaded
- [ ] UI hint shows "PDF, Office, CSV, Code, Images & more"
- [ ] Drag-and-drop works for `.xlsx`, `.csv`, `.pptx` files

### useFileStatus.ts
- [ ] `FileStatusType` includes `skipped_unsupported`
- [ ] SQL filter at line 165 includes `skipped_unsupported`
- [ ] INSERT filter at line 198 includes `skipped_unsupported`
- [ ] UPDATE filter at line 206 includes `skipped_unsupported`
- [ ] `getStatusLabel` returns "Unsupported" for `skipped_unsupported`
- [ ] `getStatusColor` returns `text-orange-500` for `skipped_unsupported`

### IngestionProgressModal.tsx
- [ ] `skippedFiles` count includes `skipped_unsupported`
- [ ] `processingFiles` excludes `skipped_unsupported`
- [ ] `isProcessing` is `false` for `skipped_unsupported`
- [ ] `isSkipped` is `true` for `skipped_unsupported`
- [ ] Status pill shows orange color for `skipped_unsupported`
- [ ] Processing stages show all complete for `skipped_unsupported`

---

## 📈 TOTAL CHANGES SUMMARY

| File | Lines Modified | Type |
|------|---------------|------|
| `FileUploadZone.tsx` | 2 locations | Accept prop + UI text |
| `useFileStatus.ts` | 6 locations | Type + SQL + Label + Color |
| `IngestionProgressModal.tsx` | 7 locations | Filters + Logic + Styling |

**Total Modifications:** 15 code locations across 3 files

---

## 🧪 TESTING SCENARIOS

### Test 1: File Upload Acceptance
1. Try uploading `.xlsx` file → Should be accepted
2. Try uploading `.csv` file → Should be accepted
3. Try uploading `.pptx` file → Should be accepted
4. Try uploading `.msg` file → Should be accepted
5. Try uploading `.py` file → Should be accepted
6. Try uploading `.env` file → Should be accepted
7. Try uploading `.jpg` file → Should be accepted

### Test 2: Status Display
1. Upload a file that backend marks as `skipped_unsupported`
2. Verify label shows "Unsupported"
3. Verify color is orange (not amber or red)
4. Verify file doesn't appear stuck in "Processing"

### Test 3: Progress Modal
1. Start multi-file ingestion with mixed files
2. Include one file that will be `skipped_unsupported`
3. Verify skipped count increases correctly
4. Verify processing count doesn't include unsupported file
5. Verify modal shows correct completion state

### Test 4: Backend Integration
1. Upload a `.xls` file without `LLAMA_CLOUD_API_KEY` configured
2. Verify backend returns `skipped_unsupported` status
3. Verify frontend displays "Unsupported" with orange badge
4. Verify file appears in skipped count, not processing count

### Test 5: React Query Cache
1. Upload a file that already exists (same source_id)
2. Backend should atomically replace chunks
3. Frontend document list should update correctly
4. No duplicate documents should appear

---

## 🔄 ROLLBACK PROCEDURE

If issues arise, revert these files to their previous state:
```bash
git checkout HEAD~1 -- frontend-new/components/data-sources/FileUploadZone.tsx
git checkout HEAD~1 -- frontend-new/hooks/useFileStatus.ts
git checkout HEAD~1 -- frontend-new/components/ingestion/IngestionProgressModal.tsx
```

---

## 📚 RELATED DOCUMENTATION

| Document | Location | Description |
|----------|----------|-------------|
| Backend Architectural Audit | `/ArchitecturalAudit_V1_Roadmap.md` | Full backend V1.0 audit and roadmap |
| Parser Router Implementation | `backend/services/parsers.py` | All file processor implementations |
| Worker Tasks Implementation | `backend/worker/tasks.py` | Ingestion pipeline with atomic replacement |
| Database Migration | `supabase/migrations/20260114223000_add_documents_source_id.sql` | source_id column migration |

---

**Document End**


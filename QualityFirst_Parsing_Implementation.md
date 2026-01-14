# 🎯 QUALITY-FIRST PARSING IMPLEMENTATION GUIDE

**Document Version:** 1.0  
**Date:** January 14, 2026  
**Author:** AI Architecture Assistant  
**Status:** IMPLEMENTATION READY

---

## 📋 EXECUTIVE SUMMARY

### The Problem: "Table Blindness"

| Format | Current Parser | Issue |
|--------|----------------|-------|
| PDF | PyMuPDF (local) | Linear text extraction destroys row/column structure |
| Images | LlamaParse (correct) | ✅ Already using quality parser |

**Example of Table Blindness:**
```
Original Table:
| Year | Revenue |
|------|---------|
| 2024 | $11M    |

PyMuPDF Output:        LlamaParse Output:
Year                   | Year | Revenue |
Revenue                |------|---------|
2024                   | 2024 | $11M    |
$11M
```

### The Solution: Quality-First Routing

Prioritize **LlamaParse** for PDFs when the API key is available, falling back to PyMuPDF only when necessary.

---

## 🔗 AFFECTED FILES

| File | Current State | Required Change |
|------|---------------|-----------------|
| `backend/services/parsers.py` | Local-First (PyMuPDF primary) | Quality-First (LlamaParse primary) |
| `backend/core/metrics.py` | Has `pdf_scan_detection_total` | Add new metric labels (optional) |

---

## 📊 CURRENT vs. PROPOSED LOGIC

### Current PDFProcessor Logic (Lines 357-380)

```
┌─────────────────────────────────────────────────────────┐
│                    CURRENT FLOW                         │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  1. ALWAYS process with PyMuPDF first                   │
│           ↓                                             │
│  2. IF LLAMA_CLOUD_API_KEY exists                       │
│     AND extracted_text < 150 chars (likely scanned)     │
│           ↓                                             │
│  3. THEN try LlamaParse as fallback                     │
│           ↓                                             │
│  4. ELSE return PyMuPDF result (tables destroyed)       │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Proposed Quality-First Logic

```
┌─────────────────────────────────────────────────────────┐
│                  QUALITY-FIRST FLOW                     │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  1. IF LLAMA_CLOUD_API_KEY exists                       │
│           ↓                                             │
│  2. Use LlamaParse (result_type="markdown")             │
│     → Tables preserved as Markdown                      │
│           ↓                                             │
│  3. IF LlamaParse fails OR returns empty                │
│           ↓                                             │
│  4. FALLBACK to PyMuPDF (local processing)              │
│                                                         │
│  ELSE (no API key):                                     │
│           ↓                                             │
│  5. Use PyMuPDF directly                                │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 🔧 IMPLEMENTATION DETAILS

### Step 1: Update PDFProcessor.process() Method

**File:** `backend/services/parsers.py`  
**Location:** Lines 357-380  
**Action:** Replace the `process` method

#### BEFORE (Current Code):

```python
def process(self, content: bytes, filename: str) -> ProcessedDocument:
    """Process PDF locally first; fallback to LlamaParse for scanned PDFs."""
    from core.config import settings
    
    local_result = self._process_with_pymupdf(content, filename)

    if settings.LLAMA_CLOUD_API_KEY:
        text_length = 0
        if local_result and local_result.metadata:
            text_length = int(local_result.metadata.get("text_length") or 0)
        is_scanned = self._is_likely_scanned(text_length)
        if pdf_scan_detection_total:
            pdf_scan_detection_total.labels("scanned" if is_scanned else "text").inc()
        if is_scanned:
            if llamaparse_fallback_total:
                llamaparse_fallback_total.labels("pdf").inc()
            try:
                result = self._process_with_llamaparse(content, filename)
                if result and result.chunks:
                    return result
            except Exception as e:
                logger.warning(f"[PDFProcessor] LlamaParse failed, falling back to PyMuPDF: {e}")

    return local_result
```

#### AFTER (Quality-First Code):

```python
def process(self, content: bytes, filename: str) -> ProcessedDocument:
    """
    Process PDF with Quality-First routing strategy.
    
    Strategy:
    1. IF LlamaParse API key is available:
       - Use LlamaParse with result_type="markdown" to preserve table structure
       - This ensures financial reports, technical specs retain row/column context
    2. FALLBACK to PyMuPDF if:
       - No API key configured
       - LlamaParse returns empty result
       - LlamaParse API call fails
    
    This solves the "Table Blindness" issue where standard parsers destroy
    table row/column structure (e.g., "2024 | 11" becomes "2024\n11").
    """
    from core.config import settings
    
    # Quality-First: Prioritize LlamaParse for table preservation
    if settings.LLAMA_CLOUD_API_KEY:
        logger.info(f"[PDFProcessor] Quality-First: Using LlamaParse for {filename}")
        
        # Track quality-first usage
        if llamaparse_fallback_total:
            llamaparse_fallback_total.labels("pdf_quality_first").inc()
        
        try:
            result = self._process_with_llamaparse(content, filename)
            
            if result and result.chunks:
                # Record successful quality-first processing
                if pdf_scan_detection_total:
                    pdf_scan_detection_total.labels("llamaparse_success").inc()
                return result
            else:
                logger.warning(
                    f"[PDFProcessor] LlamaParse returned no chunks for {filename}, "
                    "falling back to PyMuPDF"
                )
                if pdf_scan_detection_total:
                    pdf_scan_detection_total.labels("llamaparse_empty_fallback").inc()
                    
        except Exception as e:
            logger.warning(
                f"[PDFProcessor] LlamaParse failed for {filename}: {e}, "
                "falling back to PyMuPDF"
            )
            if pdf_scan_detection_total:
                pdf_scan_detection_total.labels("llamaparse_error_fallback").inc()
    else:
        logger.info(
            f"[PDFProcessor] No LLAMA_CLOUD_API_KEY configured, "
            f"using PyMuPDF (local) for {filename}"
        )
        if pdf_scan_detection_total:
            pdf_scan_detection_total.labels("local_no_api_key").inc()
    
    # Fallback: Local processing with PyMuPDF
    return self._process_with_pymupdf(content, filename)
```

---

### Step 2: ImageProcessor (NO CHANGES NEEDED)

**File:** `backend/services/parsers.py`  
**Location:** Lines 1235-1239  
**Status:** ✅ Already correctly implemented

```python
class ImageProcessor(BaseProcessor):
    """Processor for images routed to LlamaParse OCR."""

    def process(self, content: bytes, filename: str) -> ProcessedDocument:
        return LlamaParseProcessor(file_type="image").process(content, filename)
```

The `LlamaParseProcessor` already:
- ✅ Checks for `LLAMA_CLOUD_API_KEY` (line 1139)
- ✅ Uses `result_type="markdown"` (line 1168)
- ✅ Returns `unsupported` with reason `llamaparse_unavailable` if no key (line 1144)

---

### Step 3: Factory Routing (NO CHANGES NEEDED)

**File:** `backend/services/parsers.py`  
**Location:** Lines 1335-1362

The factory correctly routes:
- `.pdf` → `PDFProcessor` (line 1336)
- `.jpg`, `.jpeg`, `.png`, `.tiff`, `.bmp` → `ImageProcessor` (lines 1358-1362)

---

## 📈 OBSERVABILITY (Optional Enhancement)

### Current Metrics

The existing metrics in `backend/core/metrics.py`:

| Metric | Labels | Purpose |
|--------|--------|---------|
| `pdf_scan_detection_total` | `scanned`, `text` | Tracks PDF type detection |
| `llamaparse_fallback_total` | `pdf`, `pptx`, `email` | Tracks LlamaParse fallback usage |

### New Metric Labels for Quality-First

Update the labels used in the code to track the new routing:

| Metric | New Label | Purpose |
|--------|-----------|---------|
| `llamaparse_fallback_total` | `pdf_quality_first` | Tracks Quality-First PDF processing |
| `pdf_scan_detection_total` | `llamaparse_success` | Successful LlamaParse processing |
| `pdf_scan_detection_total` | `llamaparse_empty_fallback` | LlamaParse returned empty, fell back |
| `pdf_scan_detection_total` | `llamaparse_error_fallback` | LlamaParse error, fell back |
| `pdf_scan_detection_total` | `local_no_api_key` | No API key, used PyMuPDF |

---

## ✅ VERIFICATION CHECKLIST

### Pre-Implementation

- [ ] Backup current `backend/services/parsers.py`
- [ ] Verify `LLAMA_CLOUD_API_KEY` is set in environment
- [ ] Ensure `llama-parse` package is installed

### Implementation

- [ ] Replace `PDFProcessor.process()` method (lines 357-380)
- [ ] Keep all other methods unchanged (`_process_with_llamaparse`, `_process_with_pymupdf`, etc.)
- [ ] Keep `SCANNED_TEXT_THRESHOLD` and `_is_likely_scanned` (for potential future use)

### Post-Implementation Testing

- [ ] Test 1: PDF with tables + API key → Should produce Markdown tables
- [ ] Test 2: PDF with tables + no API key → Should use PyMuPDF (fallback)
- [ ] Test 3: Image (.jpg/.png) + API key → Should use LlamaParse
- [ ] Test 4: Image + no API key → Should return `skipped_unsupported`
- [ ] Test 5: LlamaParse API failure → Should gracefully fallback to PyMuPDF

### Unit Test Updates

**File:** `backend/tests/unit/test_parsers.py`

Add/update tests for:

```python
def test_pdf_processor_uses_llamaparse_when_api_key_available(mock_settings):
    """Quality-First: PDF should use LlamaParse when API key is set."""
    mock_settings.LLAMA_CLOUD_API_KEY = "test-key"
    # ... test implementation

def test_pdf_processor_falls_back_to_pymupdf_when_no_api_key(mock_settings):
    """Fallback: PDF should use PyMuPDF when no API key."""
    mock_settings.LLAMA_CLOUD_API_KEY = None
    # ... test implementation

def test_pdf_processor_falls_back_on_llamaparse_error(mock_settings, mock_llamaparse):
    """Fallback: PDF should use PyMuPDF when LlamaParse fails."""
    mock_settings.LLAMA_CLOUD_API_KEY = "test-key"
    mock_llamaparse.side_effect = Exception("API Error")
    # ... test implementation
```

---

## 🎯 EXPECTED BEHAVIOR MATRIX

| Scenario | API Key | LlamaParse Result | Final Parser | Output Format |
|----------|---------|-------------------|--------------|---------------|
| PDF with tables | ✅ Set | Success | LlamaParse | Markdown tables |
| PDF with tables | ✅ Set | Empty | PyMuPDF | Linear text |
| PDF with tables | ✅ Set | Error | PyMuPDF | Linear text |
| PDF with tables | ❌ Not set | N/A | PyMuPDF | Linear text |
| Scanned PDF | ✅ Set | Success | LlamaParse | Markdown (OCR) |
| Image (JPG/PNG) | ✅ Set | Success | LlamaParse | Markdown (OCR) |
| Image (JPG/PNG) | ❌ Not set | N/A | N/A | `skipped_unsupported` |

---

## 🔄 ROLLBACK PROCEDURE

If issues arise after deployment:

```bash
# Revert parsers.py to previous version
git checkout HEAD~1 -- backend/services/parsers.py

# Restart workers
sudo systemctl restart celery-worker
```

---

## 📊 COST CONSIDERATIONS

### LlamaParse API Usage

| Document Type | Estimated Cost | Notes |
|---------------|----------------|-------|
| PDF (per page) | ~$0.003 | Depends on complexity |
| Image (per image) | ~$0.003 | OCR processing |

### Recommendations

1. **Monitor API usage** via LlamaCloud dashboard
2. **Set alerts** for unusual spikes
3. **Consider batch processing** for bulk ingestion jobs
4. **Optional:** Add a config flag to disable Quality-First for specific use cases

```python
# Optional: Add to core/config.py
PDF_QUALITY_FIRST_ENABLED: bool = True  # Set to False to use local-first
```

---

## 📚 RELATED DOCUMENTATION

| Document | Location | Description |
|----------|----------|-------------|
| Backend Architectural Audit | `/ArchitecturalAudit_V1_Roadmap.md` | Full backend V1.0 audit |
| Frontend Implementation Guide | `/Frontend_V1_Implementation_Guide.md` | Frontend V1.0 sync |
| Frontend Audit Report | `/Frontend_V1_Audit_Report.md` | Frontend audit results |

---

## 🏁 IMPLEMENTATION COMMAND

To apply this change, run:

```bash
# 1. Edit the file
# Replace PDFProcessor.process() method (lines 357-380) with the new implementation

# 2. Run tests
cd /Users/onronder/axial
source venv/bin/activate
pytest backend/tests/unit/test_parsers.py -v -k "pdf"

# 3. Verify no regressions
pytest backend/tests/unit/ -v --ignore=backend/tests/unit/test_polar_integration.py --ignore=backend/tests/unit/test_stripe_integration.py
```

---

**Document End**


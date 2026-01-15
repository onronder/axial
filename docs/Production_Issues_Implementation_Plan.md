# Production Issues Implementation Plan

## Executive Summary

This document provides a comprehensive implementation plan for all production issues identified in the Railway and Vercel logs analysis. The plan is organized by severity and includes step-by-step instructions, code changes, and verification procedures.

**Last Updated:** 2026-01-14  
**Status:** Ready for Implementation

---

## Issue Categories

### 🔴 CRITICAL (Production-Breaking)

| Issue | Impact | Estimated Fix Time |
|-------|--------|-------------------|
| ClamAV Config Parse Error | Malware scanner unavailable | 15 min |
| LlamaParse 402 Quota Exceeded | PDF parsing degraded | 45 min |

### 🟠 HIGH (Significant)

| Issue | Impact | Estimated Fix Time |
|-------|--------|-------------------|
| Email Profile Lookup 400 Error | Notification emails fail | 20 min |
| Storage Endpoint Trailing Slash | Warnings in logs | 5 min |

### 🟡 MEDIUM (Warnings)

| Issue | Impact | Estimated Fix Time |
|-------|--------|-------------------|
| pkg_resources Deprecation | Future compatibility | 5 min |

---

## 1. ClamAV Configuration Fix

### 1.1 Root Cause Analysis

**Error:**
```
ERROR: Parse error at /etc/clamav/clamd.conf:14: Unknown option RecvTimeout
ERROR: Can't open/parse the config file /etc/clamav/clamd.conf
🔒 [Malware] ClamAV unavailable; defaulting to safe (scanner_unavailable)
```

**Cause:** The `RecvTimeout` option is deprecated in ClamAV 0.104+. Modern ClamAV uses `ReadTimeout` instead.

### 1.2 Files to Modify

- `backend/Dockerfile`
- `backend/Dockerfile.worker`

### 1.3 Implementation

**Replace in both Dockerfiles:**

```dockerfile
# OLD (line 42)
RecvTimeout 300
SendTimeout 300

# NEW
ReadTimeout 300
SendTimeout 300
CommandReadTimeout 30
```

### 1.4 Full ClamAV Configuration Block

```dockerfile
# Configure ClamAV to listen on TCP for instream scanning
RUN cat > /etc/clamav/clamd.conf <<'EOF' \
    && mkdir -p /var/log/clamav /var/run/clamav \
    && chown -R clamav:clamav /var/log/clamav /var/run/clamav
LogTime yes
LogVerbose yes
TCPSocket 3310
TCPAddr 127.0.0.1
Foreground yes
User clamav
FixStaleSocket yes
LocalSocket /var/run/clamav/clamd.ctl
PidFile /var/run/clamav/clamd.pid
LogFile /var/log/clamav/clamav.log
StreamMaxLength 1000M
MaxScanSize 1000M
MaxFileSize 1000M
ReadTimeout 300
SendTimeout 300
CommandReadTimeout 30
EOF
```

### 1.5 Verification

After deployment:
```bash
# Check ClamAV daemon status
clamd --version
cat /var/log/clamav/clamav.log | tail -20
```

Expected: No parse errors, daemon starts successfully.

---

## 2. LlamaParse 3-Tier Fallback Architecture

### 2.1 Root Cause Analysis

**Error:**
```
HTTP Request: POST https://api.cloud.llamaindex.ai/api/parsing/upload "HTTP/1.1 402 Payment Required"
Failed to parse the file: {"detail":"You've exceeded the maximum number of credits for your plan."}
```

**Impact:** PDFs fall back to PyMuPDF, which cannot OCR scanned documents.

### 2.2 Solution Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    PDF Processing Flow                       │
├─────────────────────────────────────────────────────────────┤
│  Tier 1: LlamaParse (Cloud)                                 │
│  ├─ Premium OCR, tables, complex layouts                    │
│  ├─ Circuit Breaker: Auto-blocks on 402/quota errors        │
│  └─ Cooldown: 1 hour after quota exceeded                   │
│                          ↓ (failure)                        │
│  Tier 2: PyMuPDF (Local Fast)                              │
│  ├─ Text layer extraction                                   │
│  ├─ Works for digital PDFs                                  │
│  └─ Check: If <50 tokens, likely scanned → Tier 3          │
│                          ↓ (low content)                    │
│  Tier 3: Tesseract OCR (Local Fallback)                    │
│  ├─ Convert PDF pages to images                             │
│  ├─ Run OCR on each page                                    │
│  └─ 100% local, no cloud dependency                         │
└─────────────────────────────────────────────────────────────┘
```

### 2.3 Files to Modify

- `backend/services/parsers.py`
- `backend/requirements.txt`
- `backend/Dockerfile`
- `backend/Dockerfile.worker`

### 2.4 Dependencies to Add

**requirements.txt:**
```
pytesseract>=0.3.10
pdf2image>=1.16.0
```

**Dockerfile & Dockerfile.worker (apt-get):**
```dockerfile
tesseract-ocr \
tesseract-ocr-eng \
poppler-utils \
```

### 2.5 Circuit Breaker Implementation

```python
# Add to backend/services/parsers.py

from datetime import datetime, timedelta
from enum import Enum
import threading

class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Service blocked
    HALF_OPEN = "half_open"  # Testing recovery

class CircuitBreaker:
    """Thread-safe circuit breaker for cloud API rate limiting."""
    
    def __init__(self, service_name: str, failure_threshold: int = 3, cooldown_seconds: int = 3600):
        self.service_name = service_name
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time = None
        self._lock = threading.Lock()
    
    def can_execute(self) -> tuple[bool, str]:
        """Check if request can proceed."""
        with self._lock:
            if self._state == CircuitState.CLOSED:
                return True, "circuit_closed"
            
            if self._state == CircuitState.OPEN:
                if self._last_failure_time:
                    elapsed = datetime.utcnow() - self._last_failure_time
                    if elapsed > timedelta(seconds=self.cooldown_seconds):
                        self._state = CircuitState.HALF_OPEN
                        return True, "circuit_half_open_test"
                
                remaining = self.cooldown_seconds
                if self._last_failure_time:
                    remaining = max(0, self.cooldown_seconds - int((datetime.utcnow() - self._last_failure_time).total_seconds()))
                return False, f"circuit_open_cooldown_{remaining}s"
            
            return True, "circuit_half_open_test"
    
    def record_success(self):
        with self._lock:
            self._failure_count = 0
            self._state = CircuitState.CLOSED
    
    def record_failure(self, error_type: str = "unknown"):
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = datetime.utcnow()
            
            if error_type in ("402", "quota_exceeded", "payment_required"):
                self._state = CircuitState.OPEN
                logger.warning(f"[CircuitBreaker] {self.service_name}: OPEN (quota error)")
                return
            
            if self._failure_count >= self.failure_threshold:
                self._state = CircuitState.OPEN

# Global circuit breaker instance
LLAMAPARSE_CIRCUIT = CircuitBreaker("LlamaParse", failure_threshold=3, cooldown_seconds=3600)
```

### 2.6 PDFProcessor 3-Tier Implementation

```python
class PDFProcessor(BaseProcessor):
    """Enterprise PDF Processor with 3-Tier Resilient Architecture."""
    
    NOISE_PATTERNS = [
        r"Page\s+\d+\s+(of|/)\s+\d+",
        r"^\d+\s*$",
        r"CONFIDENTIAL",
        r"^\s*©.*$",
    ]
    
    MIN_TOKENS_THRESHOLD = 50
    OCR_QUALITY_THRESHOLD = 100
    
    def process(self, content: bytes, filename: str) -> ProcessedDocument:
        """Process PDF with 3-tier cascading fallback."""
        from core.config import settings
        
        # ─────────────────────────────────────────────────────
        # TIER 1: LlamaParse (Cloud Premium)
        # ─────────────────────────────────────────────────────
        if settings.LLAMA_CLOUD_API_KEY:
            can_execute, reason = LLAMAPARSE_CIRCUIT.can_execute()
            
            if can_execute:
                logger.info(f"[PDFProcessor] Tier 1: Trying LlamaParse for {filename}")
                try:
                    result = self._process_with_llamaparse(content, filename)
                    if result and result.chunks and result.total_tokens >= self.MIN_TOKENS_THRESHOLD:
                        LLAMAPARSE_CIRCUIT.record_success()
                        if pdf_scan_detection_total:
                            pdf_scan_detection_total.labels("tier1_llamaparse_success").inc()
                        return result
                    logger.warning(f"[PDFProcessor] LlamaParse low content ({result.total_tokens if result else 0} tokens)")
                except Exception as e:
                    error_str = str(e).lower()
                    if "402" in error_str or "payment" in error_str or "quota" in error_str:
                        LLAMAPARSE_CIRCUIT.record_failure("402")
                    else:
                        LLAMAPARSE_CIRCUIT.record_failure("error")
                    logger.warning(f"[PDFProcessor] LlamaParse failed: {e}")
            else:
                logger.info(f"[PDFProcessor] Skipping LlamaParse ({reason})")
                if llamaparse_fallback_total:
                    llamaparse_fallback_total.labels(reason).inc()
        
        # ─────────────────────────────────────────────────────
        # TIER 2: PyMuPDF (Fast Local)
        # ─────────────────────────────────────────────────────
        logger.info(f"[PDFProcessor] Tier 2: Trying PyMuPDF for {filename}")
        result = self._process_with_pymupdf(content, filename)
        
        if result and result.chunks and result.total_tokens >= self.MIN_TOKENS_THRESHOLD:
            if pdf_scan_detection_total:
                pdf_scan_detection_total.labels("tier2_pymupdf_success").inc()
            return result
        
        logger.warning(f"[PDFProcessor] PyMuPDF low content ({result.total_tokens if result else 0} tokens), triggering OCR")
        
        # ─────────────────────────────────────────────────────
        # TIER 3: Tesseract OCR (Smart Local Fallback)
        # ─────────────────────────────────────────────────────
        logger.info(f"[PDFProcessor] Tier 3: Trying Tesseract OCR for {filename}")
        try:
            ocr_result = self._process_with_ocr(content, filename)
            if ocr_result and ocr_result.chunks and ocr_result.total_tokens >= self.OCR_QUALITY_THRESHOLD:
                if pdf_scan_detection_total:
                    pdf_scan_detection_total.labels("tier3_ocr_success").inc()
                return ocr_result
            logger.warning(f"[PDFProcessor] OCR also low content for {filename}")
        except OCRNotAvailableException as e:
            logger.warning(f"[PDFProcessor] OCR not available: {e}")
        except Exception as e:
            logger.error(f"[PDFProcessor] OCR failed: {e}")
        
        # Return best available result
        if pdf_scan_detection_total:
            pdf_scan_detection_total.labels("all_tiers_low_content").inc()
        return result or ProcessedDocument(chunks=[], file_type="pdf")
    
    def _process_with_ocr(self, content: bytes, filename: str) -> ProcessedDocument:
        """Tier 3: Tesseract OCR for scanned PDFs."""
        try:
            from pdf2image import convert_from_bytes
            import pytesseract
        except ImportError as e:
            raise OCRNotAvailableException(f"OCR dependencies not installed: {e}")
        
        logger.info(f"[PDFProcessor] Running Tesseract OCR on {filename}")
        
        images = convert_from_bytes(content, dpi=300, fmt='png')
        
        ocr_texts = []
        for page_num, image in enumerate(images, start=1):
            text = pytesseract.image_to_string(image, lang='eng')
            if text.strip():
                cleaned = self._clean_text(text)
                if cleaned.strip():
                    ocr_texts.append(f"[Page {page_num}]\n{cleaned}")
        
        if not ocr_texts:
            return ProcessedDocument(chunks=[], file_type="pdf")
        
        full_text = "\n\n".join(ocr_texts)
        logger.info(f"[PDFProcessor] OCR: {filename}: {len(full_text)} chars from {len(images)} pages")
        
        return self._chunk_text(full_text, filename, parser_name="tesseract_ocr")

class OCRNotAvailableException(Exception):
    """Raised when OCR dependencies are not installed."""
    pass
```

### 2.7 Verification

```python
# Test circuit breaker
from backend.services.parsers import LLAMAPARSE_CIRCUIT

# Simulate quota error
LLAMAPARSE_CIRCUIT.record_failure("402")
can_exec, reason = LLAMAPARSE_CIRCUIT.can_execute()
assert can_exec == False
assert "circuit_open" in reason
```

---

## 3. pkg_resources Deprecation Fix

### 3.1 Root Cause

```
/usr/local/lib/python3.11/site-packages/clamd/__init__.py:6: UserWarning: pkg_resources is deprecated as an API.
```

The `clamd` package uses deprecated `pkg_resources` for version checking.

### 3.2 Solution

Pin `clamd` to a version that doesn't trigger this warning, or suppress the warning.

**requirements.txt:**
```
clamd>=1.0.2,<2.0.0
```

---

## 4. Storage Endpoint URL Fix

### 4.1 Root Cause

```
Storage endpoint URL should have a trailing slash.
```

The Supabase storage endpoint is missing a trailing slash.

### 4.2 Solution

Check environment variable or configuration:

**Environment:**
```
SUPABASE_URL=https://your-project.supabase.co/
```

Note the trailing slash at the end.

---

## 5. Email Profile Lookup Fix

### 5.1 Root Cause

```
HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/user_profiles?select=display_name%2Cfull_name%2Cemail&user_id=... "HTTP/2 400 Bad Request"
📧 [Email] Failed to fetch profile for user ...
```

The query is trying to select `email` from `user_profiles` table, but `email` may not be a column in that table.

### 5.2 Files to Modify

- `backend/worker/tasks.py`

### 5.3 Implementation

```python
# In worker/tasks.py, find the profile lookup code and fix it:

# OLD:
user_data = db.table("user_profiles").select(
    "display_name,full_name,email"
).eq("user_id", user_id).maybe_single().execute()

# NEW (email is in auth.users, not user_profiles):
user_data = db.table("user_profiles").select(
    "display_name,full_name"
).eq("user_id", user_id).maybe_single().execute()
```

---

## Implementation Checklist

### Phase 1: Critical Fixes (Deploy ASAP) ✅ COMPLETED

- [x] **1.1** Update `RecvTimeout` → `ReadTimeout` in `backend/Dockerfile`
- [x] **1.2** Update `RecvTimeout` → `ReadTimeout` in `backend/Dockerfile.worker`
- [x] **1.3** Add `CommandReadTimeout 30` to ClamAV config
- [ ] **1.4** Deploy and verify ClamAV starts correctly

### Phase 2: High Priority Fixes ✅ COMPLETED

- [x] **2.1** Add `pytesseract` and `pdf2image` to `requirements.txt`
- [x] **2.2** Add `tesseract-ocr`, `tesseract-ocr-eng`, `poppler-utils` to Dockerfiles
- [x] **2.3** Implement `CircuitBreaker` class in `parsers.py`
- [x] **2.4** Update `PDFProcessor.process()` with 3-tier logic
- [x] **2.5** Add `_process_with_ocr()` method
- [x] **2.6** Fix email profile lookup query
- [ ] **2.7** Deploy and test PDF processing

### Phase 3: Medium Priority Fixes ✅ COMPLETED

- [x] **3.1** Pin `clamd>=1.0.2,<2.0.0` in `requirements.txt`
- [ ] **3.2** Verify Supabase URL has trailing slash (environment config)

---

## Rollback Procedure

If issues arise after deployment:

1. **ClamAV:** Revert Dockerfile changes and redeploy
2. **PDFProcessor:** The 3-tier system gracefully degrades; to revert, remove circuit breaker and OCR tier
3. **Dependencies:** Unpin and redeploy

---

## Success Metrics

| Metric | Before | Target |
|--------|--------|--------|
| ClamAV Availability | 0% | 100% |
| PDF Parsing Success Rate | ~60% (scanned fail) | 95%+ |
| Error Logs (per hour) | ~50 | <5 |
| LlamaParse Quota Handling | Crash | Graceful fallback |

---

## Testing Commands

```bash
# Test ClamAV
docker exec -it backend clamd --version
docker exec -it backend clamdscan --version

# Test PDF processing
curl -X POST http://localhost:8080/api/v1/uploads/upload-url \
  -H "Content-Type: application/json" \
  -d '{"filename": "test.pdf", "content_type": "application/pdf"}'

# Test OCR availability
docker exec -it backend python -c "import pytesseract; print(pytesseract.get_tesseract_version())"
docker exec -it backend python -c "from pdf2image import convert_from_bytes; print('pdf2image OK')"
```

---

## References

- [ClamAV Configuration Options](https://docs.clamav.net/manual/Usage/Configuration.html)
- [LlamaParse API](https://docs.llamaindex.ai/en/stable/llama_cloud/llama_parse.html)
- [Tesseract OCR](https://tesseract-ocr.github.io/)
- [Circuit Breaker Pattern](https://martinfowler.com/bliki/CircuitBreaker.html)


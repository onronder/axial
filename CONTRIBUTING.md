# Contributing to Axial

## Code Standards

### Backend (Python/FastAPI)

**Error Handling:**
- Always use `api_error()` from `api.v1.error_utils` — never raw `raise HTTPException`.
- `api_error()` logs the full exception server-side and returns a sanitized message to the user.
- If you must use `HTTPException` directly (e.g., in middleware), add `# ALLOWED` comment.

```python
# Good
from api.v1.error_utils import api_error, ApiErrorCode
raise api_error(ApiErrorCode.PROCESSING_ERROR, e, "my_operation")

# Bad — leaks internal details to users
raise HTTPException(500, f"Database error: {e}")
```

**Exception Handling:**
- Never use bare `except:` — always use `except Exception as e:`.
- Never use `except Exception: pass` without logging.
- Catch specific exceptions where possible (`except ValueError`, `except ConnectionError`).

**Validation:**
- Use `EmailStr` for email inputs in request models.
- Use `Field(gt=0)` for positive numeric constraints.
- Use `Field(max_length=N)` for string length limits on user inputs.

**Rate Limiting:**
- All mutation endpoints (POST, PUT, DELETE) must have `@limiter.limit()`.
- The endpoint must accept `request: Request` as the first parameter for slowapi.

**Linting:**
- Run `ruff check backend/` before committing.

### Frontend (TypeScript/React)

**Error Display:**
- Always use `toast()` from `@/lib/toast` — never `alert()`.
- Use `extractErrorMessage()` from `lib/error-handling.ts` for error display.
- Never show raw `error.message` to users in production.

```typescript
// Good
import { toast } from "@/lib/toast";
toast({ title: "Error", description: "Something went wrong.", variant: "destructive" });

// Bad — blocks UI, no styling
alert("Something went wrong");
```

**Accessibility:**
- Interactive `<div>` elements need `role="button"`, `tabIndex={0}`, and keyboard handlers.
- Use semantic HTML (`<button>`, `<a>`) where possible.

**Performance:**
- Lazy-load heavy libraries (Recharts, etc.) with `next/dynamic`.
- Use `useMemo` for expensive derivations.

### Commit Messages

Follow conventional commit format:
- `feat:` — new feature
- `fix:` — bug fix
- `test:` — adding/updating tests
- `refactor:` — code restructuring (no behavior change)
- `docs:` — documentation only
- `chore:` — build/CI changes

### Testing

- Every new API endpoint must have unit tests.
- Test file naming: `tests/test_<module>.py` for backend, `*.test.tsx` for frontend.
- Run backend tests: `cd backend && python -m pytest tests/ -x`
- Run frontend build: `cd frontend-new && npm run build`

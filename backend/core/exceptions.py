"""
Custom Exception Types for Production-Grade Error Handling

Provides specific exception types for better error categorization,
handling, and reporting.
"""


# =============================================================================
# Base Exceptions
# =============================================================================

class AxialError(Exception):
    """Base exception for all Axial-specific errors."""

    def __init__(self, message: str, details: dict | None = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class AxialRetryableError(AxialError):
    """Base for errors that should trigger automatic retry."""
    pass


class AxialPermanentError(AxialError):
    """Base for errors that should NOT be retried."""
    pass


# =============================================================================
# Resource Errors
# =============================================================================

class QuotaExceededError(AxialPermanentError):
    """User has exceeded their quota."""
    pass


class FileTooLargeError(AxialPermanentError):
    """File exceeds maximum allowed size."""
    pass


class UnsupportedFileTypeError(AxialPermanentError):
    """File type is not supported."""
    pass


# =============================================================================
# External Service Errors
# =============================================================================

class ExternalServiceError(AxialRetryableError):
    """Base for external service failures."""
    pass


class OpenAIError(ExternalServiceError):
    """OpenAI API error."""
    pass


class SupabaseError(ExternalServiceError):
    """Supabase error."""
    pass


class LlamaParseError(ExternalServiceError):
    """LlamaParse service error."""
    pass


class GoogleDriveError(ExternalServiceError):
    """Google Drive API error."""
    pass


# =============================================================================
# Processing Errors
# =============================================================================

class ProcessingError(AxialError):
    """Base for document processing errors."""
    pass


class ParsingError(ProcessingError):
    """Document parsing failed."""
    pass


class ChunkingError(ProcessingError):
    """Document chunking failed."""
    pass


class EmbeddingError(ProcessingError):
    """Embedding generation failed."""
    pass


class IndexingError(ProcessingError):
    """Document indexing failed."""
    pass


# =============================================================================
# Timeout Errors
# =============================================================================

class TimeoutError(AxialRetryableError):
    """Operation exceeded timeout."""

    def __init__(self, operation: str, timeout_seconds: int):
        message = f"{operation} exceeded timeout of {timeout_seconds}s"
        super().__init__(message, {"operation": operation, "timeout": timeout_seconds})


# =============================================================================
# Circuit Breaker Errors
# =============================================================================

class CircuitBreakerOpenError(AxialRetryableError):
    """Circuit breaker is open, service unavailable."""

    def __init__(self, service: str):
        message = f"Circuit breaker open for {service}"
        super().__init__(message, {"service": service})


# =============================================================================
# Authentication/Authorization Errors
# =============================================================================

class AuthenticationError(AxialPermanentError):
    """Authentication failed."""
    pass


class AuthorizationError(AxialPermanentError):
    """User not authorized for this action."""
    pass


class InvalidTokenError(AuthenticationError):
    """Token is invalid or expired."""
    pass


# =============================================================================
# Validation Errors
# =============================================================================

class ValidationError(AxialPermanentError):
    """Input validation failed."""

    def __init__(self, field: str, message: str):
        super().__init__(f"Validation error for {field}: {message}", {"field": field})


# =============================================================================
# Database Errors
# =============================================================================

class DatabaseError(AxialRetryableError):
    """Database operation failed."""
    pass


class RecordNotFoundError(AxialPermanentError):
    """Database record not found."""
    pass


class DuplicateRecordError(AxialPermanentError):
    """Record already exists."""
    pass


# =============================================================================
# Memory Errors
# =============================================================================

class MemoryLimitExceededError(AxialRetryableError):
    """Process exceeded memory limit."""

    def __init__(self, current_mb: int, limit_mb: int):
        message = f"Memory limit exceeded: {current_mb}MB / {limit_mb}MB"
        super().__init__(message, {"current_mb": current_mb, "limit_mb": limit_mb})


# =============================================================================
# Helper Functions
# =============================================================================

def is_retryable(error: Exception) -> bool:
    """Check if an error should trigger automatic retry."""
    return isinstance(error, AxialRetryableError)


def get_error_category(error: Exception) -> str:
    """Get error category for metrics/logging."""
    if isinstance(error, QuotaExceededError):
        return "quota"
    elif isinstance(error, ExternalServiceError):
        return "external_service"
    elif isinstance(error, ProcessingError):
        return "processing"
    elif isinstance(error, TimeoutError):
        return "timeout"
    elif isinstance(error, CircuitBreakerOpenError):
        return "circuit_breaker"
    elif isinstance(error, AuthenticationError):
        return "authentication"
    elif isinstance(error, ValidationError):
        return "validation"
    elif isinstance(error, DatabaseError):
        return "database"
    elif isinstance(error, MemoryLimitExceededError):
        return "memory"
    else:
        return "unknown"

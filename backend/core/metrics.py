"""
Prometheus Metrics for Production Monitoring

Tracks retry attempts, timeouts, circuit breaker states, and memory usage.
"""

import logging

try:
    from prometheus_client import Counter, Histogram, Gauge, Info
    METRICS_ENABLED = True
except Exception:
    METRICS_ENABLED = False

    class _DummyMetric:
        def __init__(self, *args, **kwargs):
            pass

        def labels(self, *args, **kwargs):
            return self

        def inc(self, *args, **kwargs):
            return None

        def observe(self, *args, **kwargs):
            return None

        def set(self, *args, **kwargs):
            return None

        def info(self, *args, **kwargs):
            return None

    Counter = Histogram = Gauge = Info = _DummyMetric

logger = logging.getLogger(__name__)
if not METRICS_ENABLED:
    logger.warning("📊 Prometheus client not available; metrics disabled")

# =============================================================================
# Retry Metrics
# =============================================================================

retry_total = Counter(
    'pipeline_retry_total',
    'Total number of retry attempts',
    ['service', 'operation']
)

retry_success = Counter(
    'pipeline_retry_success',
    'Successful retries after initial failure',
    ['service', 'operation']
)

retry_failure = Counter(
    'pipeline_retry_failure',
    'Failed retries (exhausted all attempts)',
    ['service', 'operation']
)

# =============================================================================
# Timeout Metrics
# =============================================================================

timeout_total = Counter(
    'pipeline_timeout_total',
    'Total number of timeouts',
    ['operation']
)

operation_duration = Histogram(
    'pipeline_operation_duration_seconds',
    'Duration of operations in seconds',
    ['operation'],
    buckets=[1, 5, 10, 30, 60, 120, 300, 600]  # 1s to 10min
)

# =============================================================================
# Circuit Breaker Metrics
# =============================================================================

circuit_breaker_state = Gauge(
    'circuit_breaker_state',
    'Circuit breaker state (0=closed, 1=open, 2=half-open)',
    ['service']
)

circuit_breaker_failures = Counter(
    'circuit_breaker_failures_total',
    'Total failures recorded by circuit breaker',
    ['service']
)

circuit_breaker_opens = Counter(
    'circuit_breaker_opens_total',
    'Total times circuit breaker opened',
    ['service']
)

# =============================================================================
# Memory Metrics
# =============================================================================

MEMORY_USAGE = Gauge(
    'pipeline_memory_usage_percent',
    'Current memory usage percentage'
)

MEMORY_AVAILABLE_MB = Gauge(
    'pipeline_memory_available_mb',
    'Available memory in megabytes'
)

MEMORY_WARNINGS = Counter(
    'pipeline_memory_warnings_total',
    'Total memory warnings (>85% usage)'
)

MEMORY_CRITICAL = Counter(
    'pipeline_memory_critical_total',
    'Total memory critical events (>95% usage)'
)

PROCESS_CPU_PERCENT = Gauge(
    'pipeline_process_cpu_percent',
    'CPU usage percent for worker process'
)

OPEN_FILES = Gauge(
    'pipeline_process_open_files',
    'Open file handles for worker process'
)

memory_usage_percent = MEMORY_USAGE
memory_available_mb = MEMORY_AVAILABLE_MB
memory_warnings = MEMORY_WARNINGS
memory_critical = MEMORY_CRITICAL

# =============================================================================
# Task Metrics
# =============================================================================

task_total = Counter(
    'pipeline_task_total',
    'Total tasks processed',
    ['task_name', 'status']
)

task_duration = Histogram(
    'pipeline_task_duration_seconds',
    'Task duration in seconds',
    ['task_name'],
    buckets=[10, 30, 60, 120, 300, 600, 1800, 3600]  # 10s to 1hr
)

# =============================================================================
# Progress Update Metrics
# =============================================================================

status_updates_total = Counter(
    'pipeline_status_updates_total',
    'Total status/progress updates written',
    ['scope', 'status']
)

# =============================================================================
# Job Counter Metrics
# =============================================================================

job_counters_missing = Counter(
    'job_counters_missing_total',
    'Redis job counters missing or unavailable',
    ['job_type']
)

job_counters_reconciled = Counter(
    'job_counters_reconciled_total',
    'Job counters reconciled using database counts',
    ['job_type']
)

job_counters_finalize = Counter(
    'job_counters_finalize_total',
    'Job finalizations triggered',
    ['job_type', 'source']
)

# =============================================================================
# Document Processing Metrics
# =============================================================================

documents_processed = Counter(
    'pipeline_documents_processed_total',
    'Total documents processed',
    ['source_type', 'status']
)

chunks_generated = Counter(
    'pipeline_chunks_generated_total',
    'Total chunks generated',
    ['source_type']
)

embeddings_generated = Counter(
    'pipeline_embeddings_generated_total',
    'Total embeddings generated'
)

idempotency_hits = Counter(
    'pipeline_idempotency_hits_total',
    'Total idempotent reuses of existing documents',
    ['source_type']
)

parser_rejections = Counter(
    'pipeline_parser_rejections_total',
    'Total parser rejections and skips',
    ['reason', 'source_type']
)

pdf_scan_detection_total = Counter(
    'pipeline_pdf_scan_detection_total',
    'PDF scan detection results',
    ['result']
)

llamaparse_fallback_total = Counter(
    'pipeline_llamaparse_fallback_total',
    'LlamaParse fallback attempts for local-first parsers',
    ['file_type']
)

dedup_actions_total = Counter(
    'pipeline_dedup_actions_total',
    'Deduplication actions taken during ingestion',
    ['action', 'source_type']
)

# =============================================================================
# Dead Letter Queue Metrics
# =============================================================================

DLQ_TASKS_TOTAL = Gauge(
    'dlq_tasks_total',
    'Total tasks in dead letter queue',
    ['status']
)

DLQ_RETRY_ATTEMPTS = Counter(
    'dlq_retries_total',
    'Total DLQ retry attempts',
    ['result']  # success or failure
)

DLQ_PERMANENTLY_FAILED = Counter(
    'dlq_permanently_failed_total',
    'Total DLQ tasks permanently failed'
)

DLQ_TASKS_PENDING = Gauge(
    'dlq_tasks_pending',
    'Pending tasks in dead letter queue'
)

dlq_tasks_total = DLQ_TASKS_TOTAL
dlq_retries_total = DLQ_RETRY_ATTEMPTS

# =============================================================================
# System Info
# =============================================================================

system_info = Info(
    'pipeline_system_info',
    'System information'
)

# Set initial system info
try:
    import platform
    system_info.info({
        'python_version': platform.python_version(),
        'system': platform.system(),
        'machine': platform.machine()
    })
except Exception as e:
    logger.warning(f"Failed to set system info: {e}")

logger.info("📊 Prometheus metrics initialized")

"""
Prometheus Metrics for Production Monitoring

Tracks retry attempts, timeouts, circuit breaker states, and memory usage.
"""

from prometheus_client import Counter, Histogram, Gauge, Info
import logging

logger = logging.getLogger(__name__)

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

memory_usage_percent = Gauge(
    'pipeline_memory_usage_percent',
    'Current memory usage percentage'
)

memory_available_mb = Gauge(
    'pipeline_memory_available_mb',
    'Available memory in megabytes'
)

memory_warnings = Counter(
    'pipeline_memory_warnings_total',
    'Total memory warnings (>85% usage)'
)

memory_critical = Counter(
    'pipeline_memory_critical_total',
    'Total memory critical events (>95% usage)'
)

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

# =============================================================================
# Dead Letter Queue Metrics
# =============================================================================

dlq_tasks_total = Gauge(
    'dlq_tasks_total',
    'Total tasks in dead letter queue',
    ['status']
)

dlq_retries_total = Counter(
    'dlq_retries_total',
    'Total DLQ retry attempts',
    ['result']  # success or failure
)

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

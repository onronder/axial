# Docker Health Check Reference Documentation
#
# This file contains health check configurations to be added to the respective
# Dockerfiles for each service. These are NOT standalone Dockerfile instructions.
#
# =============================================================================
# Backend (FastAPI) Health Check
# =============================================================================
# Add to: docker/backend.dockerfile
#
# HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
#     CMD python -c "import requests; requests.get('http://localhost:8000/health', timeout=5).raise_for_status()" || exit 1
#
# =============================================================================
# Celery Worker Health Check
# =============================================================================
# Add to: docker/celery-worker.dockerfile
#
# HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
#     CMD celery -A core.celery_app inspect ping -d celery@$HOSTNAME || exit 1
#
# =============================================================================
# Celery Beat Health Check  
# =============================================================================
# Add to: docker/celery-beat.dockerfile
#
# HEALTHCHECK --interval=60s --timeout=10s --start-period=40s --retries=3 \
#     CMD pgrep -f "celery.*beat" || exit 1
#
# =============================================================================
# Notes
# =============================================================================
# - Each service should have only ONE HEALTHCHECK instruction
# - The HEALTHCHECK must be in a valid Dockerfile with a FROM instruction
# - These configurations assume the respective services are running on their ports

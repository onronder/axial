"""
Health Check Endpoints for Kubernetes/Docker

Provides readiness and liveness probes for container orchestration.
"""

import logging
import psutil
from fastapi import APIRouter, Response, status
from core.db import get_supabase
from core.celery_app import celery_app

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check():
    """
    Basic health check endpoint.
    
    Returns 200 if service is running.
    """
    return {"status": "healthy", "service": "axial-api"}


@router.get("/health/ready")
async def readiness_probe():
    """
    Readiness probe for Kubernetes.
    
    Checks if the service is ready to accept traffic:
    - Database connection
    - Celery connection
    - Memory usage
    
    Returns 200 if ready, 503 if not ready.
    """
    checks = {
        "database": False,
        "celery": False,
        "memory": False
    }
    
    # Check database connection
    try:
        supabase = get_supabase()
        # Simple query to verify connection
        result = supabase.table("ingestion_jobs").select("id").limit(1).execute()
        checks["database"] = True
    except Exception as e:
        logger.error(f"Database readiness check failed: {e}")
    
    # Check Celery connection
    try:
        # Ping Celery workers
        celery_app.control.ping(timeout=1.0)
        checks["celery"] = True
    except Exception as e:
        logger.error(f"Celery readiness check failed: {e}")
    
    # Check memory usage
    try:
        memory = psutil.virtual_memory()
        # Consider ready if memory usage < 90%
        checks["memory"] = memory.percent < 90
    except Exception as e:
        logger.error(f"Memory readiness check failed: {e}")
    
    # Service is ready if all checks pass
    all_ready = all(checks.values())
    
    if all_ready:
        return {
            "status": "ready",
            "checks": checks
        }
    else:
        return Response(
            content={"status": "not_ready", "checks": checks},
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE
        )


@router.get("/health/live")
async def liveness_probe():
    """
    Liveness probe for Kubernetes.
    
    Checks if the service is alive and should not be restarted.
    This is a lighter check than readiness.
    
    Returns 200 if alive, 503 if dead.
    """
    try:
        # Check if process is responsive
        memory = psutil.virtual_memory()
        
        # Consider dead if memory usage > 95% (likely OOM soon)
        if memory.percent > 95:
            logger.error(f"Liveness check failed: Memory usage at {memory.percent}%")
            return Response(
                content={"status": "unhealthy", "reason": "memory_critical"},
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        
        return {"status": "alive"}
    
    except Exception as e:
        logger.error(f"Liveness check failed: {e}")
        return Response(
            content={"status": "unhealthy", "reason": str(e)},
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE
        )


@router.get("/health/startup")
async def startup_probe():
    """
    Startup probe for Kubernetes.
    
    Checks if the application has finished starting up.
    More lenient than readiness probe.
    
    Returns 200 when startup is complete.
    """
    try:
        # Check if database is accessible
        supabase = get_supabase()
        supabase.table("ingestion_jobs").select("id").limit(1).execute()
        
        return {"status": "started"}
    
    except Exception as e:
        logger.error(f"Startup check failed: {e}")
        return Response(
            content={"status": "starting", "reason": str(e)},
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE
        )

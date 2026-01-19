#!/bin/bash
#
# Ghost Protocol: Start ClamAV daemon before the application
#
# This script ensures ClamAV is running for malware scanning
# before the FastAPI/Celery worker starts.
#
# Usage:
#   CMD ["/start-with-clamav.sh"]  # In Dockerfile
#   Or override at runtime: docker run ... /start-with-clamav.sh
#
# Environment Variables:
#   SKIP_CLAMAV=true      - Skip ClamAV entirely (for lightweight dev)
#   SKIP_FRESHCLAM=true   - Skip virus definition update (for faster startup)
#

set -e

# =============================================================================
# Development Bypass: Skip ClamAV entirely if SKIP_CLAMAV=true
# =============================================================================
if [ "$SKIP_CLAMAV" = "true" ]; then
    echo "⚠️  [GhostProtocol] SKIP_CLAMAV=true - Running WITHOUT malware scanning"
    echo "⚠️  [GhostProtocol] This mode is for DEVELOPMENT ONLY!"
    echo "🚀 [GhostProtocol] Starting application (no ClamAV)..."
    exec uvicorn main:app --host 0.0.0.0 --port 8000
fi

echo "🛡️  [GhostProtocol] Starting ClamAV daemon..."

# Update virus definitions (can be slow on first run)
# Skip in dev if already updated to speed up startup
if [ ! -f /var/lib/clamav/main.cvd ] || [ "$SKIP_FRESHCLAM" = "true" ]; then
    if [ "$SKIP_FRESHCLAM" != "true" ]; then
        echo "📥 [GhostProtocol] Updating virus definitions..."
        freshclam --quiet || echo "⚠️  Freshclam update failed (continuing anyway)"
    else
        echo "⏭️  [GhostProtocol] Skipping freshclam (SKIP_FRESHCLAM=true)"
    fi
fi

# Start ClamAV daemon in background
echo "🚀 [GhostProtocol] Starting clamd..."
clamd &

# Wait for clamd to be ready (TCP socket)
echo "⏳ [GhostProtocol] Waiting for clamd to be ready..."
max_wait=30
waited=0
while ! nc -z 127.0.0.1 3310 2>/dev/null; do
    if [ $waited -ge $max_wait ]; then
        echo "❌ [GhostProtocol] Clamd failed to start within ${max_wait}s"
        echo "⚠️  [GhostProtocol] Continuing without ClamAV - malware scanning may be unavailable"
        break
    fi
    sleep 1
    waited=$((waited + 1))
done

if [ $waited -lt $max_wait ]; then
    echo "✅ [GhostProtocol] ClamAV daemon is ready"
fi

# Start the main application
echo "🚀 [GhostProtocol] Starting application..."
exec uvicorn main:app --host 0.0.0.0 --port 8000

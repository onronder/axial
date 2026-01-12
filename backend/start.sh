#!/bin/bash
set -e

# Ensure log directories exist and are writable
mkdir -p /var/log/clamav
mkdir -p /var/run/clamav
chown -R clamav:clamav /var/log/clamav /var/run/clamav || true
chmod -R 775 /var/log/clamav /var/run/clamav || true

# Update virus definitions (best effort)
if command -v freshclam >/dev/null 2>&1; then
  gosu clamav freshclam --stdout || true
fi

# Start ClamAV daemon in the background with TCP listener for instream scans
if command -v clamd >/dev/null 2>&1; then
  echo "🛡️ Starting ClamAV daemon..."
  gosu clamav clamd --config-file=/etc/clamav/clamd.conf --foreground=yes &
  # Give clamd a moment to come up
  sleep 3
fi

# Ensure PORT is set (Railway injects it for web; default to 8000 for local)
: "${PORT:=8000}"

# If uvicorn is requested, force the resolved port regardless of caller args
if [ "$#" -gt 0 ] && [ "$1" = "uvicorn" ]; then
  shift
  exec gosu appuser uvicorn "$@" --port "${PORT}"
fi

# Default command: uvicorn app server (override by passing args)
if [ "$#" -gt 0 ]; then
  exec gosu appuser "$@"
else
  exec gosu appuser uvicorn main:app --host 0.0.0.0 --port "${PORT}"
fi

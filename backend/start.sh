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

# Start ClamAV daemon in the background with log to stdout
if command -v clamd >/dev/null 2>&1; then
  gosu clamav clamd --foreground=yes --stdout &
  sleep 2
fi

# Default command: uvicorn app server (override by passing args)
if [ "$#" -gt 0 ]; then
  exec gosu appuser "$@"
else
  exec gosu appuser uvicorn main:app --host 0.0.0.0 --port "${PORT:-8000}"
fi

# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    gcc \
    libpython3-dev \
    libmagic1 \
    libgl1 \
    libglib2.0-0 \
    clamav-daemon \
    clamav-freshclam \
    libclamav-dev \
    gosu \
    && rm -rf /var/lib/apt/lists/*

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
RecvTimeout 300
SendTimeout 300
EOF

# Update virus definitions during build (best effort)
RUN freshclam || true

# Install Python dependencies
COPY requirements.txt .

# CACHE BUSTER: Force rebuild to install gevent
ARG CACHEBUST=2026010516450001

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    # Force install gevent to ensure it's available
    && pip install --no-cache-dir --force-reinstall gevent>=23.9.1 \
    && python -c "import gevent; print(f'✅ gevent {gevent.__version__} installed')"

# Copy application code
COPY . .

# Start script to launch ClamAV daemon before app
RUN chmod +x /app/start.sh || true

# Create a non-root user (appuser). We keep root as runtime to allow clamd start,
# and drop to appuser inside start.sh for the app/worker processes.
RUN groupadd -r appuser && useradd -r -g appuser appuser \
    && chown -R appuser:appuser /app

# Run the application
# Railway injects PORT environment variable - we must use it
CMD ["/app/start.sh"]

FROM python:3.11-slim

# Install system dependencies for Unstructured (OCR, PDF, Magic)
# and ClamAV for Ghost Protocol malware scanning
RUN apt-get update && apt-get install -y \
    libmagic-dev \
    poppler-utils \
    tesseract-ocr \
    # Ghost Protocol: ClamAV for malware scanning
    clamav \
    clamav-daemon \
    clamav-freshclam \
    && rm -rf /var/lib/apt/lists/*

# Configure ClamAV (Ghost Protocol requirement)
# Create necessary directories and set permissions
RUN mkdir -p /var/run/clamav && \
    chown clamav:clamav /var/run/clamav && \
    mkdir -p /var/lib/clamav && \
    chown -R clamav:clamav /var/lib/clamav

# Configure clamd to use TCP socket for clamd Python library
RUN echo "TCPSocket 3310\nTCPAddr 127.0.0.1" >> /etc/clamav/clamd.conf && \
    sed -i 's/^LocalSocket/#LocalSocket/' /etc/clamav/clamd.conf

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Copy the startup script for ClamAV + uvicorn
COPY docker/start-with-clamav.sh /start-with-clamav.sh
RUN chmod +x /start-with-clamav.sh

# =============================================================================
# GHOST PROTOCOL: Production Default with ClamAV
# =============================================================================
# In production, ClamAV is REQUIRED for Zero-Retention compliance.
# The start-with-clamav.sh script ensures ClamAV daemon is ready before app starts.
#
# For lightweight development without ClamAV:
#   docker run --entrypoint uvicorn ... main:app --host 0.0.0.0 --port 8000
# Or set env var SKIP_CLAMAV=true in the startup script
CMD ["/start-with-clamav.sh"]

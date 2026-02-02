FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY . .

# =============================================================================
# SECURITY FIX: Create non-root user for running the application
# =============================================================================
# Running as root inside containers is a security risk - if the app is
# compromised, the attacker gains root access to the container.
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Change ownership of app directory to non-root user
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8501

# Run Streamlit in Headless Mode (No email prompt, Dark Theme enforced)
CMD ["streamlit", "run", "app.py", \
    "--server.address=0.0.0.0", \
    "--server.headless=true", \
    "--browser.gatherUsageStats=false", \
    "--theme.base=dark"]

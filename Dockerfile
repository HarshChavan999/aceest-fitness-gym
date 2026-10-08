# =========================================================================
# ACEest Fitness & Gym — Production Dockerfile
# Optimized for size, security, and reproducibility
# =========================================================================

FROM python:3.11-slim

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_ENV=production \
    PORT=5000

# Set working directory
WORKDIR /app

# Create non-privileged system user for container security hardening
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -s /bin/sh -M appuser

# Install dependencies (cached in layer)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

# Set file ownership to non-root user
RUN chown -R appuser:appgroup /app

# Switch to non-root execution
USER appuser

# Expose web service port
EXPOSE 5000

# Healthcheck probe hitting internal health endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD python3 -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5000/health')" || exit 1

# Launch application via production-grade WSGI server Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--threads", "4", "--access-logfile", "-", "app:app"]

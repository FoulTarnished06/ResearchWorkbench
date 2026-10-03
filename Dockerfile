# Multi-stage production Dockerfile for AI Research Workbench v3.0
# Compatible with Hugging Face Spaces (User 1000, Port 7860), Render.com ($PORT), and Local Docker
FROM python:3.11-slim

# Set environment flags for Python in containers
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=7860

# Install essential system dependencies (curl for healthchecks, libglib for PyMuPDF)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Create non-root application user for container security (Hugging Face Spaces compatible)
RUN useradd -m -u 1000 appuser

WORKDIR /app

# Install Python requirements
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --upgrade pip && \
    pip install -r /app/backend/requirements.txt

# Copy application source code
COPY --chown=appuser:appuser . /app

# Ensure uploads and cache directories are writable
RUN mkdir -p /app/backend/uploads && \
    chown -R appuser:appuser /app

USER appuser

# Expose container port (Default 7860 matches Hugging Face Spaces; configurable via PORT env)
EXPOSE 7860

# Healthcheck targeting FastAPI health endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:${PORT:-7860}/api/health || exit 1

# Start Uvicorn production server
CMD ["sh", "-c", "uvicorn backend.app:app --host 0.0.0.0 --port ${PORT:-7860}"]

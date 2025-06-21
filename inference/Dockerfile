# Use official Python runtime as base image
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file early to leverage Docker cache
COPY ../requirements.txt .

# Install large dependencies first (improves caching & stability)
RUN pip install --timeout=300 --retries=10 --no-cache-dir \
    torch tensorflow

# Install remaining dependencies
RUN pip install --timeout=300 --retries=10 --no-cache-dir -r requirements.txt

# Copy application files
COPY inference/inference_api.py .
COPY configs/ ./configs/
COPY models/ ./models/

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Set entry point
CMD ["uvicorn", "inference_api:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]

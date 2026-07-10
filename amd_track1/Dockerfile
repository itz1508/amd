# AMD Track 1 General-Purpose AI Agent
# Multi-stage build for minimal image size

# Stage 1: Build stage
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY amd_track1/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Runtime stage
FROM python:3.11-slim

WORKDIR /app

# Create non-root user for security
RUN useradd -m -u 1000 agent && \
    mkdir -p /input /output && \
    chown agent:agent /input /output

# Copy Python packages from builder
COPY --from=builder /root/.local /home/agent/.local

# Make sure scripts in .local are usable
ENV PATH=/home/agent/.local/bin:$PATH

# Copy application code
COPY amd_track1 /app/amd_track1

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# Switch to non-root user
USER agent

# Run the package from its parent so relative imports resolve correctly.
WORKDIR /app

# Entry point
ENTRYPOINT ["python", "-m", "amd_track1.entrypoint"]

# Expose port (if needed for debugging)
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s \
    CMD python -c "import sys; sys.exit(0)" || exit 1

# Scope 3 Estimator - Dockerfile
# Multi-stage build for optimized image size

# ============================================================================
# Stage 1: Builder
# ============================================================================
FROM python:3.10-slim as builder

LABEL maintainer="Scope 3 Estimator Team"
LABEL description="Scope 3 Emission Factor Retrieval System"

# Set working directory
WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies in a virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Upgrade pip and install dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ============================================================================
# Stage 2: Runtime
# ============================================================================
FROM python:3.10-slim

LABEL version="0.2.0"
LABEL description="Scope 3 Emission Factor Retrieval System"

# Set working directory
WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Set environment variables
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p cache logs

# Copy data files (embeddings and metadata)
# These should be pre-generated before building the image
RUN if [ ! -f "data/emission_factors/tier1_local/tier1_embeddings.npy" ]; then \
        echo "WARNING: Tier 1 embeddings not found. Please build embeddings before deployment."; \
    fi && \
    if [ ! -f "data/emission_factors/tier2_international/tier2_embeddings.npy" ]; then \
        echo "WARNING: Tier 2 embeddings not found. Please build embeddings before deployment."; \
    fi && \
    if [ ! -f "data/emission_factors/tier3_eeio/tier3_eeio_embeddings.npy" ]; then \
        echo "WARNING: Tier 3 embeddings not found. Please build embeddings before deployment."; \
    fi

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# Expose Streamlit port
EXPOSE 8501

# Run the application
CMD ["streamlit", "run", "app.py", \
     "--server.port=8501", \
     "--server.address=0.0.0.0", \
     "--server.headless=true", \
     "--browser.gatherUsageStats=false"]

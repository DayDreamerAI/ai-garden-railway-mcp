# Daydreamer MCP Connector - Cloud Run Deployment
# Python 3.11 (ML library compatibility - sentencepiece requires <3.13)
# Created: October 25, 2025
# Purpose: Railway → Cloud Run migration (lift-and-shift)

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies for Neo4j driver and ML libraries
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (Docker layer caching)
COPY requirements.txt .

# Install Python dependencies with optimizations for Cloud Run build speed
# Install core deps first (fast), then ML deps (slow but cached)
RUN pip install --no-cache-dir \
    neo4j==5.26.0 \
    aiohttp==3.10.11 \
    python-dotenv==1.0.1 \
    PyJWT==2.9.0 \
    cryptography==43.0.3 \
    && pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu \
    torch==2.5.1 \
    && pip install --no-cache-dir \
    transformers==4.45.0 \
    sentence-transformers==3.2.1 \
    protobuf==5.28.3 \
    sentencepiece==0.2.0 \
    safetensors==0.4.5 \
    tokenizers==0.20.3 \
    numpy==1.26.4 \
    psutil==6.1.0 \
    einops==0.8.0

# Copy application code
COPY mcp-claude-connector-memory-server.py .
COPY property_names.py .
COPY v6_mcp_bridge.py .
COPY jina_v3_optimized_embedder.py .
COPY semantic_classifier.py .
COPY schema_enforcement.py .
COPY global_search.py .
COPY local_search.py .
COPY mcp_integration.py .
COPY oauth/ ./oauth/
COPY tools/ ./tools/

# Cloud Run sets PORT environment variable
# Server will auto-detect Linux platform and use CPU (no MPS)
ENV PYTHONUNBUFFERED=1

# HuggingFace cache configuration for Cloud Run's read-only filesystem
# Cloud Run only allows writes to /tmp
ENV HF_HOME=/tmp/huggingface
ENV TRANSFORMERS_CACHE=/tmp/huggingface/transformers
ENV HF_DATASETS_CACHE=/tmp/huggingface/datasets

# Health check (Cloud Run will use /health endpoint)
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:${PORT:-8080}/health')"

# Start server
# Cloud Run will set PORT automatically
CMD python -u mcp-claude-connector-memory-server.py

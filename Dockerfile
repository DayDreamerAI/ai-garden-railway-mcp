# Daydreamer MCP Connector - Cloud Run Deployment
# Python 3.13.5 (matching Railway environment)
# Created: October 25, 2025
# Purpose: Railway → Cloud Run migration (lift-and-shift)

FROM python:3.13.5-slim

# Set working directory
WORKDIR /app

# Install system dependencies for Neo4j driver and ML libraries
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (Docker layer caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

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
COPY tools/ ./tools/

# Cloud Run sets PORT environment variable
# Server will auto-detect Linux platform and use CPU (no MPS)
ENV PYTHONUNBUFFERED=1

# Health check (Cloud Run will use /health endpoint)
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:${PORT:-8080}/health')"

# Start server
# Cloud Run will set PORT automatically
CMD python -u mcp-claude-connector-memory-server.py

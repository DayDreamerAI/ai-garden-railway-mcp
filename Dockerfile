# AI Garden Enhanced Railway Dockerfile
# Phase 2.3 - Docker Optimization with Build Auditing
# Created: 2025-09-12T23:29:00Z

FROM python:3.11-slim

# Build-time auditing labels
LABEL ai.garden.version="2.3.0" \
      ai.garden.component="railway-mcp-server" \
      ai.garden.phase="2.3" \
      ai.garden.security="enhanced" \
      ai.garden.audit="enabled" \
      ai.garden.build-date="2025-09-12T23:29:00Z" \
      maintainer="julian.crespi@ai-garden.dev"

# Security-hardened environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive

# Create audit directory early
RUN mkdir -p /app/audit /tmp/ai-garden-logs && \
    echo "$(date -u +"%Y-%m-%dT%H:%M:%SZ") - Docker build started" > /app/audit/build.log

# System hardening and security updates
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        dumb-init \
        && \
    echo "$(date -u +"%Y-%m-%dT%H:%M:%SZ") - System packages installed" >> /app/audit/build.log && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Create non-root user for security
RUN groupadd -r aigardenuser && \
    useradd -r -g aigardenuser -d /app -s /sbin/nologin -c "AI Garden User" aigardenuser && \
    echo "$(date -u +"%Y-%m-%dT%H:%M:%SZ") - Non-root user created" >> /app/audit/build.log

WORKDIR /app

# Copy and audit requirements
COPY requirements.txt .
RUN echo "$(date -u +"%Y-%m-%dT%H:%M:%SZ") - Requirements copied" >> /app/audit/build.log && \
    pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip list --format=json > /app/audit/installed-packages.json && \
    echo "$(date -u +"%Y-%m-%dT%H:%M:%SZ") - Python packages installed" >> /app/audit/build.log

# Copy application files with audit trail
COPY mcp_neo4j_semantic_server_with_consolidation.py ./server_original.py
COPY --from=build-context infrastructure/enhanced_railway_server.py ./server_enhanced.py
COPY --from=build-context infrastructure/railway_security_audited.py ./security_middleware.py
COPY --from=build-context infrastructure/logging_config.py ./logging_config.py

# Create startup script with enhanced security
RUN cat > /app/entrypoint.sh << 'EOF' && \
echo '#!/bin/bash' > /app/entrypoint.sh && \
echo 'set -euo pipefail' >> /app/entrypoint.sh && \
echo '' >> /app/entrypoint.sh && \
echo '# AI Garden Enhanced Railway MCP Server Entrypoint' >> /app/entrypoint.sh && \
echo '# Phase 2.3 - Docker Security & Auditing' >> /app/entrypoint.sh && \
echo '' >> /app/entrypoint.sh && \
echo 'TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")' >> /app/entrypoint.sh && \
echo 'echo "$TIMESTAMP - Container starting" >> /app/audit/runtime.log' >> /app/entrypoint.sh && \
echo '' >> /app/entrypoint.sh && \
echo '# Environment validation' >> /app/entrypoint.sh && \
echo 'if [[ -z "${NEO4J_URI:-}" ]]; then' >> /app/entrypoint.sh && \
echo '  echo "$TIMESTAMP - ERROR: NEO4J_URI not set" >> /app/audit/runtime.log' >> /app/entrypoint.sh && \
echo '  exit 1' >> /app/entrypoint.sh && \
echo 'fi' >> /app/entrypoint.sh && \
echo '' >> /app/entrypoint.sh && \
echo '# Security audit log' >> /app/entrypoint.sh && \
echo 'echo "$TIMESTAMP - Security check: Auth required=${REQUIRE_AUTHENTICATION:-true}" >> /app/audit/runtime.log' >> /app/entrypoint.sh && \
echo 'echo "$TIMESTAMP - Security check: Rate limit=${RATE_LIMIT_PER_MINUTE:-60}" >> /app/audit/runtime.log' >> /app/entrypoint.sh && \
echo 'echo "$TIMESTAMP - Security check: Bearer token configured=${RAILWAY_BEARER_TOKEN:+yes}" >> /app/audit/runtime.log' >> /app/entrypoint.sh && \
echo '' >> /app/entrypoint.sh && \
echo '# Health check before startup' >> /app/entrypoint.sh && \
echo 'python -c "import sys; print(f\"Python {sys.version}\")" >> /app/audit/runtime.log' >> /app/entrypoint.sh && \
echo 'python -c "import json; import pkg_resources; installed = [str(d).split() for d in pkg_resources.working_set]; print(json.dumps(installed, indent=2))" > /app/audit/runtime-packages.json' >> /app/entrypoint.sh && \
echo '' >> /app/entrypoint.sh && \
echo '# Set port from Railway environment' >> /app/entrypoint.sh && \
echo 'export MCP_PORT=${PORT:-8080}' >> /app/entrypoint.sh && \
echo 'echo "$TIMESTAMP - Starting server on port $MCP_PORT" >> /app/audit/runtime.log' >> /app/entrypoint.sh && \
echo '' >> /app/entrypoint.sh && \
echo '# Start the enhanced server with security' >> /app/entrypoint.sh && \
echo 'exec python server_enhanced.py 2>&1 | tee -a /app/audit/runtime.log' >> /app/entrypoint.sh && \
chmod +x /app/entrypoint.sh && \
echo "$(date -u +"%Y-%m-%dT%H:%M:%SZ") - Entrypoint script created" >> /app/audit/build.log

# Security: Set proper file permissions
RUN chown -R aigardenuser:aigardenuser /app && \
    chmod 755 /app && \
    chmod 644 /app/*.py && \
    chmod 755 /app/entrypoint.sh && \
    chmod -R 755 /app/audit && \
    echo "$(date -u +"%Y-%m-%dT%H:%M:%SZ") - File permissions set" >> /app/audit/build.log

# Set security context
USER aigardenuser

# Enhanced health check with security validation
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=5 \
  CMD curl -fsS http://127.0.0.1:${PORT:-8080}/health \
      -H "User-Agent: AI-Garden-HealthCheck/2.3.0" \
      ${RAILWAY_BEARER_TOKEN:+-H "Authorization: Bearer $RAILWAY_BEARER_TOKEN"} \
      || exit 1

# Expose port (Railway dynamically assigns)
EXPOSE 8080

# Use dumb-init for proper signal handling
ENTRYPOINT ["dumb-init", "--"]

# Start with enhanced entrypoint
CMD ["/app/entrypoint.sh"]

# Build completion audit
RUN echo "$(date -u +"%Y-%m-%dT%H:%M:%SZ") - Docker build completed successfully" >> /app/audit/build.log && \
    echo "AI Garden Enhanced Railway MCP Server v2.3.0 ready for deployment" >> /app/audit/build.log
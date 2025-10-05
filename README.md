# Daydreamer Railway MCP Server v3.0

✅ **Production-Validated Multi-Platform Memory Sovereignty**

Railway-hosted MCP server enabling Claude Desktop/Web/Mobile access to AuraDB-backed memory graph. Successfully migrated 27,487 entities (October 2025) with full Custom Connector integration.

**Production Status:**
- ✅ AuraDB Migration Complete (Oct 5, 2025)
- ✅ Claude Desktop Validated (27,487 entities accessible)
- ✅ Claude Mobile Validated (10 query patterns tested)
- ✅ SSE Transport Operational
- ✅ Multi-platform memory sovereignty achieved

## 🚀 Quick Deploy

### 1) Clone & Push to GitHub

```bash
git clone <this-repo>
cd neo4j-mcp-railway
git remote add origin https://github.com/<you>/neo4j-mcp-railway.git
git push -u origin main
```

### 2) Deploy on Railway with AuraDB

- Railway → **New Project** → **Deploy from GitHub** → select this repo
- In **Variables**, set:
  - `NEO4J_URI=neo4j+s://<your-db-id>.databases.neo4j.io` ⚠️ **No port number for AuraDB**
  - `NEO4J_USERNAME=neo4j`
  - `NEO4J_PASSWORD=<your-auradb-password>`
  - `RAILWAY_BEARER_TOKEN=<generate-secure-token>` (🔒 **Required for production**)
  - `REQUIRE_AUTHENTICATION=true` (optional, defaults to true)
  - `RATE_LIMIT_PER_MINUTE=60` (optional, defaults to 60)

**Production Configuration (Oct 2025):**
- Instance: `neo4j+s://8c3b5488.databases.neo4j.io` (InstanceDaydreamer_01)
- Database: 27,487 entities, 110,449 relationships
- Status: Operational and validated

### 3) Generate Secure Bearer Token

```bash
# Generate a secure token for production
openssl rand -hex 32
# Example: a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef123456
```

### 4) Validate Deployment

```bash
BASE=https://<service>.up.railway.app
TOKEN=<your-bearer-token>

# Health check (requires authentication)
curl -H "Authorization: Bearer $TOKEN" "$BASE/health"

# Test SSE endpoint
curl -H "Authorization: Bearer $TOKEN" -N "$BASE/sse" | head -20
```

## 🛡️ Security Features

### Authentication & Authorization
- **Bearer Token Auth**: Required for all endpoints in production
- **Rate Limiting**: 60 requests per minute per IP (configurable)
- **Request Auditing**: Every request/response logged with unique tracking ID

### Security Headers
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY` 
- `Strict-Transport-Security: max-age=31536000`
- `Content-Security-Policy: default-src 'self'`

### Container Security
- **Non-root user**: Container runs as `aigardenuser`
- **Minimal attack surface**: Only essential packages installed
- **Build auditing**: Complete audit trail of build process

## 🏥 Health Monitoring

### Comprehensive Health Checks
- **Memory usage**: Warns at >85% usage
- **Disk space**: Monitors available storage  
- **Neo4j connectivity**: Validates database connection
- **Security metrics**: Tracks authentication failures, rate limits

### Health Endpoint Response
```json
{
  "status": "healthy",
  "checks": {
    "memory": {"status": "healthy", "usage_percent": 45.2},
    "disk": {"status": "healthy", "free_gb": 12.3},
    "neo4j": {"status": "healthy", "responsive": true},
    "security": {"total_requests": 1247, "failed_auth_attempts": 3}
  },
  "server": {
    "version": "2.3.0",
    "uptime_seconds": 3600
  }
}
```

## 📊 Audit Logging

All requests include audit trail:
- **Request ID**: Unique tracking identifier
- **Client IP**: Source IP address
- **Authentication**: Success/failure status
- **Rate Limiting**: Request count and limits
- **Response Time**: Processing duration in milliseconds

## 🔧 Local Development

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Set environment variables
export NEO4J_URI=neo4j+s://<your-db>.databases.neo4j.io:7687
export NEO4J_USERNAME=neo4j
export NEO4J_PASSWORD=<password>
export RAILWAY_BEARER_TOKEN=<secure-token>
export MCP_PORT=8080

# Run enhanced server
python server_enhanced.py
```

## 🔗 Custom Connector Integration

### Setup Guide

**Complete documentation:** [CUSTOM_CONNECTOR_SETUP.md](./CUSTOM_CONNECTOR_SETUP.md)

**Quick Setup (Claude Desktop):**
1. Edit `~/Library/Application Support/Claude/claude_desktop_config.json`
2. Add connector:
```json
{
  "mcpServers": {
    "daydreamer-memory": {
      "url": "https://ai-garden-railway-mcp-production.up.railway.app/mcp",
      "transport": "sse",
      "headers": {
        "Authorization": "Bearer <your-token>"
      }
    }
  }
}
```
3. Restart Claude Desktop
4. Test: "Search for Julian Crespi in memory"

**Supported Platforms:**
- ✅ Claude Desktop (validated Oct 5, 2025)
- ✅ Claude Web (Custom Connector support)
- ✅ Claude Mobile (validated Oct 5, 2025)
- ✅ ChatGPT (Custom Connector support)

## 📊 AuraDB Migration (October 2025)

**Migration Report:** [Migration Success Documentation](../../../../../docs/migrations/neo4j-auradb-migration-success.md)

**What Was Migrated:**
- 27,487 entities (100% validation match)
- 110,449 relationships (zero data loss)
- 14,414 V6 Observation nodes (Perennial architecture)
- 537 Conversation Sessions
- Complete temporal binding and relationship graph

**Migration Method:**
```bash
# Official Neo4j tooling
neo4j-admin database dump neo4j --to-path=/backups/neo4j
neo4j-admin database upload neo4j \
  --from-path=/backups/neo4j \
  --to-uri=neo4j+s://8c3b5488.databases.neo4j.io \
  --overwrite-destination=true
```

**Duration:** 23 minutes (dump + upload + validation)

**Validation:**
- ✅ Count comparison (Python script)
- ✅ Claude Desktop production test
- ✅ Claude Mobile 10-pattern query test
- ✅ Custom Connector SSE transport
- ✅ Multi-platform access operational

**Key Learnings:**
1. AuraDB URIs should NOT include `:7687` port
2. Always source `.env` for credentials
3. Validate with count comparison before declaring success

## 📚 Complete Documentation

### 🚀 Quick Start Guides
- **AI_GARDEN_DEPLOYMENT_GUIDE.md**: Complete deployment guide with architecture overview
- **DEPLOYMENT_INSTRUCTIONS.md**: Step-by-step Railway deployment instructions  
- **ENVIRONMENT_GUIDE.md**: Environment configuration with templates and validation

### 🏗️ Technical Documentation
- **ARCHITECTURE.md**: Comprehensive system architecture and technical design
- **README.md**: This file - project overview and quick reference

### 🔧 Configuration Templates
- **`.env.production`**: Production environment with maximum security
- **`.env.staging`**: Pre-production testing with validation features
- **`.env.development`**: Local development with debugging enabled
- **`.env.example`**: Basic configuration template

### 🛠️ Automation Scripts
- **`deploy.sh`**: Pre-deployment validation and setup automation
- **`validate_deployment.sh`**: Post-deployment testing and validation
- **`validate_env.sh`**: Environment configuration validation
- **`setup_github.sh`**: Automated GitHub repository creation
- **`smoke.sh`**: Basic service health check

### 📊 Deployment Assets
- **`Dockerfile`**: Security-hardened container with audit trails
- **`railway.toml`**: Railway platform configuration
- **`requirements.txt`**: Python dependencies
- **`ai-garden-deployment-manifest.json`**: Deployment metadata

### 🤖 Core Application
- **`server_enhanced.py`**: Enhanced MCP server v2.2.0 with security integration
- **`security_middleware.py`**: Authentication, rate limiting, and audit logging
- **`logging_config.py`**: Structured JSON logging with performance metrics
- **`mcp_neo4j_semantic_server_with_consolidation.py`**: Original MCP server implementation
- **`health_check.py`**: Service health monitoring

## ⚡ Quick Commands

```bash
# Environment setup and validation
./validate_env.sh                    # Validate current configuration
cp .env.production .env              # Use production template
cp .env.development .env             # Use development template

# Deployment automation
./deploy.sh                          # Complete deployment preparation
./setup_github.sh [repo-name]       # Create GitHub repository
git push origin main                 # Deploy to Railway (after setup)

# Post-deployment validation
./validate_deployment.sh https://your-service.up.railway.app your-token
./smoke.sh https://your-service.up.railway.app  # Basic health check
```

## 🔍 Troubleshooting

**For detailed troubleshooting, see [AI_GARDEN_DEPLOYMENT_GUIDE.md](./AI_GARDEN_DEPLOYMENT_GUIDE.md#-troubleshooting)**

### Quick Diagnostic Commands
```bash
# Environment validation
./validate_env.sh

# Service health check  
curl -H "Authorization: Bearer $RAILWAY_BEARER_TOKEN" https://your-service.up.railway.app/health

# View Railway logs
railway logs

# Test database connection
python3 -c "from neo4j import GraphDatabase; print('✅ Neo4j available')"
```

---

**Daydreamer Railway MCP Server v3.0**
✅ Multi-platform memory sovereignty • 🔗 Custom Connector integration • ☁️ AuraDB cloud-hosted

**Last Updated:** October 5, 2025
**Production Status:** Operational and validated across Claude Desktop/Web/Mobile platforms
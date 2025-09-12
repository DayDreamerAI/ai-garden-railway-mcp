# AI Garden Enhanced Railway MCP Server v2.3.0

🛡️ **Security-Enhanced MCP Server with Comprehensive Auditing**

This repository deploys your Neo4j-backed MCP server on Railway with integrated security middleware, request auditing, and comprehensive health monitoring.

## 🚀 Quick Deploy

### 1) Clone & Push to GitHub

```bash
git clone <this-repo>
cd neo4j-mcp-railway
git remote add origin https://github.com/<you>/neo4j-mcp-railway.git
git push -u origin main
```

### 2) Deploy on Railway with Security

- Railway → **New Project** → **Deploy from GitHub** → select this repo
- In **Variables**, set:
  - `NEO4J_URI=neo4j+s://<your-db-id>.databases.neo4j.io:7687`
  - `NEO4J_USERNAME=neo4j`
  - `NEO4J_PASSWORD=<your-password>`
  - `RAILWAY_BEARER_TOKEN=<generate-secure-token>` (🔒 **Required for production**)
  - `REQUIRE_AUTHENTICATION=true` (optional, defaults to true)
  - `RATE_LIMIT_PER_MINUTE=60` (optional, defaults to 60)

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

## 🚀 ChatGPT Integration

### Custom Connector Setup
1. Open ChatGPT → Settings → Beta Features
2. Enable "Custom Connectors" 
3. Add new connector:
   - **Name**: Daydreamer Memory
   - **Base URL**: `https://<your-service>.up.railway.app`
   - **Authentication**: Bearer Token
   - **Token**: Your `RAILWAY_BEARER_TOKEN`

### Test Connection
In ChatGPT: "Search my memory for information about AI Garden"

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

**AI Garden Enhanced Railway MCP Server v2.3.0**  
🛡️ Security-first design • 📊 Comprehensive auditing • 🏥 Advanced monitoring

Generated: 2025-09-12 23:30:04 UTC
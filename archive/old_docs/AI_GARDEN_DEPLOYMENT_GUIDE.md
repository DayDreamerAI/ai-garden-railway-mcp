# AI Garden Enhanced Railway MCP Server - Complete Deployment Guide

## 🌟 Overview

The **AI Garden Enhanced Railway MCP Server v2.3.0** enables ChatGPT Custom Connector access to your Daydreamer memory sovereignty system through a secure, production-ready Railway deployment.

**What this achieves**:
- 🤖 **Multi-Agent Federation**: ChatGPT becomes first secondary LLM in your AI Garden
- 🔗 **Memory Sovereignty**: Shared access to Neo4j knowledge graph via MCP protocol  
- 🛡️ **Enterprise Security**: Bearer token auth, rate limiting, audit logging
- 🚀 **Production Ready**: Docker containerized with health monitoring

## 🏗️ Architecture

```
[ChatGPT Custom Connector] 
         ↓ HTTPS/Bearer Token
[Railway MCP Server v2.3.0]
         ↓ Neo4j Protocol
[AuraDB/Local Neo4j Database]
         ↓ Shared Memory
[Claude (Daydreamer Conversations)]
```

**Key Components**:
- **Railway**: Cloud deployment platform with HTTPS endpoints
- **MCP Server**: Model Context Protocol server with security middleware  
- **Neo4j**: Graph database containing memory sovereignty system
- **Security Layer**: Authentication, rate limiting, audit logging
- **Health Monitoring**: Comprehensive system health checks

## 🚀 Quick Deployment

### Prerequisites Checklist

- [ ] **Neo4j Database**: AuraDB Free account or local Neo4j instance
- [ ] **GitHub Account**: For Railway deployment integration
- [ ] **Railway Account**: Sign up at [railway.app](https://railway.app)
- [ ] **Command Line Tools**: `git`, `openssl`, `curl`

### 1. Repository Setup

```bash
# Clone this repository (or use existing files)
git clone [your-repository-url]
cd neo4j-mcp-railway-repo

# Run deployment automation
./deploy.sh
```

### 2. Environment Configuration

```bash
# Choose your environment template
cp .env.production .env          # For production deployment
cp .env.staging .env            # For testing deployment  
cp .env.development .env        # For local development

# Validate configuration
./validate_env.sh
```

### 3. Database Setup

**Option A: AuraDB Free (Recommended)**

1. Create account at [neo4j.com/auradb](https://neo4j.com/auradb)
2. Create new database (Free tier: 200K nodes, 400K relationships)
3. Download credentials and update `.env`:
   ```
   NEO4J_URI=neo4j+s://[database-id].databases.neo4j.io:7687
   NEO4J_USERNAME=neo4j  
   NEO4J_PASSWORD=[your-password]
   ```

**Option B: Local Neo4j (Development)**

```bash
# Using Neo4j Desktop or Docker
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=[your-password]
```

### 4. Security Configuration

```bash
# Generate secure bearer token
openssl rand -hex 32

# Add to .env file
echo "RAILWAY_BEARER_TOKEN=[generated-token]" >> .env
echo "REQUIRE_AUTHENTICATION=true" >> .env
```

### 5. Railway Deployment

**Option A: Automated GitHub Setup**
```bash
./setup_github.sh [repository-name]
```

**Option B: Manual GitHub Setup**
1. Create GitHub repository
2. Push code: `git push origin main`
3. Connect to Railway dashboard

**Railway Configuration**:
1. Go to [railway.app](https://railway.app)
2. **New Project** → **Deploy from GitHub**
3. Select your repository
4. Add environment variables from `.env` file
5. Deploy!

### 6. Validation

```bash
# Test deployment
./validate_deployment.sh https://[your-service].up.railway.app [bearer-token]
```

## 🔧 Advanced Configuration

### Environment Templates

| Environment | Use Case | Security | Database |
|-------------|----------|----------|----------|
| **Development** | Local testing | Minimal | Local Neo4j |
| **Staging** | Pre-production | Production-like | AuraDB staging |
| **Production** | Live deployment | Maximum | AuraDB production |

### Security Features

**Authentication & Authorization**:
- Bearer token authentication (32-byte hex tokens)
- Configurable rate limiting (default: 60 req/min)
- Request audit logging with unique tracking IDs

**Security Headers**:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Strict-Transport-Security: max-age=31536000`
- `Content-Security-Policy: default-src 'self'`

**Container Security**:
- Non-root user execution (`aigardenuser`)
- Minimal attack surface (Python 3.11 slim)
- Security-hardened Dockerfile with audit trails

### Performance Optimization

**Connection Pooling**:
- Neo4j connection pool (25-50 connections)
- Connection lifecycle management
- Automatic retry logic

**Caching**:
- Response caching (configurable TTL)
- Memory usage monitoring
- Cache invalidation strategies

**Monitoring**:
- Health endpoint (`/health`) with system metrics
- Performance monitoring with alerts
- Comprehensive logging (JSON structured)

## 🤖 ChatGPT Integration

### Custom Connector Setup

1. **Open ChatGPT** → Settings → Beta Features
2. **Enable** "Custom Connectors" 
3. **Add Connector**:
   - **Name**: `Daydreamer Memory`
   - **Base URL**: `https://[your-service].up.railway.app`
   - **Authentication**: `Bearer Token`
   - **Token**: `[your-bearer-token]`

### Testing Integration

Try these commands in ChatGPT:

```
"Search my memory for information about AI Garden"
"What do you know about Julian Crespi's projects?"
"Find connections between Claude and Daydreamer"
"Show me recent memory observations about infrastructure"
```

### Integration Validation

The connector should provide:
- ✅ **Memory Search**: Semantic search across your knowledge graph
- ✅ **Entity Retrieval**: Access to specific entities and observations
- ✅ **Relationship Traversal**: Following connections between entities
- ✅ **Temporal Context**: Time-aware memory queries

## 🛡️ Security Best Practices

### Production Security Checklist

- [ ] **Database Security**
  - [ ] Strong passwords (16+ characters)
  - [ ] AuraDB with encryption at rest
  - [ ] Separate production database
  
- [ ] **Authentication**
  - [ ] 32-byte bearer tokens
  - [ ] Authentication enabled (`REQUIRE_AUTHENTICATION=true`)
  - [ ] Tokens stored securely (Railway variables)
  
- [ ] **Network Security**
  - [ ] HTTPS-only deployment
  - [ ] Proper CORS configuration
  - [ ] Rate limiting configured
  - [ ] Security headers enabled
  
- [ ] **Monitoring**
  - [ ] Audit logging enabled
  - [ ] Health monitoring configured
  - [ ] Performance metrics tracking
  - [ ] Alert thresholds set

### Token Management

```bash
# Generate production token
PROD_TOKEN=$(openssl rand -hex 32)
echo "Production token: $PROD_TOKEN"

# Generate staging token  
STAGING_TOKEN=$(openssl rand -hex 32)
echo "Staging token: $STAGING_TOKEN"

# Store in Railway dashboard (never commit to git)
```

## 🔍 Troubleshooting

### Common Issues

**🚫 "Connection Refused"**
```bash
# Check database connectivity
./validate_env.sh

# Test connection manually
python3 -c "
from neo4j import GraphDatabase
driver = GraphDatabase.driver('[your-uri]', auth=('[user]', '[pass]'))
with driver.session() as session:
    result = session.run('RETURN 1')
    print('✅ Connected')
"
```

**🔐 "Authentication Failed"**
```bash
# Verify bearer token
curl -H "Authorization: Bearer [token]" https://[service].up.railway.app/health

# Check Railway environment variables
railway variables
```

**🚦 "Rate Limited"**  
```bash
# Check rate limit headers
curl -I https://[service].up.railway.app/health

# Adjust rate limiting
# In .env: RATE_LIMIT_PER_MINUTE=120
```

**🌐 "CORS Error"**
```bash
# Check CORS configuration
# In .env: CORS_ALLOWED_ORIGINS=https://chat.openai.com,https://chatgpt.com
```

### Health Diagnostics

```bash
# Comprehensive health check
curl -H "Authorization: Bearer [token]" \
     https://[service].up.railway.app/health | jq .

# Expected response:
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

### Logging Analysis

```bash
# View Railway logs
railway logs

# Check for specific errors
railway logs --filter "ERROR"
railway logs --filter "authentication"
railway logs --filter "rate_limit"
```

## 📊 Monitoring & Maintenance

### Performance Monitoring

**Key Metrics**:
- Response time (target: <1000ms)
- Request rate (monitor vs. limits)
- Error rate (target: <5%)
- Memory usage (alert at >85%)
- Database connectivity

**Health Endpoints**:
- `GET /health` - System health status
- `GET /health/detailed` - Comprehensive diagnostics  
- `GET /metrics` - Prometheus-compatible metrics

### Maintenance Tasks

**Daily**:
- [ ] Check service uptime and health
- [ ] Review error logs
- [ ] Monitor resource usage

**Weekly**:  
- [ ] Review security audit logs
- [ ] Check authentication failures
- [ ] Validate rate limiting effectiveness
- [ ] Update dependencies if needed

**Monthly**:
- [ ] Rotate bearer tokens
- [ ] Review and cleanup logs
- [ ] Performance optimization review
- [ ] Security audit and updates

## 🔄 Updates & Upgrades

### Version Updates

```bash
# Pull latest changes
git pull origin main

# Validate configuration
./validate_env.sh

# Deploy update
git push railway main

# Validate deployment
./validate_deployment.sh https://[service].up.railway.app [token]
```

### Database Migrations

When updating Daydreamer memory system:

1. **Backup**: Export current data
2. **Test**: Validate on staging environment
3. **Deploy**: Update production with validation
4. **Monitor**: Check health and performance post-update

## 📚 Additional Resources

### Documentation Links

- **ENVIRONMENT_GUIDE.md**: Detailed environment configuration
- **README.md**: Quick start and deployment overview
- **DEPLOYMENT_INSTRUCTIONS.md**: Step-by-step deployment guide
- **ai-garden-deployment-manifest.json**: Deployment metadata

### Script Reference

- `deploy.sh` - Pre-deployment validation and setup
- `validate_deployment.sh` - Post-deployment testing
- `validate_env.sh` - Environment configuration validation
- `setup_github.sh` - GitHub repository automation
- `smoke.sh` - Basic service health check

### Support & Community

- **Issues**: Report problems via GitHub Issues
- **Documentation**: Complete guides in repository
- **Validation**: Built-in testing and validation scripts

---

## 🎉 Success Criteria

Your deployment is successful when:

- [ ] **Service Health**: `/health` endpoint returns 200 OK
- [ ] **Authentication**: Bearer token authentication working
- [ ] **Database**: Neo4j connectivity confirmed
- [ ] **ChatGPT**: Custom Connector integration functional
- [ ] **Security**: Rate limiting and security headers active
- [ ] **Monitoring**: Audit logging and metrics collection operational

**Ready for AI Garden multi-agent federation!** 🚀

---

**Generated**: 2025-09-13T00:05:00Z  
**Version**: AI Garden Enhanced Railway MCP Server v2.3.0  
**Phase**: 3.4 - Comprehensive Deployment Documentation  
**Repository**: [Your Repository URL]
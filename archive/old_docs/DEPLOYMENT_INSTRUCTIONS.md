# AI Garden Railway Deployment Instructions

## Quick Deploy to Railway

### 1. Prerequisites
- ✅ GitHub repository: https://github.com/JulianCrespi/ai-garden-railway-mcp
- ✅ Railway account: [railway.app](https://railway.app)
- ✅ AuraDB Neo4j database (or local Neo4j)

### 2. Deploy on Railway

1. **Connect Repository**
   - Go to [railway.app](https://railway.app)
   - Click "Deploy from GitHub"
   - Select: `ai-garden-railway-mcp`
   - Railway will auto-detect Python project

2. **Environment Variables**
   Add these in Railway dashboard → Variables:
   ```
   NEO4J_URI=neo4j+s://your-db-id.databases.neo4j.io:7687
   NEO4J_USERNAME=neo4j
   NEO4J_PASSWORD=your-password
   RAILWAY_BEARER_TOKEN=your-generated-token
   REQUIRE_AUTHENTICATION=true
   RATE_LIMIT_PER_MINUTE=60
   ```

3. **Generate Secure Token**
   ```bash
   openssl rand -hex 32
   ```

### 3. Validate Deployment

After Railway deploys your service:

```bash
# Test your deployment
./validate_deployment.sh https://your-service.up.railway.app your-bearer-token
```

### 4. ChatGPT Integration

1. Open ChatGPT → Settings → Beta Features
2. Enable "Custom Connectors"
3. Add connector:
   - **Name**: Daydreamer Memory
   - **Base URL**: `https://your-service.up.railway.app`
   - **Auth**: Bearer Token
   - **Token**: Your `RAILWAY_BEARER_TOKEN`

### 5. Test Integration

In ChatGPT: *"Search my memory for information about AI Garden"*

---

**Generated**: 2025-09-12T23:51:26Z  
**Repository**: https://github.com/JulianCrespi/ai-garden-railway-mcp  
**Version**: AI Garden Enhanced Railway MCP Server v2.3.0

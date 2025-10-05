# Railway Deployment Guide

**Complete guide for deploying Daydreamer MCP servers to Railway**

---

## Quick Start

### Prerequisites
- Railway account: https://railway.app
- GitHub account
- Daydreamer MCP server development environment

### One-Command Deployment

```bash
cd /llm/mcp/connectors/mcp-claude-connector/neo4j-mcp-railway-repo/
./deploy_to_railway.sh
```

That's it! Railway will auto-deploy within 2 minutes.

---

## Architecture Overview

### Three-Layer System

```
PRIVATE REPOSITORY (daydreamer-mcp)
├── /llm/mcp/servers/
│   └── daydreamer-memory-mcp/ (stdio, 22 tools)
│
├── /llm/mcp/connectors/
│   └── mcp-claude-connector/
│       └── neo4j-mcp-railway-repo/
│           ├── mcp-claude-connector-memory-server.py (SSE, Tier 1: 5 tools)
│           ├── deploy_to_railway.sh (automated sync)
│           └── test_railway_memory_server.py (7 tests)
│
                    ↓ Automated Sync

PUBLIC REPOSITORY (ai-garden-railway-mcp)
├── mcp-claude-connector-memory-server.py
├── railway.toml
├── requirements.txt
└── README.md

                    ↓ Auto-Deploy (2 min)

RAILWAY PRODUCTION
└── https://ai-garden-railway-mcp-production.up.railway.app
```

### Deployment Flow

1. **Develop** in private repo (mcp-claude-connector-memory-server.py)
2. **Test** locally with test suite
3. **Deploy** via `./deploy_to_railway.sh`
4. **Sync** to public repo (security validated)
5. **Auto-deploy** Railway watches public repo
6. **Validate** test suite against production URL

---

## Tier-Based Deployment Strategy

### Tier 1: Core Operations (5 tools) ✅ DEPLOYED

**Status:** Production (Oct 5, 2025)
**Tools:**
1. search_nodes - Semantic search via JinaV3 or exact lookup
2. memory_stats - Graph statistics with V6 status
3. create_entities - Entity creation with embeddings
4. add_observations - Observation management
5. raw_cypher_query - Direct Cypher access

**Validation:** 7/7 tests passing (100%)

### Tier 2: Conversation Tools (4 tools) - READY

**Status:** Implemented, awaiting deployment
**Tools:**
1. search_conversations - Find sessions by content, time, activity
2. trace_entity_origin - Discover conversation origins
3. get_temporal_context - Retrieve conversations around dates
4. get_breakthrough_sessions - Load high-impact sessions

**Next:** Update server.py, run deploy script

### Tier 3: Advanced Search (3 tools) - READY

**Status:** Implemented, awaiting deployment
**Tools:**
1. virtual_context_search - 70% token reduction
2. conversational_memory_search - Natural language memory
3. search_observations - Multi-dimensional filtering

**Total Tools:** 12 (Tier 1: 5 deployed, Tier 2+3: 7 ready)

---

## Deployment Script Details

### deploy_to_railway.sh Workflow

**Step 1: Security Validation**
```bash
# Prevents hardcoded secrets in deployment
- Scans for password/key/token patterns
- Allows env var assignments (os.environ, getenv)
- Fails if hardcoded secrets detected
```

**Step 2: Repository Sync**
```bash
# Clone/update public deployment repo
- Git clone ai-garden-railway-mcp (if needed)
- Git pull latest (if exists)
- Clean deployment directory
```

**Step 3: File Selection**
```bash
# Copy deployment files only (4 files)
- mcp-claude-connector-memory-server.py
- railway.toml
- requirements.txt
- .env.template
```

**Step 4: Documentation Update**
```bash
# Generate deployment README
- Tier information
- Tool descriptions
- Environment variables
- Setup instructions
```

**Step 5: Git Operations**
```bash
# Commit and push with version tag
git add -A
git commit -m "deploy: Tier X memory server vYYYY.MM.DD-HHMM"
git push origin main
```

**Step 6: Health Check**
```bash
# Validate deployment (after 15s)
curl https://ai-garden-railway-mcp-production.up.railway.app/health
```

---

## Configuration Files

### railway.toml

```toml
[build]
buildCommand = "pip install -r requirements.txt"

[deploy]
startCommand = "python -u mcp-claude-connector-memory-server.py"
healthcheckPath = "/health"
healthcheckTimeout = 300
restartPolicyType = "never"

[environments.production]
MCP_TRANSPORT = "sse"
REQUIRE_AUTHENTICATION = "true"
RATE_LIMIT_PER_MINUTE = "60"
```

**Key Settings:**
- `startCommand`: Entry point for SSE server
- `healthcheckPath`: Railway monitors this endpoint
- `healthcheckTimeout`: 5 minutes for startup
- `restartPolicyType`: Never restart (manual control)

### Environment Variables (Railway Dashboard)

**Required:**
```env
NEO4J_URI=neo4j+s://8c3b5488.databases.neo4j.io
NEO4J_PASSWORD=<your-auradb-password>
JINA_API_KEY=<your-jina-api-key>
```

**Optional:**
```env
MCP_TRANSPORT=sse
REQUIRE_AUTHENTICATION=true
RATE_LIMIT_PER_MINUTE=60
```

---

## Testing

### Local Testing

```bash
cd neo4j-mcp-railway-repo/

# Run test suite locally
python3 test_railway_memory_server.py
```

**Expected:** 7/7 tests passing for Tier 1

### Production Testing

```bash
# Set Railway server URL
export RAILWAY_SERVER_URL="https://ai-garden-railway-mcp-production.up.railway.app"
export TEST_MODE="railway"

# Run test suite
python3 test_railway_memory_server.py
```

**Expected Output:**
```
✅ Test 1: Initialize MCP Connection
✅ Test 2: List Available Tools (5 tools)
✅ Test 3: Search Nodes
✅ Test 4: Memory Statistics
✅ Test 5: Create Test Entity
✅ Test 6: Add Observations
✅ Test 7: Raw Cypher Query

Total: 7/7 PASSED (100%)
```

---

## Troubleshooting

### Deployment Not Triggering

**Problem:** Railway doesn't auto-deploy after push

**Solution:**
1. Check Railway dashboard: https://railway.app
2. Navigate to project: ai-garden-railway-mcp-production
3. Click "Deploy" → "Redeploy Latest"
4. Wait ~2 minutes for build

### Test Suite Failures

**Problem:** Tests failing against production URL

**Solution:**
1. Check health endpoint: `curl https://ai-garden-railway-mcp-production.up.railway.app/health`
2. Verify tools available: Check `/sse` endpoint establishes connection
3. Confirm environment variables set in Railway dashboard
4. Check Railway logs for server errors

### SSE Connection Issues

**Problem:** SSE endpoint not responding

**Solution:**
1. Verify `startCommand` in railway.toml points to correct file
2. Check Python dependencies installed (requirements.txt)
3. Confirm Neo4j connection (NEO4J_URI, NEO4J_PASSWORD)
4. Review Railway deployment logs

---

## Best Practices

### Security

- ✅ Never commit secrets to public repo
- ✅ Use Railway environment variables for credentials
- ✅ Security scan runs automatically via deploy script
- ✅ .env files excluded from deployment

### Version Control

- ✅ Commit messages include version tags
- ✅ Each deployment tagged with timestamp
- ✅ Git history maintained in both repos

### Testing

- ✅ Test locally before deploying
- ✅ Validate production after deployment
- ✅ Monitor health endpoint regularly

### Rollback

```bash
# If deployment fails, rollback in Railway dashboard
1. Go to Deployments tab
2. Find previous working deployment
3. Click "Redeploy" on that version
```

---

## Multi-Platform Access

### Custom Connector Configuration

**Claude Desktop/Mobile/Web:**

1. Go to Settings → Developer → Custom Connectors
2. Add new connector:
   - Name: "Daydreamer Memory"
   - URL: https://ai-garden-railway-mcp-production.up.railway.app/mcp
   - Transport: SSE
   - Auth: None (public endpoint)

3. Enable connector
4. Tools appear in Claude interface

**Validation:**
- Desktop: ✅ All 5 tools available
- Mobile: ✅ All 5 tools available
- Web: ✅ All 5 tools available (same connector)

---

## Performance Metrics

### Production Stats (Oct 5, 2025)

**Data Scale:**
- Entities: 21,651
- Relationships: 27,487
- V6 Observation Nodes: 14,488
- Conversation Sessions: 537
- Chunks: 4,765

**Response Times:**
- SSE connection: Instant
- Tool queries: Sub-second (<1s)
- Health check: ~50ms
- Search operations: <500ms

**Reliability:**
- Uptime: 99.9% (Railway SLA)
- Auto-scaling: Enabled
- Health monitoring: Active

---

## Adding New Tools

### Step 1: Update Server

```python
# In mcp-claude-connector-memory-server.py

# Register new tool
register_tool({
    "name": "new_tool_name",
    "description": "Tool description",
    "inputSchema": {
        "type": "object",
        "properties": {
            "param1": {"type": "string"}
        },
        "required": ["param1"]
    }
})

# Add handler
async def handle_new_tool(params):
    # Implementation
    pass

# Register in handler map
TOOL_HANDLERS["new_tool_name"] = handle_new_tool
```

### Step 2: Update Tests

```python
# In test_railway_memory_server.py

async def test_new_tool(self):
    result = await self.send_mcp_request(
        method="tools/call",
        params={
            "name": "new_tool_name",
            "arguments": {"param1": "value"}
        }
    )
    assert result["success"] == True
```

### Step 3: Deploy

```bash
./deploy_to_railway.sh
```

### Step 4: Validate

```bash
RAILWAY_SERVER_URL="..." python3 test_railway_memory_server.py
```

---

## Documentation References

### Internal Docs
- **CONNECTOR_DEVELOPMENT_GUIDE.md** - Multi-connector best practices
- **DEPLOYMENT_COMPLETE.md** - Tier 1 deployment summary
- **DEPLOYMENT_VALIDATED.md** - Production validation (7/7 tests)
- **CLEANUP_PLAN.md** - Repository organization

### External Resources
- Railway Docs: https://docs.railway.app
- MCP Specification: https://modelcontextprotocol.io
- SSE Transport: https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events

---

## Tier Deployment Checklist

### Deploying New Tier

- [ ] Update mcp-claude-connector-memory-server.py (add tools)
- [ ] Update TOOL_REGISTRY (register tools)
- [ ] Add tool handlers (implement functions)
- [ ] Update test suite (add new tests)
- [ ] Test locally (all tests passing)
- [ ] Run `./deploy_to_railway.sh`
- [ ] Wait for Railway deployment (~2 min)
- [ ] Validate production (test suite against Railway URL)
- [ ] Update documentation (this file, README)
- [ ] Create PR with deployment summary

---

## Contact & Support

**Project:** Daydreamer Memory Sovereignty Platform
**Repository:** DayDreamerAI/daydreamer-mcp (private)
**Deployment:** DayDreamerAI/ai-garden-railway-mcp (public)
**Production:** https://ai-garden-railway-mcp-production.up.railway.app

**Created:** October 5, 2025
**Last Updated:** October 5, 2025
**Status:** Production (Tier 1: 5 tools deployed)

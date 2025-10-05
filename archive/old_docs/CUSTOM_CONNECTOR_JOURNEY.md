# Custom Connector Integration Journey
**Railway MCP Server with Claude Custom Connectors**

## Success Status: ✅ WORKING (Oct 5, 2025)

**Current deployment:** https://ai-garden-railway-mcp-production.up.railway.app/sse
**Working server:** `minimal_sse_server.py` (SSE dual-endpoint pattern)
**Database:** Neo4j AuraDB (neo4j+s://8c3b5488.databases.neo4j.io:7687)

---

## The Challenge

Connect Claude Desktop (and Claude Web/Mobile) to a Railway-hosted MCP server with Neo4j AuraDB backend via Custom Connectors.

**Goal:** Enable remote MCP tools (not just local stdio servers) for:
- Cross-platform access (Desktop, Web, Mobile)
- Cloud-hosted memory (AuraDB)
- Platform independence (any MCP client)

---

## What Worked (Final Solution)

### SSE Dual-Endpoint Pattern

Custom Connectors require **two endpoints**:

1. **`/sse` endpoint** (GET) - Establishes SSE connection
   - Returns `event: endpoint` with URI for message posting
   - Keeps connection alive with keepalive comments
   - Sends all responses via SSE stream

2. **`/messages` endpoint** (POST) - Receives JSON-RPC messages
   - Query param: `?session_id=<uuid>`
   - Returns responses via SSE stream (not HTTP response body)
   - Handles: initialize, tools/list, tools/call, notifications/*

### Key Implementation Details

**Endpoint Event Format** (Critical):
```python
# ✅ CORRECT - Send just the URI
await response.write(f"event: endpoint\ndata: /messages?session_id={session_id}\n\n".encode())

# ❌ WRONG - Don't wrap in JSON-RPC
# This causes client to POST to URL-encoded JSON path
endpoint_message = {"jsonrpc": "2.0", "method": "endpoint", "params": {"uri": "/messages?..."}}
```

**Neo4j Result Iteration** (Critical):
```python
# ✅ CORRECT - Result is iterator, not list
for i, record in enumerate(result):
    if i >= limit:
        break
    # process record

# ❌ WRONG - Result object not subscriptable
for record in result[:limit]:  # ERROR: 'Result' object is not subscriptable
```

**Session Management**:
```python
sse_sessions = {}  # session_id -> StreamResponse

# Store session when SSE connects
sse_sessions[session_id] = response

# Send responses via stored session
async def send_sse_message(session_id: str, message: dict):
    response = sse_sessions[session_id]
    data = json.dumps(message)
    await response.write(f"data: {data}\n\n".encode())
```

**Notifications Handling**:
```python
# Notifications don't get responses
if method.startswith("notifications/"):
    return None  # Return 204 No Content from HTTP handler
```

---

## What Didn't Work (Trial & Error)

### Attempt 1: Simple POST Endpoint ❌
**Tried:** Single `/mcp` endpoint accepting POST requests
**Failed:** Custom Connectors need SSE transport, not just POST
**Error:** No tools appeared in Claude Desktop

### Attempt 2: POST + GET with JSON info ❌
**Tried:** GET `/mcp` returns server info JSON
**Failed:** Client expects SSE stream, not JSON
**Error:** Client abandoned connection

### Attempt 3: HTTP Wrapper for stdio Server ❌
**Tried:** Wrap `daydreamer-mcp-memory_server.py` (stdio) with HTTP
**Failed:** Can't easily convert stdio to SSE, complex dependencies
**Error:** Server initialization failures (missing imports)

### Attempt 4: Endpoint as JSON-RPC Message ❌
**Tried:** Send endpoint wrapped in JSON-RPC format
**Failed:** Client treated entire JSON as URL (URL-encoded path)
**Error:** `POST /%7B%22jsonrpc%22:%20%222.0%22...` (404)

### Attempt 5: Neo4j Result Slicing ❌
**Tried:** `for record in result[:limit]`
**Failed:** Result object is iterator, not subscriptable
**Error:** `'Result' object is not subscriptable`

---

## Protocol Flow (Working)

### Connection Establishment
```
1. Client  → GET /sse (Accept: text/event-stream)
2. Server → event: endpoint
            data: /messages?session_id=<uuid>
3. Server → : keepalive (every 30s)
```

### Tool Discovery
```
4. Client  → POST /messages?session_id=<uuid>
            {"jsonrpc":"2.0","id":1,"method":"initialize",...}
5. Server → data: {"jsonrpc":"2.0","id":1,"result":{...}}
            (via SSE stream)

6. Client  → POST /messages?session_id=<uuid>
            {"jsonrpc":"2.0","method":"notifications/initialized"}
7. Server → 204 No Content (notifications don't get responses)

8. Client  → POST /messages?session_id=<uuid>
            {"jsonrpc":"2.0","id":2,"method":"tools/list"}
9. Server → data: {"jsonrpc":"2.0","id":2,"result":{"tools":[...]}}
            (via SSE stream)
```

### Tool Execution
```
10. Client → POST /messages?session_id=<uuid>
            {"jsonrpc":"2.0","id":3,"method":"tools/call","params":{
              "name":"raw_cypher_query",
              "arguments":{"query":"MATCH (n) RETURN n LIMIT 5"}
            }}
11. Server → data: {"jsonrpc":"2.0","id":3,"result":{"content":[...]}}
            (via SSE stream)
```

---

## Files Reference

### Core Server (Working)
- **`minimal_sse_server.py`** - 350 lines, SSE dual-endpoint, 1 tool (raw_cypher_query)
- **`minimal_test_server.py`** - Previous POST-only attempt (doesn't work)
- **`mcp_http_wrapper.py`** - First HTTP wrapper attempt (deprecated)

### v5.0 Memory Server (Future)
- **`mcp_v5_http_wrapper.py`** - HTTP wrapper for full v5.0 server (untested)
- **`daydreamer_mcp_memory_server.py`** - v5.0 stdio server with 27 tools
- **`jina_v3_optimized_embedder.py`** - JinaV3 embeddings
- **`conversational_memory_search.py`** - Enhanced search
- **`v6_mcp_bridge.py`** - V6 observation nodes bridge
- **`tools/`** - conversation_tools.py, observation_search.py

### Configuration
- **`railway.toml`** - Railway deployment config (health checks, start command)
- **`Procfile`** - Railway process file
- **`requirements.txt`** - Python dependencies (minimal: neo4j, aiohttp, python-dotenv)

### Documentation
- **`CUSTOM_CONNECTOR_SETUP.md`** - User setup guide
- **`seed_auradb.py`** - Seed test data script

---

## Environment Variables (Railway)

```bash
# Neo4j AuraDB
NEO4J_URI=neo4j+s://8c3b5488.databases.neo4j.io:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=<password>

# Railway
PORT=8080  # Auto-set by Railway
```

---

## Testing & Validation

### Manual Testing
```bash
# 1. Health check
curl https://ai-garden-railway-mcp-production.up.railway.app/health

# 2. Test initialize (POST)
curl -X POST https://ai-garden-railway-mcp-production.up.railway.app/mcp \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}'

# 3. Test tools/list (POST)
curl -X POST https://ai-garden-railway-mcp-production.up.railway.app/mcp \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}'
```

### Custom Connector Setup
1. Open Claude Desktop Settings
2. Add Custom Connector:
   - Name: "Daydreamer Memory (AuraDB)"
   - URL: `https://ai-garden-railway-mcp-production.up.railway.app/sse`
   - Auth: None (authless for now)
3. Restart Claude Desktop
4. Tool should appear in "Search and tools"

### Expected Logs (Railway)
```
🔗 SSE connection established: <session_id>
📍 [<session>] Sent endpoint: /messages?session_id=<uuid>
📨 [<session>] initialize
📤 [<session>] Sent: response
📨 [<session>] notifications/initialized
📨 [<session>] tools/list
📤 [<session>] Sent: response
📨 [<session>] tools/call
📤 [<session>] Sent: response
```

---

## Deployment Steps

### Initial Setup
```bash
# 1. Clone repo
git clone https://github.com/DayDreamerAI/ai-garden-railway-mcp.git
cd ai-garden-railway-mcp

# 2. Create Railway project
railway init

# 3. Set environment variables
railway variables set NEO4J_URI="neo4j+s://..."
railway variables set NEO4J_USERNAME="neo4j"
railway variables set NEO4J_PASSWORD="..."

# 4. Deploy
git push origin main
# Railway auto-deploys
```

### Updates
```bash
# Make changes
git add -A
git commit -m "feat: description"
git push origin main
# Railway auto-deploys (3-5 min)
```

---

## Common Issues & Solutions

### Issue: Tools not appearing in Claude Desktop
**Symptoms:** Custom Connector connects but shows 0 tools
**Causes:**
1. Wrong endpoint (using `/mcp` instead of `/sse`)
2. Endpoint event format wrong (wrapped in JSON-RPC)
3. tools/list not being called (session disconnected)

**Solution:**
- Use `/sse` endpoint URL
- Check Railway logs for `tools/list` request
- Restart Claude Desktop to reconnect

### Issue: "Tool execution failed"
**Symptoms:** Tool appears but fails when executed
**Causes:**
1. Neo4j query error (Result slicing)
2. Session disconnected before execution
3. Response not sent via SSE

**Solution:**
- Check Railway logs for error messages
- Fix Neo4j query iteration (use enumerate, not slice)
- Ensure responses sent via `send_sse_message()`

### Issue: Session disconnects after 5 minutes
**Symptoms:** Works initially, then stops responding
**Causes:**
1. Client timeout (Claude Desktop closes connection)
2. No keepalive sent
3. Railway load balancer timeout

**Solution:**
- Send keepalive comments every 30s: `await response.write(b": keepalive\n\n")`
- Client auto-reconnects on next use

### Issue: Railway health checks failing
**Symptoms:** Deployment fails, "service unavailable"
**Causes:**
1. `/health` endpoint missing
2. Server not binding to PORT env var
3. Startup errors (imports, Neo4j connection)

**Solution:**
- Implement `/health` endpoint returning JSON
- Use `PORT = int(os.environ.get('PORT', 8080))`
- Check Railway logs for startup errors

---

## Key Learnings

1. **Custom Connectors use SSE, not simple POST** - Dual-endpoint pattern is mandatory
2. **Endpoint event must be plain URI** - Not wrapped in JSON-RPC format
3. **Responses via SSE, not HTTP body** - Even though client POSTs, responses come via SSE stream
4. **Neo4j Result is iterator** - Can't slice, must enumerate
5. **Notifications are fire-and-forget** - Return 204, no response needed
6. **Health checks are critical** - Railway needs `/health` returning 200
7. **Session management matters** - Store SSE responses, send via correct session

---

## Future Enhancements

### Short Term
- [ ] Add v5.0 memory server with all 27 tools
- [ ] Implement proper error responses (MCP error codes)
- [ ] Add request timeout handling
- [ ] Better logging (structured JSON logs)

### Medium Term
- [ ] OAuth authentication (replace authless)
- [ ] Rate limiting per session
- [ ] Connection pool optimization
- [ ] Metrics/monitoring (Prometheus)

### Long Term
- [ ] Multi-user support (user-specific AuraDB instances)
- [ ] WebSocket transport (in addition to SSE)
- [ ] Tool permission system
- [ ] Streaming responses for long-running queries

---

## References

- **MCP Specification:** https://modelcontextprotocol.io/docs/concepts/transports
- **MCP Python SDK:** https://github.com/modelcontextprotocol/python-sdk
- **SSE Spec:** https://html.spec.whatwg.org/multipage/server-sent-events.html
- **Railway Docs:** https://docs.railway.app/
- **Neo4j Python Driver:** https://neo4j.com/docs/python-manual/current/

---

**Last Updated:** Oct 5, 2025
**Status:** Production Ready ✅
**Commit:** 0f60c8b

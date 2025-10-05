# Railway MCP Server Deployment Guide
**Quick Start for Custom Connector Remote Servers**

## Prerequisites

- Railway account (https://railway.app)
- Neo4j AuraDB instance (or local Neo4j)
- GitHub account (for auto-deploy)
- Claude Desktop (for testing Custom Connectors)

---

## Option 1: Deploy This Repo (Minimal Server)

### Step 1: Fork & Configure

```bash
# 1. Fork this repo on GitHub
# 2. Clone your fork
git clone https://github.com/YOUR_USERNAME/ai-garden-railway-mcp.git
cd ai-garden-railway-mcp

# 3. Create Railway project
railway init
railway link  # Select your project
```

### Step 2: Set Environment Variables

```bash
# Neo4j connection (AuraDB or local)
railway variables set NEO4J_URI="neo4j+s://your-instance.databases.neo4j.io:7687"
railway variables set NEO4J_USERNAME="neo4j"
railway variables set NEO4J_PASSWORD="your-password"

# PORT is auto-set by Railway, but can override:
# railway variables set PORT="8080"
```

### Step 3: Deploy

```bash
# Push to trigger deployment
git push origin main

# Railway auto-deploys (3-5 min)
# Check logs: railway logs
```

### Step 4: Test Deployment

```bash
# Check health
curl https://your-app.up.railway.app/health

# Expected response:
# {
#   "status": "healthy",
#   "neo4j_connected": true,
#   "active_sessions": 0,
#   "version": "1.0.0"
# }
```

### Step 5: Add to Claude Desktop

1. Open Claude Desktop → Settings → Custom Connectors
2. Add connector:
   - **Name:** Your Server Name
   - **URL:** `https://your-app.up.railway.app/sse`
   - **Auth:** None (authless)
3. Save & restart Claude Desktop
4. Tool should appear in "Search and tools"

---

## Option 2: Create New Server From Template

### File Structure

```
your-mcp-server/
├── server.py              # Main SSE server (copy from minimal_sse_server.py)
├── railway.toml           # Railway config
├── Procfile              # Process definition
├── requirements.txt      # Python dependencies
└── README.md
```

### Minimal Server Template

**`server.py`** (Simplified from minimal_sse_server.py):

```python
#!/usr/bin/env python3
import os
import json
import asyncio
from uuid import uuid4
from aiohttp import web
from dotenv import load_dotenv

load_dotenv()

PORT = int(os.environ.get('PORT', 8080))

# SSE sessions
sse_sessions = {}

async def handle_sse(request):
    """Establish SSE connection"""
    session_id = str(uuid4())

    response = web.StreamResponse()
    response.headers['Content-Type'] = 'text/event-stream'
    response.headers['Cache-Control'] = 'no-cache'
    response.headers['Access-Control-Allow-Origin'] = '*'
    await response.prepare(request)

    sse_sessions[session_id] = response

    # Send endpoint
    endpoint_uri = f"/messages?session_id={session_id}"
    await response.write(f"event: endpoint\ndata: {endpoint_uri}\n\n".encode())

    # Keepalive
    while True:
        await asyncio.sleep(30)
        try:
            await response.write(b": keepalive\n\n")
        except:
            break

    del sse_sessions[session_id]
    return response

async def handle_post_message(request):
    """Handle JSON-RPC messages"""
    session_id = request.query.get('session_id')

    if not session_id or session_id not in sse_sessions:
        return web.json_response({"error": "Invalid session"}, status=400)

    data = await request.json()
    method = data.get("method", "")

    # Handle notifications (no response)
    if method.startswith("notifications/"):
        return web.Response(status=204)

    # Handle initialize
    if method == "initialize":
        result = {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {
                "name": "your-server",
                "version": "1.0.0"
            }
        }
        response = {
            "jsonrpc": "2.0",
            "id": data.get("id"),
            "result": result
        }

        # Send via SSE
        sse_response = sse_sessions[session_id]
        await sse_response.write(f"data: {json.dumps(response)}\n\n".encode())
        return web.json_response(response)

    # Add your tool handlers here
    # ...

    return web.json_response({"error": "Not implemented"}, status=501)

async def health_check(request):
    return web.json_response({"status": "healthy"})

async def main():
    app = web.Application()
    app.router.add_get('/sse', handle_sse)
    app.router.add_post('/messages', handle_post_message)
    app.router.add_get('/health', health_check)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()

    print(f"Server listening on http://0.0.0.0:{PORT}")
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
```

**`railway.toml`:**

```toml
[build]
buildCommand = "pip install -r requirements.txt"

[deploy]
startCommand = "python -u server.py"
healthcheckPath = "/health"
healthcheckTimeout = 300
restartPolicyType = "never"
```

**`Procfile`:**

```
web: python -u server.py
```

**`requirements.txt`:**

```
aiohttp>=3.9.0
python-dotenv
```

---

## Adding Tools

### Tool Registration (tools/list)

```python
elif method == "tools/list":
    result = {
        "tools": [
            {
                "name": "your_tool",
                "description": "What your tool does",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "param1": {
                            "type": "string",
                            "description": "Parameter description"
                        }
                    },
                    "required": ["param1"]
                }
            }
        ]
    }
    # Send via SSE...
```

### Tool Execution (tools/call)

```python
elif method == "tools/call":
    tool_name = data.get("params", {}).get("name")
    arguments = data.get("params", {}).get("arguments", {})

    if tool_name == "your_tool":
        # Execute your tool logic
        result_text = f"Tool executed with {arguments}"

        result = {
            "content": [
                {
                    "type": "text",
                    "text": result_text
                }
            ]
        }
        # Send via SSE...
```

---

## Troubleshooting

### Health Check Fails

**Problem:** Railway shows "service unavailable"

**Solution:**
1. Check server binds to Railway's PORT: `PORT = int(os.environ.get('PORT', 8080))`
2. Verify `/health` endpoint returns 200
3. Check Railway logs for startup errors

### Tools Not Appearing

**Problem:** Custom Connector connects but 0 tools

**Solution:**
1. Verify URL ends with `/sse` (not `/mcp`)
2. Check Railway logs for `tools/list` request
3. Restart Claude Desktop
4. Test manually:
```bash
curl -X POST https://your-app.up.railway.app/mcp \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}'
```

### Tool Execution Fails

**Problem:** Tool appears but fails when called

**Solution:**
1. Check Railway logs for error messages
2. Verify responses sent via SSE (not HTTP body)
3. Test tool logic separately

### Session Disconnects

**Problem:** Works initially, stops after 5 minutes

**Solution:**
1. Send keepalive comments every 30s
2. Client auto-reconnects on next use
3. Check Railway logs for disconnection reason

---

## Cost Considerations

**Railway Pricing** (as of Oct 2025):
- **Hobby Plan:** $5/month + usage ($0.000231/GB-hour)
- **Typical MCP server:** ~$10-15/month total
- **Pro Plan:** $20/month + usage (better for production)

**Neo4j AuraDB Pricing:**
- **Free Tier:** Limited (good for testing)
- **Professional:** $65/month (production)
- **Enterprise:** Custom pricing

**Total Infrastructure Cost** (per user):
- Railway: ~$10/month
- AuraDB Pro: $65/month
- **Total: ~$75/month**

---

## Scaling Considerations

### Single User
- Minimal server (1 tool) works fine
- Railway Hobby plan sufficient
- AuraDB Free tier for testing

### Multi-User (Future)
- User-specific database instances
- Connection pooling critical
- Railway Pro plan recommended
- Load balancing for >100 concurrent users

### Performance Optimization
- Connection pool size tuning
- Query result caching
- Async database operations
- Prometheus monitoring

---

## Security Checklist

- [ ] Never commit credentials (use Railway env vars)
- [ ] Enable HTTPS (Railway provides automatically)
- [ ] Implement rate limiting (future)
- [ ] Add OAuth authentication (future)
- [ ] Regular security audits
- [ ] Log sensitive data handling
- [ ] API key rotation policy

---

## Next Steps

1. **Local Testing:** Test server locally before deploying
2. **Staging Environment:** Use Railway preview deployments
3. **Monitoring:** Set up Railway metrics alerts
4. **Backup Strategy:** AuraDB auto-backups enabled
5. **Documentation:** Keep deployment docs updated

---

## Resources

- **This Repo:** Working SSE implementation
- **CUSTOM_CONNECTOR_JOURNEY.md:** Detailed trial-and-error learnings
- **Railway Docs:** https://docs.railway.app/
- **MCP Specification:** https://modelcontextprotocol.io/
- **Neo4j Python Driver:** https://neo4j.com/docs/python-manual/

---

**Last Updated:** Oct 5, 2025
**Template Version:** 1.0
**Status:** Production Ready ✅

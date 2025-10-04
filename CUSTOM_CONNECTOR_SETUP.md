# Claude Custom Connector Setup Guide

## Overview

Connect Claude Desktop, Mobile, or ChatGPT to your Daydreamer memory via Railway-hosted MCP server with AuraDB backend.

**Deployment URL**: `https://ai-garden-railway-mcp-production.up.railway.app`

## Prerequisites

- Claude Desktop app installed
- Railway deployment active and healthy
- Bearer token for authentication

## Claude Desktop Setup

### Method 1: Config File (Recommended)

1. **Open Claude Desktop config**:
   - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - Windows: `%APPDATA%\Claude\claude_desktop_config.json`
   - Linux: `~/.config/Claude/claude_desktop_config.json`

2. **Add Custom Connector** to config:

```json
{
  "mcpServers": {
    "daydreamer-memory": {
      "url": "https://ai-garden-railway-mcp-production.up.railway.app/mcp",
      "transport": "sse",
      "headers": {
        "Authorization": "Bearer fe66b963f7e6d338412b65e658d50c0b7d15a30dede727172602c8de9c944b59"
      }
    }
  }
}
```

3. **Restart Claude Desktop**

4. **Verify connection**:
   - Open new conversation
   - Check for MCP tools indicator
   - Test: "Search for Julian Crespi in memory"

### Method 2: UI (if available)

1. Claude Desktop → Settings → Developer → Custom Connectors
2. Add connector:
   - **Name**: Daydreamer Memory
   - **URL**: `https://ai-garden-railway-mcp-production.up.railway.app/mcp`
   - **Transport**: SSE
   - **Auth Type**: Bearer Token
   - **Token**: `fe66b963f7e6d338412b65e658d50c0b7d15a30dede727172602c8de9c944b59`

## ChatGPT Custom Connector Setup

1. **ChatGPT** → Settings → Custom Connectors
2. Add connector:
   - **URL**: `https://ai-garden-railway-mcp-production.up.railway.app/mcp`
   - **Auth**: Bearer Token
   - **Token**: `fe66b963f7e6d338412b65e658d50c0b7d15a30dede727172602c8de9c944b59`
3. Test connection

## Available Tools (22 Memory Operations)

### Core Tools
- `search_nodes` - Semantic search via JinaV3 embeddings
- `create_entities` - Create entities with V6 observation nodes
- `add_observations` - Add observations to existing entities
- `create_relations` - Build relationships between entities
- `memory_stats` - System health metrics

### Conversation Tools
- `search_conversations` - Find sessions by topic/date/activity
- `trace_entity_origin` - Discover which conversations created entities
- `get_temporal_context` - Retrieve conversations around specific dates
- `get_breakthrough_sessions` - Load high-impact conversations

### Advanced Tools
- `virtual_context_search` - 70% token reduction with personality protection
- `conversational_memory_search` - Natural language memory exploration
- `raw_cypher_query` - Direct Neo4j access for operational queries
- `search_observations` - Multi-dimensional filtering (theme, entity, date)

## Testing the Connection

### Health Check
```bash
curl -H "Authorization: Bearer <token>" \
  "https://ai-garden-railway-mcp-production.up.railway.app/health"
# Expected: "OK"
```

### Server Info
```bash
curl -H "Authorization: Bearer <token>" \
  "https://ai-garden-railway-mcp-production.up.railway.app/"
# Expected: JSON with server info, neo4j status
```

### SSE Endpoint
```bash
curl -N -H "Authorization: Bearer <token>" \
  -H "Accept: text/event-stream" \
  "https://ai-garden-railway-mcp-production.up.railway.app/mcp"
# Expected: SSE stream with MCP protocol messages
```

## Troubleshooting

### Connection Refused
- Verify Railway deployment is active
- Check deployment logs for errors
- Confirm environment variables set correctly

### 401 Unauthorized
- Verify bearer token matches Railway environment
- Check `Authorization: Bearer <token>` header format
- Regenerate token if needed: `openssl rand -hex 32`

### 404 Not Found
- Confirm URL ends with `/mcp`
- Check Railway domain is correct
- Verify deployment is from `main` branch

### No Tools Visible in Claude
- Restart Claude Desktop after config change
- Check config file JSON syntax (use JSON validator)
- Verify `transport: "sse"` is set
- Check Claude Desktop logs for errors

### MCP Protocol Errors
- Verify server is responding with `Content-Type: text/event-stream`
- Check Railway logs for protocol errors
- Test with MCP Inspector: `npx @modelcontextprotocol/inspector`

## Security Notes

- **Bearer token is sensitive** - store securely, never commit to git
- **Rotate tokens monthly** - generate new with `openssl rand -hex 32`
- **Rate limiting**: 60 requests/minute per client
- **CORS**: Only allows chat.openai.com, chatgpt.com, claude.ai
- **HTTPS only** - Railway provides automatic SSL certificates

## Environment Variables (Railway Dashboard)

Required variables set in Railway project:

```bash
# AuraDB Connection
NEO4J_URI=neo4j+s://8c3b5488.databases.neo4j.io:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=<auradb-password>

# Security
RAILWAY_BEARER_TOKEN=fe66b963f7e6d338412b65e658d50c0b7d15a30dede727172602c8de9c944b59
REQUIRE_AUTHENTICATION=true
RATE_LIMIT_PER_MINUTE=60

# Transport
MCP_TRANSPORT=sse

# Custom Connector Support
CHATGPT_CUSTOM_CONNECTOR_MODE=true
CLAUDE_CUSTOM_CONNECTOR_MODE=true
ENABLE_CORS=true
CORS_ALLOWED_ORIGINS=https://chat.openai.com,https://chatgpt.com,https://claude.ai
```

## Architecture

```
Claude Desktop/Web/Mobile
    ↓ HTTPS + Bearer Token
Railway MCP Server (SSE Transport)
    ↓ Security Middleware (auth, rate limit, audit)
MCP Protocol Handler
    ↓ bolt+s://
Neo4j AuraDB (Cloud)
```

## Next Steps

1. Test connection from Claude Desktop
2. Verify all 22 memory tools are accessible
3. Test multi-platform: Desktop → Web → Mobile
4. Monitor Railway logs for errors
5. Set up token rotation schedule

## Support

- **Railway Dashboard**: https://railway.com/project/a81d68e2-0f90-4397-a02d-0b12a71d4104
- **GitHub Issues**: https://github.com/DayDreamerAI/daydreamer-mcp/issues
- **MCP Docs**: https://modelcontextprotocol.io/introduction

# Daydreamer Railway MCP Server

**Production Deployment for Claude Custom Connectors**

## 🚀 Live Deployment

- **URL**: https://ai-garden-railway-mcp-production.up.railway.app
- **Protocol**: SSE Transport (Custom Connector compatible)
- **Database**: Neo4j AuraDB InstanceDaydreamer_01

## 🛠️ Current Deployment

### Tier 1: Core Memory Tools (5 tools)

1. **search_nodes** - Semantic search via JinaV3 or exact name lookup
2. **memory_stats** - Graph statistics with V6 status
3. **create_entities** - Entity creation with embeddings
4. **add_observations** - Observation management
5. **raw_cypher_query** - Direct Cypher access

## 📊 Production Data

- **Entities**: 27,487
- **Relationships**: 110,449
- **V6 Observations**: 14,414
- **Conversation Sessions**: 537

## 🔧 Environment Variables

Required environment variables (set in Railway):

```env
NEO4J_URI=neo4j+s://8c3b5488.databases.neo4j.io
NEO4J_PASSWORD=<your-auradb-password>
JINA_API_KEY=<your-jina-api-key>
```

## 📦 Deployment

Railway auto-deploys from `main` branch.

### Manual Deployment

```bash
# Install Railway CLI
brew install railway

# Login
railway login

# Deploy
railway up
```

## 🧪 Testing

```bash
# Test production endpoint
curl https://ai-garden-railway-mcp-production.up.railway.app/health
```

## 📚 Documentation

- **Setup Guide**: See main daydreamer-mcp repository
- **Architecture**: Custom Connector + SSE transport
- **Memory System**: V6 observation nodes, temporal binding

---

**Deployment Version**: Tier 1 (5 tools)
**Last Updated**: $(date +"%Y-%m-%d")
**Source**: Private daydreamer-mcp repository

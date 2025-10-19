# Daydreamer Railway MCP Server

**Production Deployment for Claude Custom Connectors**

**Version**: 6.3.3 (October 19, 2025)

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

- **CHANGELOG**: See [CHANGELOG.md](CHANGELOG.md) for complete version history
- **Setup Guide**: See main daydreamer-mcp repository
- **Architecture**: Custom Connector + SSE transport
- **Memory System**: V6 observation nodes, temporal binding

## 🆕 Recent Updates

**v6.3.3 (October 19, 2025)** - 🔥 CRITICAL FIX:
- ✅ **Memory Monitoring Disabled**: Fixed misleading system memory logs causing mobile connection rejections
- ✅ **Circuit Breaker Working**: Process memory correctly monitored (4.5GB threshold)
- ✅ **Mobile Connections Restored**: 503 errors eliminated

**v6.3.2 (October 18, 2025)** - V6 Compliance & Resource Optimization:
- ✅ **Semantic Theme Classification**: Fixed 97.5% "general" theme bug with lightweight classifier
- ✅ **V5 Timestamp Removal**: 100% V6 compliance with ISO 8601 `created_at` properties
- ✅ **Resource Optimization**: CPU-only mode for Railway environment
- ✅ **Memory Efficiency**: Lazy initialization, pattern-based classification

**Impact**: Production stability restored, proper theme distribution, V6 schema compliance

---

**Deployment Version**: Tier 1 (5 tools) | v6.3.3
**Last Updated**: October 19, 2025
**Source**: Private daydreamer-mcp repository

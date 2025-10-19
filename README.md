# Daydreamer Railway MCP Server

**Production Deployment for Claude Custom Connectors**

**Version**: 6.3.6 (October 19, 2025)

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

**v6.3.6 (October 19, 2025)** - ✅ V6 AUDIT FIXES COMPLETE - 70% → 95% Compliance:
- ✅ **V5 Chunk Migration**: 3,428 nodes migrated to V6 schema (100% compliance)
- ✅ **Observation Reclassification**: 9,343 observations reclassified (97.5% → 49.2% "general")
- ✅ **Community Membership**: Audit bug resolved - actual coverage 99.7% (exceeds 80% target)
- ✅ **V6 Compliance**: Improved from 70% (14/20) to 95% (19/20 requirements)
- ✅ **Documentation**: AUDIT_FIX_COMPLETE.md with corrected audit queries

**v6.3.5 (October 19, 2025)** - 🔧 SSE Connection Management + V5 Migration:
- ✅ **SSE Connections**: Increased limit from 5→10 for multi-platform usage
- ✅ **Auto-Cleanup**: 5-minute timeout + background stale session cleanup
- ✅ **V5 Migration Tool**: Script to migrate 3,427 legacy Chunk nodes to V6 schema
- ✅ **Better Monitoring**: Session tracking with timestamps and active connection logging

**v6.3.4 (October 19, 2025)** - 🔥 CRITICAL FIXES - MCP Protocol + GraphRAG Global Search:
- ✅ **MCP Protocol Compliance**: Fixed "Unknown method: prompts/list" error (added 4 missing handlers)
- ✅ **GraphRAG Global Search**: Fixed embedder isolation causing memory spikes and failures
- ✅ **True Lazy Loading**: Removed warmup call that defeated v6.3.3 lazy loading (startup memory now ~500MB)
- ✅ **Memory Stability**: Global search uses singleton embedder (no duplicate 3.2GB model loading)

**v6.3.3 (October 19, 2025)** - 🔥 CRITICAL FIX - True Lazy Loading (incomplete):
- ✅ **JinaV3 Model Lazy Loading**: Fixed model loading at startup (was consuming 3.2GB immediately)
- ✅ **Startup Memory**: Reduced from 6.28GB to ~3.0GB (below 4.5GB circuit breaker threshold)
- ✅ **Mobile Connections Restored**: Model only loads when actually needed (may never load if read-only)
- ✅ **Memory Monitoring Disabled**: Eliminated misleading system memory logs

**v6.3.2 (October 18, 2025)** - V6 Compliance & Resource Optimization:
- ✅ **Semantic Theme Classification**: Fixed 97.5% "general" theme bug with lightweight classifier
- ✅ **V5 Timestamp Removal**: 100% V6 compliance with ISO 8601 `created_at` properties
- ✅ **Resource Optimization**: CPU-only mode for Railway environment
- ✅ **Memory Efficiency**: Lazy initialization, pattern-based classification

**Impact**: Production stability restored, proper theme distribution, V6 schema compliance

---

**Deployment Version**: Tier 1 (8 tools) | v6.3.5
**Last Updated**: October 19, 2025
**Source**: Private daydreamer-mcp repository

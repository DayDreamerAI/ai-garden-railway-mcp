# Daydreamer Railway MCP Server

**Production Deployment for Claude Custom Connectors**

**Version**: 6.7.1 (October 22, 2025)
**Stdio Parity**: 100% (17/17 tools)

## 🚀 Live Deployment

- **URL**: https://ai-garden-railway-mcp-production.up.railway.app
- **Protocol**: SSE Transport (Custom Connector compatible)
- **Database**: Neo4j AuraDB InstanceDaydreamer_01
- **Architecture**: Railway = stdio v6.7.0 + SSE transport (ONE CANONICAL LOGIC)

## 🛠️ Complete Tool Suite (17 Tools - 100% Stdio Parity)

### Entity & Observation Management (5 tools)
1. **create_entities** - Create entities with V6 observations, JinaV3 embeddings, MVCM
2. **add_observations** - Add observations with direct Cypher, semantic themes, MVCM entity mentions
3. **search_nodes** - Semantic search via JinaV3 256D or exact name/alias lookup
4. **create_relations** - Create entity relationships with canonical types
5. **search_observations** - Multi-dimensional filtering (theme, entity, date, confidence)

### Conversation & Temporal Tools (4 tools)
6. **search_conversations** - Search preserved conversation sessions by topic/date/activity
7. **trace_entity_origin** - Find which conversations created/discussed an entity
8. **get_temporal_context** - Get conversations within time window around specific dates
9. **get_breakthrough_sessions** - Retrieve high-importance conversation sessions

### GraphRAG Advanced Search (2 tools)
10. **graphrag_global_search** - Community-level synthesis across 241 Leiden clusters
11. **graphrag_local_search** - Entity neighborhood exploration with multi-hop traversal

### System Management (3 tools)
12. **memory_stats** - System health, embedding coverage, V6 compliance metrics
13. **raw_cypher_query** - Direct Neo4j Cypher access for operational queries
14. **generate_embeddings_batch** - JinaV3 256D batch embedding generation (Railway cloud-native)

### Advanced Memory Tools (3 tools - Stubs)
15. **conversational_memory_search** - Natural language memory search (fallback to enhanced_search)
16. **virtual_context_search** - 70% token reduction search (fallback to regular search)
17. **lightweight_embodiment** - <4K token startup protocol (recommend full PBC via Claude Code)

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

### Optional Performance Variables

```env
EMBEDDING_TIMEOUT=40        # Default: 40 seconds (configured for Railway CPU)
ENABLE_AUTO_UNLOAD=false    # Default: false (keep model resident)
```

**EMBEDDING_TIMEOUT**: Maximum time to wait for embedding generation before fallback.
- **Default**: 40 seconds (allows ~24s CPU model load + safety buffer)
- **Configured**: Optimized for Railway CPU lazy loading

**ENABLE_AUTO_UNLOAD**: Whether to unload JinaV3 model after idle timeout.
- **Default**: false (model stays resident once loaded)
- **Benefit**: Instant subsequent queries, no reload needed
- **Memory**: ~3.7GB persistent (acceptable for Railway environment)

## ⚡ Performance Characteristics

### JinaV3 Lazy Loading (CPU Environment)

**First Embedding Request** (~24 seconds):
- Model downloads from HuggingFace (if not cached)
- 3.2GB model loads into CPU memory
- Int8 quantization applied
- 256D Matryoshka truncation configured

**Subsequent Requests** (instant):
- Model stays resident in memory
- No reload required until Railway container restarts
- Fast inference on all embedding operations

**Memory Profile**:
- Startup: ~500MB (no model loaded)
- After first embedding: ~3.7GB (model + base server)
- Peak: ~4.2GB (during embedding generation)

**Why Lazy Loading?**:
- Prevents 6.28GB startup memory spike (exceeded Railway's 4.5GB threshold)
- Enables mobile/web connections without memory circuit breaker
- Optimal for read-only sessions (never loads model if no embeddings needed)
- Implemented in v6.3.3 (October 19, 2025)

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

# Test search (triggers JinaV3 lazy load on first request)
# Expect: ~24s first time, instant subsequent requests
```

## 📚 Documentation

### Quick Links

- **[CHANGELOG.md](CHANGELOG.md)** - Complete version history (v6.3.6: 95% V6 compliance)
- **[docs/audits/](docs/audits/)** - V6 compliance audits and responses
  - Latest: 19/20 (95%) - October 19, 2025
  - All fixes documented and validated
- **[docs/](docs/)** - Technical documentation and deployment guides

### System Status

- **V6 Compliance**: 19/20 (95%) ✅ PRODUCTION READY
- **Architecture**: Custom Connector + SSE transport
- **Memory System**: V6 observation nodes with temporal binding
- **GraphRAG**: Phase 3 complete (241 communities, global/local search operational)

## 🆕 Recent Updates

**v6.7.1 (October 22, 2025)** - 🔧 STDIO SYNC - Observation Source Property:
- ✅ **Source Property Added**: Observations now include `source` property for provenance tracking
- ✅ **Stdio Parity Maintained**: Matches stdio v6.7.0 post-Oct 21 fixes
- ✅ **Backward Compatible**: Defaults to "manual-reflection" for existing workflows
- ✅ **Schema Compliant**: Full V6 observation property compliance (id, content, created_at, semantic_theme, conversation_id, source)

**v6.7.0 (October 20, 2025)** - 🎯 COMPLETE STDIO PARITY - 47% → 100% Tool Coverage:
- ✅ **V6 Bridge Removed**: Deprecated V6MCPBridge replaced with direct Cypher implementation (stdio v6.6.0)
- ✅ **Direct Cypher**: Stdio-identical observation creation with MVCM entity mentions
- ✅ **MVCM Integration**: Automatic entity mention detection via concept extraction (stdio v6.7.0)
- ✅ **9 New Tools**: create_relations, search_observations, 4 conversation tools, 3 advanced stubs
- ✅ **Tool Parity**: 8 tools → 17 tools (100% stdio v6.7.0 feature parity)
- ✅ **ONE CANONICAL LOGIC**: Railway = stdio + SSE transport (zero logic variations)
- ✅ **Schema Compliance**: Updated paths to `/llm/memory/standards/MEMORY_V6_COMPLIANCE_STANDARDS.md`
- ✅ **SemanticThemeClassifier**: 9 themes + MVCM concept extraction integrated directly
- ✅ **Localhost Protection**: Triple-layer security preventing local connections (stdio v5.1.0)

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

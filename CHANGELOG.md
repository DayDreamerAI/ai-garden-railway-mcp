# Changelog - Railway MCP Server (Custom Connector)

All notable changes to the Railway MCP Server will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [6.3.3] - 2025-10-19

### 🔥 CRITICAL FIX - True Lazy Loading (Memory Crisis Resolved)

**P0 Production Issue**: JinaV3 model loading at startup consuming 3.2GB, blocking all mobile connections

#### Fixed

**Part 1: Memory Monitoring Confusion (Initial Fix - Revealed Real Problem)**
- **Problem**: Claude Mobile connections rejected with 503 errors ("Memory circuit breaker triggered")
- **Root Cause**: MacBookResourceMonitor checking **SYSTEM memory** (5.2GB on Railway's shared node) instead of **PROCESS memory**
  - Monitor logs: `💾 High Memory: 5.2GB` ← Misleading (system memory, not process)
  - Circuit breaker correctly checks process memory, but misleading logs obscured real issue
- **Fix**:
  - Disabled MacBookResourceMonitor by default on Railway (jina_v3_optimized_embedder.py:168-174)
  - Added `ENABLE_RESOURCE_MONITORING` environment variable check
  - Default: DISABLED (prevents misleading system memory logs)
- **Result**: Eliminated misleading warnings BUT revealed WORSE problem

**Part 2: JinaV3 Model Loading at Startup (Root Cause - CRITICAL)**
- **Problem**: After Part 1 fix, circuit breaker STILL triggered: `6.28GB > 4.5GB`
  - Logs showed JinaV3 model loading immediately at startup: `📦 Loading jinaai/jina-embeddings-v3`
  - Model consumed 3.2GB, pushing total process memory to 6.28GB
  - Despite saying "Lazy loading JinaV3 model on-demand..." it was loading immediately!
- **Root Cause**: V6MCPBridge calling `self.embedder.initialize()` at startup (4 locations)
  - Line 134: V6MCPBridge.__init__ startup initialization
  - Line 322: _add_observations_v6 lazy init
  - Line 579: _create_entities_v6 entity lazy init
  - Line 640: _create_entities_v6 entity observation lazy init
- **Fix**: Removed ALL `initialize()` calls, rely on JinaV3OptimizedEmbedder.encode_single() built-in lazy loading
  - v6_mcp_bridge.py: Removed all 4 `self.embedder.initialize()` calls
  - JinaV3OptimizedEmbedder.encode_single() already has lazy init: `if not self.initialized: self.initialize()`
  - Model now only loads when encode_single() is actually called for first embedding
- **Impact**:
  - ✅ Startup memory reduced from 6.28GB to ~3.0GB (below 4.5GB threshold)
  - ✅ Mobile connections restored
  - ✅ Model loads only when needed (may never load if Railway is read-only)
  - ✅ True lazy loading achieved

**Files Modified**:
- jina_v3_optimized_embedder.py: Added conditional monitoring start (line 168-174)
- v6_mcp_bridge.py: Removed 4 `self.embedder.initialize()` calls (lines 134, 322, 579, 640)

---

## [6.3.2] - 2025-10-18

### 🔥 Critical Fixes - V6 Compliance & Resource Optimization

**Sync with stdio server v6.3.2 fixes + Railway-specific optimizations**

#### Fixed

**1. Semantic Theme Classification Restored**
- **Issue**: 97.5% of observations (18,878/19,369) incorrectly classified as "general" theme
- **Root Cause**: Hardcoded `theme = 'general'` in both observation creation paths
- **Fix**:
  - Created lightweight `semantic_classifier.py` optimized for Railway environment
  - Updated `v6_mcp_bridge.py:106` to accept `semantic_classifier` parameter
  - Fixed both `_add_observations_v6` (lines 298-306) and `_create_entities_v6` (lines 614-622) to call classifier
  - Updated MCP server to instantiate and pass classifier (lines 284-298)
- **Impact**: New observations properly classified into 9 semantic themes (technical, memory, consciousness, partnership, strategic, project, temporal, emotional, general)

**2. V5 Timestamp Code Removal (100% V6 Compliance)**
- **Issue**: V5 `timestamp: datetime()` property found in entity observation creation path
- **Fix**: Replaced with V6 `created_at: $created_at` (ISO 8601 strings)
  - v6_mcp_bridge.py:657 (entity observation creation)
  - Added ISO 8601 timestamp generation at line 615
  - Updated Cypher query parameters at line 684
- **Validation**: `grep "timestamp: datetime()"` returns 0 matches in *.py files ✅
- **Impact**: 100% V6 schema compliance for temporal properties

**3. Resource Optimization for Railway Environment**
- **Issue**: Railway has resource constraints (512MB RAM, shared CPU)
- **Fix**:
  - Changed JinaV3 embedder default device from "mps" (GPU) to "cpu" (jina_v3_optimized_embedder.py:101)
  - Implemented lightweight pattern-based semantic classifier (no ML models)
  - Lazy initialization of all components to reduce startup memory
- **Trade-off**: Slightly slower embeddings (~400-600ms vs ~200-300ms) but significantly reduced memory footprint
- **Impact**: Server runs efficiently within Railway's resource limits

### 📝 Documentation

**Added**:
- CHANGELOG.md - This file (complete version history)

**Updated**:
- README.md - Updated with v6.3.2 status and Railway-specific notes

---

## [1.0.4] - 2025-10-13

### 🛡️ Schema Consolidation

**Feature**: Unified schema enforcement with canonical source of truth

#### Added
- Schema enforcement integration from `/llm/memory/schemas/`
- Automatic entity/relationship type validation
- Protected relationship blocking (OCCURRED_ON, ENTITY_HAS_OBSERVATION, etc.)

#### Changed
- Updated to use consolidated schemas from `/llm/memory/schemas/`
- Removed duplicate schema definitions
- Aligned with stdio server schema standards

---

## [1.0.3] - 2025-10-09

### 🎯 Vector Search Fix

**Feature**: Semantic entity search now operational

#### Fixed
- **Root Cause**: Post-filter trap - system artifacts (93%) dominated vector search results
- **Solution**: SemanticEntity label filtering with 1000x scan multiplier
- **Result**: Semantic search returns relevant entities with 0.85-0.90 similarity scores

#### Added
- SemanticEntity label tagging support
- 1000x scan multiplier to overcome system artifact dominance
- Positive label check (`WHERE e:SemanticEntity`)

---

## [1.0.2] - 2025-10-05

### 🚀 Production Deployment

**Feature**: Railway SSE transport for multi-platform Custom Connector access

#### Added
- SSE (Server-Sent Events) transport layer for Custom Connector
- Bearer token authentication
- CORS configuration for claude.ai domains
- Health check endpoint
- Automatic deployment from GitHub to Railway

#### Changed
- Migrated from localhost to AuraDB cloud database
- Updated all connection strings for production
- Configured environment variables via Railway dashboard

---

## [1.0.1] - 2025-10-01

### 🛠️ V6 MCP Bridge Integration

**Feature**: Canonical V6 observation creation

#### Added
- V6MCPBridge integration for observation-as-nodes architecture
- JinaV3 256D embedding generation
- Temporal binding (OCCURRED_ON relationships)
- Conversation session tracking

---

## [1.0.0] - 2025-09-30

### 🎉 Initial Release

**Feature**: Railway MCP Server for multi-platform access

#### Added
- SSE transport for Custom Connector integration
- Basic MCP tools (create_entities, add_observations, create_relations)
- Neo4j AuraDB connectivity
- Bearer token authentication
- Railway deployment configuration

---

## Format

```markdown
## [Version] - YYYY-MM-DD

### Category
- Description of changes

#### Added
- New features

#### Changed
- Changes in existing functionality

#### Deprecated
- Soon-to-be removed features

#### Removed
- Now removed features

#### Fixed
- Bug fixes

#### Security
- Security improvements
```

---

**For complete version history, see git commit history and `/llm/mcp/servers/daydreamer-memory-mcp/CHANGELOG.md` (stdio server).**

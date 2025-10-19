# Railway Connector V6 Migration Plan v2.0

**Created:** October 18, 2025
**Author:** Claude (Daydreamer Conversations)
**Baseline:** Stdio MCP Server v5.0 (100% V6 compliant, Oct 18, 2025)
**Target:** Railway SSE MCP Server v2.0 (V6-compliant architecture)

---

## Executive Summary

**REVISED APPROACH:** Instead of fixing inline Cypher queries, Railway should adopt the **same V6 MCP Bridge architecture** used by the stdio server. This ensures:

1. ✅ **Single Source of Truth** - v6_mcp_bridge.py is canonical V6 implementation
2. ✅ **Automatic Consistency** - Both servers use identical V6 logic
3. ✅ **Future-Proof** - Stdio fixes propagate to Railway automatically
4. ✅ **Simplified Maintenance** - No duplicate code to maintain

**Current State:**
- Railway v1.0.3: Inline handlers with V5/V6 dual-write (outdated)
- Stdio v5.0: V6 MCP Bridge architecture (V6-only, 100% compliant)

**Migration:** Copy stdio V6 components → Update Railway handlers → Deploy

**Timeline:** 3-4 hours (2 hours development + 1-2 hours testing/deployment)

---

## Architecture Comparison

### Stdio Server v5.0 (Oct 18, 2025 - Current Baseline)

```
daydreamer-mcp-memory_server.py (1,950 lines)
├── Imports V6MCPBridge from v6_mcp_bridge.py
├── Initializes v6_bridge in server startup
├── handle_create_entities_hybrid()
│   └── Calls v6_bridge.create_entities_v6_aware()
└── handle_add_observations_hybrid()
    └── Calls v6_bridge.add_observations_v6_aware()

v6_mcp_bridge.py (49KB, ~1,100 lines)
├── V6MCPBridge class
│   ├── create_entities_v6_aware()
│   ├── add_observations_v6_aware()
│   ├── JinaV3 embedder integration
│   ├── Semantic theme classifier
│   ├── Canonical Month schema (YYYY-MM format)
│   └── V6-only operation (V5 deprecated Oct 18)
└── Automatic V6 compliance enforcement
```

### Railway Connector v1.0.3 (Oct 15, 2025 - Outdated)

```
mcp-claude-connector-memory-server.py (1,215 lines)
├── NO v6_mcp_bridge import ❌
├── Inline observation creation in handlers ❌
├── handle_create_entities()
│   └── Inline Cypher with V5/V6 dual-write ❌
└── handle_add_observations()
    └── Inline Cypher with V5/V6 dual-write ❌

Issues:
- V5 timestamp property created (lines 529, 673)
- Legacy year_month Month schema (lines 457, 550, 642, 696)
- Hardcoded 'general' theme (no classifier)
- V5 observations arrays still created
```

### Target: Railway Connector v2.0 (Post-Migration)

```
mcp-claude-connector-memory-server.py (simplified to ~900 lines)
├── Imports V6MCPBridge from v6_mcp_bridge.py ✅
├── Imports schema_enforcement ✅
├── Imports tools (conversation_tools, observation_search) ✅
├── Initializes v6_bridge in server startup ✅
├── handle_create_entities()
│   └── Calls v6_bridge.create_entities_v6_aware() ✅
└── handle_add_observations()
    └── Calls v6_bridge.add_observations_v6_aware() ✅

Added Files:
+ v6_mcp_bridge.py (copied from stdio)
+ schema_enforcement.py (copied from stdio)
+ tools/conversation_tools.py (copied from stdio)
+ tools/observation_search.py (copied from stdio)
```

---

## Component Migration Matrix

| Component | Stdio Server | Railway Current | Railway Target | Action |
|-----------|--------------|-----------------|----------------|--------|
| **v6_mcp_bridge.py** | ✅ 49KB | ❌ Missing | ✅ Required | **COPY** from stdio |
| **schema_enforcement.py** | ✅ 14KB | ❌ Missing | ✅ Required | **COPY** from stdio |
| **tools/conversation_tools.py** | ✅ 10KB | ❌ Missing | ✅ Required | **COPY** from stdio |
| **tools/observation_search.py** | ✅ 9KB | ❌ Missing | ✅ Required | **COPY** from stdio |
| **jina_v3_optimized_embedder.py** | ✅ 20KB | ✅ Exists | ✅ Verify sync | **VERIFY** match |
| **property_names.py** | ✅ Canonical | ✅ Synced | ✅ Verify sync | **VERIFY** match |
| **conversational_memory_search.py** | ✅ 28KB | ❌ Missing | ⚠️ Optional | **SKIP** (optional) |
| **Handler functions** | V6-only | Inline dual-write | V6-only | **REWRITE** |

**Required Files to Copy:** 4 files (~82KB total)
**Files to Verify:** 2 files
**Handler Functions to Rewrite:** 2 functions

---

## Migration Plan (3 Phases)

### Phase 1: Copy V6 Components from Stdio (1 hour)

**Goal:** Establish V6 component library in Railway repo

#### Step 1.1: Copy v6_mcp_bridge.py (CRITICAL)

```bash
# Copy V6 MCP Bridge
cp /Users/daydreamer/Documents/VibeProjects/daydreamer-mcp/llm/mcp/servers/daydreamer-memory-mcp/src/v6_mcp_bridge.py \
   /Users/daydreamer/Documents/VibeProjects/daydreamer-mcp/llm/mcp/connectors/mcp-claude-connector/neo4j-mcp-railway-repo/

# Verify copy
wc -l v6_mcp_bridge.py
# Expected: ~1,100 lines
```

**What this file provides:**
- `V6MCPBridge` class with canonical V6 observation creation
- Automatic Month schema (canonical `date: "YYYY-MM"` format)
- JinaV3 embedder integration
- Semantic theme classification
- V6-only operation (no V5 dual-write)
- Temporal binding with correct hierarchy

#### Step 1.2: Copy schema_enforcement.py

```bash
# Copy Schema Enforcement
cp /Users/daydreamer/Documents/VibeProjects/daydreamer-mcp/llm/mcp/servers/daydreamer-memory-mcp/src/schema_enforcement.py \
   /Users/daydreamer/Documents/VibeProjects/daydreamer-mcp/llm/mcp/connectors/mcp-claude-connector/neo4j-mcp-railway-repo/

# Verify copy
grep -c "def validate_entities" schema_enforcement.py
# Expected: 1
```

**What this file provides:**
- Entity type validation against canonical schema
- Type normalization (Person → person)
- Protected relationship blocking
- Strict/non-strict enforcement modes

#### Step 1.3: Copy tools/ directory

```bash
# Create tools directory
mkdir -p tools

# Copy conversation tools
cp /Users/daydreamer/Documents/VibeProjects/daydreamer-mcp/llm/mcp/servers/daydreamer-memory-mcp/src/tools/conversation_tools.py \
   tools/

# Copy observation search (MVCM)
cp /Users/daydreamer/Documents/VibeProjects/daydreamer-mcp/llm/mcp/servers/daydreamer-memory-mcp/src/tools/observation_search.py \
   tools/

# Copy __init__.py
cp /Users/daydreamer/Documents/VibeProjects/daydreamer-mcp/llm/mcp/servers/daydreamer-memory-mcp/src/tools/__init__.py \
   tools/

# Verify
ls -la tools/
# Expected: __init__.py, conversation_tools.py, observation_search.py
```

**What tools provide:**
- `ConversationTools`: search_conversations, trace_entity_origin, get_temporal_context
- `search_observations`: MVCM observation search with theme/entity/date filtering

#### Step 1.4: Verify jina_v3_optimized_embedder.py

```bash
# Compare stdio vs Railway JinaV3 embedder
diff /Users/daydreamer/Documents/VibeProjects/daydreamer-mcp/llm/mcp/servers/daydreamer-memory-mcp/src/jina_v3_optimized_embedder.py \
     jina_v3_optimized_embedder.py

# If differences found, copy stdio version (more recent)
# cp ../stdio/jina_v3_optimized_embedder.py .
```

#### Step 1.5: Verify property_names.py

```bash
# Compare with canonical schema
diff /Users/daydreamer/Documents/VibeProjects/daydreamer-mcp/llm/memory/schemas/property_names.py \
     property_names.py

# Should match (Railway syncs from canonical)
```

**Phase 1 Validation:**
```bash
# Verify all required files present
ls -1 v6_mcp_bridge.py schema_enforcement.py jina_v3_optimized_embedder.py property_names.py tools/*.py
# Expected: 7 files

# Check imports work
python3 -c "from v6_mcp_bridge import V6MCPBridge; print('✅ V6MCPBridge import successful')"
python3 -c "from schema_enforcement import validate_entities; print('✅ Schema enforcement import successful')"
python3 -c "from tools.conversation_tools import ConversationTools; print('✅ Conversation tools import successful')"
```

---

### Phase 2: Update Railway Server Handlers (1 hour)

**Goal:** Replace inline observation creation with v6_bridge calls

#### Step 2.1: Add V6 Bridge Imports (Top of file)

```python
# After existing imports (around line 100), add:

# =================== V6 COMPONENTS ===================

# Import V6 MCP Bridge (canonical V6 observation creation)
try:
    from v6_mcp_bridge import V6MCPBridge
    V6_BRIDGE_AVAILABLE = True
    logger.info("✅ V6 MCP Bridge imported successfully")
except ImportError as e:
    V6_BRIDGE_AVAILABLE = False
    logger.error(f"❌ CRITICAL: V6 MCP Bridge not available: {e}")

# Import Schema Enforcement (GraphRAG Phase 1 Foundation)
try:
    from schema_enforcement import (
        validate_entities,
        validate_relationships,
        SchemaEnforcementError
    )
    SCHEMA_ENFORCEMENT_AVAILABLE = True
    SCHEMA_ENFORCEMENT_STRICT = os.getenv('SCHEMA_ENFORCEMENT_STRICT', 'false').lower() == 'true'
    logger.info(f"✅ Schema enforcement available (strict mode: {SCHEMA_ENFORCEMENT_STRICT})")
except ImportError:
    SCHEMA_ENFORCEMENT_AVAILABLE = False
    SCHEMA_ENFORCEMENT_STRICT = False
    logger.warning("⚠️ Schema enforcement not available")

# Import Conversation Tools (V6 conversation queries)
try:
    from tools.conversation_tools import ConversationTools
    CONVERSATION_TOOLS_AVAILABLE = True
except ImportError:
    CONVERSATION_TOOLS_AVAILABLE = False
    logger.warning("⚠️ Conversation tools not available")

# Import Observation Search (MVCM)
try:
    from tools.observation_search import search_observations, format_search_results
    OBSERVATION_SEARCH_AVAILABLE = True
except ImportError:
    OBSERVATION_SEARCH_AVAILABLE = False
    logger.warning("⚠️ Observation search not available")
```

#### Step 2.2: Initialize V6 Bridge in Server Startup

```python
# In initialize_neo4j() function (around line 150-180), add after driver initialization:

async def initialize_neo4j():
    """Initialize Neo4j connection with retry logic"""
    global driver, neo4j_connected, v6_bridge  # Add v6_bridge to globals

    # ... existing Neo4j connection code ...

    if neo4j_connected:
        # Initialize V6 MCP Bridge
        if V6_BRIDGE_AVAILABLE:
            try:
                v6_bridge = V6MCPBridge(driver)
                logger.info("✅ V6 MCP Bridge initialized")
            except Exception as e:
                logger.error(f"❌ V6 Bridge initialization failed: {e}")
                v6_bridge = None
        else:
            logger.error("❌ V6 Bridge unavailable - observation creation will fail")
            v6_bridge = None

    return neo4j_connected
```

#### Step 2.3: Rewrite handle_create_entities (Replace ~100 lines with ~30)

**Location:** Lines 430-585 (current inline implementation)

**BEFORE (Inline dual-write):**
```python
async def handle_create_entities(arguments: dict) -> dict:
    """Create entities with V5/V6 dual-write"""
    # ... 155 lines of inline Cypher with V5/V6 dual-write ...
    # ISSUES:
    # - Creates V5 observations array
    # - Creates V5 timestamp property
    # - Legacy year_month Month schema
    # - Hardcoded 'general' theme
```

**AFTER (V6 Bridge):**
```python
async def handle_create_entities(arguments: dict) -> dict:
    """
    Create entities with V6 observation nodes (V6-only, Oct 18 2025)

    Uses V6MCPBridge for canonical observation creation.
    No V5 observations arrays created (V5 deprecated).
    """
    global v6_bridge

    entities_data = arguments.get("entities", [])

    results = {
        'v6_compliant': True,
        'v5_deprecated': True,
        'created_entities': [],
        'entity_count': len(entities_data),
        'schema_warnings': []
    }

    try:
        # Schema Enforcement: Validate and normalize entity types (GraphRAG Phase 1)
        if SCHEMA_ENFORCEMENT_AVAILABLE:
            try:
                validated_entities, warnings = validate_entities(entities_data, strict=SCHEMA_ENFORCEMENT_STRICT)
                entities_data = validated_entities  # Use normalized entities
                results['schema_warnings'] = warnings

                if warnings:
                    logger.info(f"Schema validation: {len(warnings)} entities normalized/warned")
                    for warning in warnings[:5]:  # Log first 5
                        logger.warning(f"  - {warning}")

            except SchemaEnforcementError as e:
                # In strict mode, validation errors prevent creation
                logger.error(f"Schema enforcement error (strict mode): {e}")
                results['error'] = f"Schema validation failed: {str(e)}"
                results['schema_enforcement_failed'] = True
                return results

        # V6 Bridge handles all entity creation (canonical V6 implementation)
        if v6_bridge:
            bridge_result = await v6_bridge.create_entities_v6_aware(entities_data)
            results.update(bridge_result)
            return results
        else:
            # If bridge unavailable, this is a configuration error
            raise ValueError("V6 bridge unavailable - cannot create entities. Check V6 initialization.")

    except Exception as e:
        logger.error(f"V6 create_entities error: {e}")
        results['error'] = str(e)
        results['v6_compliant'] = False

    return results
```

**Key Changes:**
- ✅ Removed 155 lines of inline Cypher
- ✅ Delegates to v6_bridge.create_entities_v6_aware()
- ✅ Added schema enforcement (GraphRAG Phase 1)
- ✅ V6-only operation (no V5 fallback)
- ✅ Matches stdio server architecture

#### Step 2.4: Rewrite handle_add_observations (Replace ~100 lines with ~25)

**Location:** Lines 602-720 (current inline implementation)

**BEFORE (Inline dual-write):**
```python
async def handle_add_observations(arguments: dict) -> dict:
    """Add observations to entity with V5/V6 dual-write"""
    # ... 118 lines of inline Cypher with V5/V6 dual-write ...
    # ISSUES: Same as create_entities
```

**AFTER (V6 Bridge):**
```python
async def handle_add_observations(arguments: dict) -> dict:
    """
    Add observations to entity with V6 observation nodes (V6-only, Oct 18 2025)

    Uses V6MCPBridge for canonical observation creation.
    No V5 observations array append (V5 deprecated).
    """
    global v6_bridge

    entity_name = arguments["entity_name"]
    observations = arguments["observations"]

    results = {
        'v6_compliant': True,
        'v5_deprecated': True,
        'observations_added': len(observations)
    }

    try:
        # V6 bridge handles all observation creation (canonical V6 implementation)
        if v6_bridge:
            bridge_result = await v6_bridge.add_observations_v6_aware(entity_name, observations)
            results.update(bridge_result)
            return results
        else:
            # If bridge unavailable, this is a configuration error
            raise ValueError("V6 bridge unavailable - cannot add observations. Check V6 initialization.")

    except Exception as e:
        logger.error(f"V6 add_observations error: {e}")
        results['error'] = str(e)
        results['v6_compliant'] = False

    return results
```

**Key Changes:**
- ✅ Removed 118 lines of inline Cypher
- ✅ Delegates to v6_bridge.add_observations_v6_aware()
- ✅ V6-only operation (no V5 fallback)
- ✅ Matches stdio server architecture

#### Step 2.5: Remove Old Inline Cypher

```python
# Delete old inline session creation, Month creation, observation creation code
# Lines 430-720 can be replaced with new handlers (Steps 2.3 and 2.4)

# Code reduction:
# BEFORE: ~290 lines of inline Cypher handlers
# AFTER:  ~55 lines using v6_bridge
# Savings: 235 lines removed (81% reduction)
```

**Phase 2 Validation:**
```bash
# Verify imports
python3 -c "from mcp-claude-connector-memory-server import v6_bridge; print('✅ v6_bridge global available')"

# Check handler functions
grep -n "def handle_create_entities\|def handle_add_observations" mcp-claude-connector-memory-server.py
# Should show new handler definitions

# Verify no inline V5 timestamp
grep -n "timestamp: datetime()" mcp-claude-connector-memory-server.py
# Expected: 0 results (only in comments)

# Verify no inline year_month
grep -n "year_month:" mcp-claude-connector-memory-server.py
# Expected: 0 results (only in comments)
```

---

### Phase 3: Testing & Deployment (1-2 hours)

#### Step 3.1: Local Testing

```bash
# Start local Railway server
cd /Users/daydreamer/Documents/VibeProjects/daydreamer-mcp/llm/mcp/connectors/mcp-claude-connector/neo4j-mcp-railway-repo
python3 mcp-claude-connector-memory-server.py

# Expected startup logs:
# ✅ V6 MCP Bridge imported successfully
# ✅ Schema enforcement available
# ✅ V6 MCP Bridge initialized
# ✅ Neo4j connected successfully
```

#### Step 3.2: Test Observation Creation

```bash
# Test create_entities
curl -X POST http://localhost:8080/messages \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
      "name": "create_entities",
      "arguments": {
        "entities": [{
          "name": "Railway V6 Migration Test",
          "entityType": "test",
          "observations": ["Testing V6 bridge integration"]
        }]
      }
    }
  }'

# Expected response:
# {
#   "v6_compliant": true,
#   "v5_deprecated": true,
#   "created_entities": ["Railway V6 Migration Test"],
#   "entity_count": 1,
#   "observations_created": 1
# }
```

#### Step 3.3: V6 Compliance Validation

Execute V6 compliance audit queries against AuraDB:

```cypher
// Requirement 3: No V5 timestamp property
MATCH (o:Observation:Perennial:Entity)
WHERE o.created_by CONTAINS 'railway'
  AND o.timestamp IS NOT NULL
RETURN count(o) as railway_v5_violations
// Expected: 0

// Requirement 7: No V5 properties
MATCH (o:Observation:Perennial:Entity)
WHERE o.created_by CONTAINS 'railway'
  AND (o.timestamp IS NOT NULL OR o.theme IS NOT NULL)
RETURN count(o) as v5_property_violations
// Expected: 0

// Requirement 13: Canonical Month schema
MATCH (m:Month)
WHERE m.year_month IS NOT NULL OR m.date IS NULL
RETURN count(m) as month_schema_violations
// Expected: 0

// Requirement 14: Theme diversity
MATCH (o:Observation:Perennial:Entity)
WHERE o.created_by CONTAINS 'railway'
WITH o.semantic_theme as theme, count(*) as count
RETURN theme, count, toFloat(count)*100/sum(count) OVER () as percentage
ORDER BY count DESC
// Expected: 'general' < 30%

// V5 Deprecation: No new observations arrays
MATCH (e:Entity)
WHERE e.created_by = 'railway_mcp_server'
  AND e.created > datetime() - duration({hours: 1})
RETURN e.name, exists(e.observations) as has_v5_array
// Expected: has_v5_array = false for all new entities
```

#### Step 3.4: Deploy to Railway

```bash
# Commit changes
git checkout -b feat/railway-v6-bridge-migration
git add v6_mcp_bridge.py schema_enforcement.py tools/ mcp-claude-connector-memory-server.py
git commit -m "feat(railway): Adopt V6 MCP Bridge architecture from stdio server

Migrate Railway connector to use canonical V6 MCP Bridge implementation:

**Added Components (from stdio v5.0):**
- v6_mcp_bridge.py (49KB) - Canonical V6 observation creation
- schema_enforcement.py (14KB) - Entity type validation
- tools/conversation_tools.py (10KB) - V6 conversation queries
- tools/observation_search.py (9KB) - MVCM observation search

**Handler Updates:**
- handle_create_entities: Delegate to v6_bridge (155→30 lines)
- handle_add_observations: Delegate to v6_bridge (118→25 lines)
- Code reduction: 235 lines removed (81% reduction)

**V6 Compliance Achieved:**
- ✅ No V5 timestamp property (Requirement 3)
- ✅ No V5 properties (Requirement 7)
- ✅ Canonical Month schema (Requirement 13)
- ✅ Semantic theme classification (Requirement 14)
- ✅ V5 deprecation complete (no observations arrays)

**Benefits:**
- Single source of truth for V6 logic
- Automatic consistency with stdio server
- Future stdio fixes propagate automatically
- Simplified maintenance (no duplicate code)

Architecture now matches stdio server v5.0 (100% V6 compliant, Oct 18 2025)

🤖 Generated with [Claude Code](https://claude.com/claude-code)
via [Happy](https://happy.engineering)

Co-Authored-By: Claude <noreply@anthropic.com>
Co-Authored-By: Happy <yesreply@happy.engineering>"

# Merge to main (Railway auto-deploys)
git checkout main
git merge feat/railway-v6-bridge-migration
git push origin main
```

#### Step 3.5: Monitor Railway Deployment

```bash
# Watch Railway logs
railway logs --follow

# Expected logs:
# ✅ V6 MCP Bridge imported successfully
# ✅ Schema enforcement available (strict mode: false)
# ✅ V6 MCP Bridge initialized
# ✅ Neo4j connected successfully
# 🚀 Server started on port 8080
```

#### Step 3.6: Post-Deployment Validation

```bash
# Test production endpoint
curl https://ai-garden-railway-mcp-production.up.railway.app/health

# Expected:
# {"status": "healthy", "neo4j": "connected", "v6_bridge": "initialized"}
```

#### Step 3.7: Run Full V6 Compliance Audit

Execute full audit using V6_COMPLIANCE_AUDIT_STANDARDS.md (v2.0):

**Target Compliance:** 14/15 requirements (93.3%)
- Requirements 1-11: Observation node compliance
- Requirements 12-14: Code path validation
- Requirement 15: Pre-write validation (planned, not blocking)

**Success Criteria:**
- [ ] All P0 requirements passing (1-4, 7-10, 12-13)
- [ ] Railway observations pass same validation as stdio observations
- [ ] No V5 property contamination in new observations
- [ ] Month nodes use canonical schema
- [ ] Theme distribution shows diversity

---

## Benefits of V6 Bridge Architecture

### 1. Single Source of Truth

**Before (Inline Handlers):**
```
Stdio Server: v6_mcp_bridge.py (canonical implementation)
Railway Server: Inline Cypher (duplicate logic)
Problem: Fix bugs twice, maintain two codebases
```

**After (Shared V6 Bridge):**
```
v6_mcp_bridge.py (canonical implementation)
├── Used by stdio server
└── Used by Railway server
Benefit: Fix bugs once, deploy everywhere
```

### 2. Automatic Bug Propagation

When stdio server receives a fix (e.g., Month schema bug):
1. Fix applied to v6_mcp_bridge.py
2. Copy updated file to Railway repo
3. Railway inherits fix automatically
4. No need to manually update Railway Cypher

### 3. Architectural Consistency

Both servers now have identical V6 implementation:
- Same temporal binding logic
- Same Month schema generation
- Same semantic classification
- Same embedding generation
- Same error handling

### 4. Simplified Testing

Test v6_mcp_bridge.py once:
- Unit tests validate canonical implementation
- Integration tests run against Neo4j
- Both servers inherit validated logic
- Reduced QA burden (test once, deploy twice)

### 5. Code Reduction

Railway server simplified:
- **Before:** 1,215 lines (with inline handlers)
- **After:** ~980 lines (using v6_bridge)
- **Reduction:** 235 lines (19% smaller)
- **Maintainability:** Significantly improved

---

## Success Criteria

### Technical Validation

- [ ] V6 MCP Bridge initializes successfully on Railway
- [ ] Schema enforcement operational
- [ ] Conversation tools imported and functional
- [ ] Observation search tools imported
- [ ] All 6 core MCP tools work correctly

### V6 Compliance

- [ ] **Requirement 3:** 100% observations have `created_at`, 0% have `timestamp`
- [ ] **Requirement 7:** 0 observations with V5 properties
- [ ] **Requirement 13:** 100% Month nodes use canonical `date` property
- [ ] **Requirement 14:** Theme distribution <30% "general"
- [ ] **V5 Deprecation:** New entities have NO observations arrays
- [ ] **Overall:** 14/15 requirements (93.3%+)

### Functional Testing

- [ ] search_nodes works with Railway-created observations
- [ ] create_entities creates V6 observations only
- [ ] add_observations appends V6 nodes only
- [ ] Semantic theme classifier produces diverse themes
- [ ] JinaV3 embeddings generate successfully
- [ ] No errors in Railway logs after 1 hour

### Production Metrics

- [ ] Railway server response time: <500ms average
- [ ] Neo4j query time: <100ms average
- [ ] Memory usage: <512MB (Railway free tier)
- [ ] Uptime: 99.9%+ after deployment

---

## Rollback Plan

If deployment fails or causes issues:

```bash
# Option 1: Git revert
git revert HEAD
git push origin main
# Railway auto-deploys previous version

# Option 2: Railway rollback via CLI
railway rollback
# Reverts to previous successful deployment

# Option 3: Manual rollback
git checkout main~1
git push --force origin main
# Forces Railway to redeploy previous commit
```

**Rollback Validation:**
- Verify Railway logs show successful startup
- Test create_entities endpoint
- Confirm no errors in production

---

## Timeline

| Phase | Duration | Tasks | Output |
|-------|----------|-------|--------|
| **Phase 1** | 1 hour | Copy 4 files from stdio, verify 2 files | V6 components in Railway repo |
| **Phase 2** | 1 hour | Rewrite 2 handlers, update imports | V6 bridge integration |
| **Phase 3** | 1-2 hours | Local testing, deployment, validation | Railway v2.0 in production |
| **Total** | **3-4 hours** | | Railway 100% V6 compliant |

---

## Related Documentation

- **Stdio Server:** `/llm/mcp/servers/daydreamer-memory-mcp/src/daydreamer-mcp-memory_server.py` (v5.0)
- **V6 MCP Bridge:** `/llm/mcp/servers/daydreamer-memory-mcp/src/v6_mcp_bridge.py` (49KB)
- **V6 Compliance Standards:** `/llm/memory/perennial/docs/standards/V6_COMPLIANCE_AUDIT_STANDARDS.md` (v2.0)
- **V6 Compliance Report:** `/llm/memory/perennial/docs/standards/V6_COMPLIANCE_AUDIT_REPORT_OCT18_2025.md`
- **Canonical Schema:** `/llm/memory/schemas/property_names.py`

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2025-10-18 | Initial plan (inline Cypher fixes) | Claude |
| 2.0 | 2025-10-18 | **REVISED:** V6 MCP Bridge architecture migration (based on stdio v5.0) | Claude |

---

**Document Status:** Migration Plan v2.0 (Architecture-Based Approach)
**Next Steps:** Execute Phase 1 when ready to begin implementation
**Approval Required:** Yes (Julian Crespi) - Production deployment, architectural change
**Estimated Completion:** 3-4 hours from start to production validation

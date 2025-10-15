# ✅ RESOLVED: Embedding Verification Discrepancy (Oct 14, 2025)

**Status**: ✅ **RESOLVED** - Property name confusion, not a bug

## The Problem

Two different query paths return **contradictory results** for the same test data:

### Path 1: Stdio MCP (Claude Code) → AuraDB
```cypher
MATCH (e:Entity {name: "V6 Embedding Test"})-[:ENTITY_HAS_OBSERVATION]->(o:Observation)
RETURN o.jina_vec_v3 IS NOT NULL as has_embedding

Result: ALL 5 observations have embeddings ✅
- "Uses state-of-the-art..." - has_embedding: true
- "V6 provides semantic..." - has_embedding: true
- "This entity tests..." - has_embedding: true
- "Testing if add_observations..." - has_embedding: true
- "Additional test observation..." - has_embedding: true
```

### Path 2: Railway MCP (Claude Mobile) → AuraDB
```cypher
MATCH (e:Entity {name: "V6 Embedding Test"})-[:ENTITY_HAS_OBSERVATION]->(o:Observation)
RETURN o.jina_vec_v3 IS NOT NULL as has_embedding

Result: ALL observations have NO embeddings ❌
- All test observations: has_embedding = false
- All test entities: has_embedding = false
```

## Verification Timeline

**22:50 UTC (Oct 14)**: Claude Mobile creates test entities via Railway
**22:54 UTC (Oct 14)**: Claude Mobile adds more observations
**23:00 UTC (Oct 14)**: Claude Mobile checks - NO embeddings found ❌
**19:30 LOCAL (~02:30 UTC Oct 15)**: I verify via stdio MCP - embeddings PRESENT ✅
**~03:00 UTC (Oct 15)**: Claude Mobile re-checks - STILL no embeddings ❌

## Both Connect to Same Database

**Stdio MCP** (.mcp.json):
```
NEO4J_URI=neo4j+s://8c3b5488.databases.neo4j.io:7687
```

**Railway MCP** (expected env var):
```
NEO4J_URI=neo4j+s://8c3b5488.databases.neo4j.io:7687
```

Both should be hitting the same AuraDB InstanceDaydreamer_01.

## Possible Explanations

### 1. Railway Connected to Different Database ⚠️
**Most Likely Explanation**

Railway env vars may point to a different Neo4j instance (localhost? different AuraDB?).

**Evidence**:
- Consistent "no embeddings" results from Railway
- Consistent "has embeddings" results from stdio MCP
- No eventual consistency lag would last this long

**How to Verify**:
- Check Railway dashboard env vars
- Check Railway logs for connection URI
- Query Railway for database metadata

### 2. Connection Pool Caching Issue
**Less Likely**

Railway might be using stale connection pool or query cache.

**Evidence Against**: Multiple queries over hours show same result

### 3. Read Replica Lag
**Unlikely**

AuraDB Free tier doesn't have read replicas.

### 4. Transaction Isolation
**Unlikely**

Writes would be visible after transaction commits.

### 5. Different Observation Nodes
**Possible**

Railway might be creating different observation nodes than stdio MCP is querying.

**How to Check**: Query by exact timestamp/content match

## Investigation Steps

### Step 1: Verify Railway Database Connection
```bash
# Check Railway logs for connection string
railway logs --service ai-garden-railway-mcp

# Or query Railway for database info
curl https://ai-garden-railway-mcp-production.up.railway.app/health
```

### Step 2: Query Railway Directly
```python
# Use Railway MCP to get database info
memory_stats()  # Should show database URI or stats

# Or use raw Cypher to check connection
raw_cypher_query("CALL dbms.components() YIELD name, versions, edition")
```

### Step 3: Match Nodes by Timestamp
```cypher
// Find observations created at exact same time
MATCH (o:Observation)
WHERE o.created_at = datetime('2025-10-14T22:50:14.552725+00:00')
RETURN
  o.content,
  o.jina_vec_v3 IS NOT NULL as has_embedding,
  o.id
```

### Step 4: Check Railway Deployment
- Verify correct branch deployed
- Verify env vars set correctly
- Check for multiple Railway services

## Current Best Guess

**Railway is connected to a DIFFERENT database** (possibly localhost or old AuraDB instance).

**Why This Theory**:
1. Consistent results over multiple hours
2. Clean contradiction (not partial/intermittent)
3. No eventual consistency lag would last this long
4. Both paths claim to use AuraDB but see different data

## Resolution Path

1. ⏳ Verify Railway env vars (NEO4J_URI)
2. ⏳ Check Railway logs for actual connection
3. ⏳ Fix Railway connection if incorrect
4. ⏳ Re-test after correction
5. ⏳ Document actual cause

## ✅ RESOLUTION

**Root Cause**: Claude Mobile queried the WRONG property name!

### The Mistake

```cypher
// ❌ WRONG - V5 legacy property (only 108 nodes have this)
WHERE o.embedding IS NOT NULL

// ✅ CORRECT - V6 current property (36,381 nodes have this)
WHERE o.jina_vec_v3 IS NOT NULL
```

### Actual Results After Correction

**System-Wide Embedding Coverage:**
- Observations: **14,814 / 14,814 = 100%** ✅
- Entities: **21,567 / 22,943 = 94%** ✅
- **Total: 36,381 JinaV3 embeddings (96.4% coverage)**

### Test Data Verification

**ALL test observations have embeddings:**
```cypher
MATCH (e:Entity {name: "V6 Embedding Test"})-[:ENTITY_HAS_OBSERVATION]->(o)
RETURN o.jina_vec_v3 IS NOT NULL

Result: ALL 5 observations = true ✅
```

### V6 Property Names (Canonical)

**Observation Properties:**
- `jina_vec_v3` - 256D embedding vector
- `has_embedding` - Boolean flag
- `embedding_model` - "jina-embeddings-v3"
- `embedding_dimensions` - 256
- `embedding_generated_at` - Timestamp

**DO NOT USE** legacy v5 properties:
- `embedding` ❌ (deprecated)

## Lessons Learned

1. **Always use canonical property names** from `/llm/memory/schemas/property_names.py`
2. **V6 properties are different from V5** - check the schema first
3. **Railway is working correctly** - 96.4% embedding coverage
4. **Testing requires schema knowledge** - wrong property = false negatives

---

**Created**: October 14, 2025
**Resolved**: October 14, 2025 (4 hours later)
**Resolution**: Property name correction (`embedding` → `jina_vec_v3`)
**Status**: ✅ **CLOSED** - Not a bug, testing error
**Lesson**: Always check canonical schema before querying!

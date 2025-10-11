# Railway V6 Observation Validation Queries

**Created**: October 10, 2025
**Purpose**: Correct property names and query patterns for Railway MCP V6 observations

---

## Critical Property Name Differences

| What You Were Querying | Actual Property Name | Status |
|------------------------|---------------------|--------|
| `o.embedding_jina_v3` ❌ | `o.jina_vec_v3` ✅ | MISMATCH |
| `o.session_id` ❌ | `o.conversation_id` ✅ | MISMATCH |
| `o.content` ✅ | `o.content` ✅ | CORRECT |

---

## Test 1: Check Recent Observations with CORRECT Properties

```cypher
// Find recent observations created via Railway MCP
MATCH (o:Observation:Perennial)
WHERE o.source = 'mcp_tool'
  AND o.created_by = 'railway_mcp_v6_handler'
  AND o.created_at > datetime('2025-10-10T00:00:00')
RETURN
  o.id as observation_id,
  o.content as content,
  o.conversation_id as conversation_id,  // ← NOT session_id
  o.has_embedding as has_embedding,
  o.jina_vec_v3 IS NOT NULL as embedding_exists,  // ← NOT embedding_jina_v3
  o.embedding_model as model,
  o.embedding_dimensions as dimensions,
  o.created_at as created_at
ORDER BY o.created_at DESC
LIMIT 10
```

---

## Test 2: Validate Complete Graph Structure

```cypher
// Check observation with ALL relationships and properties
MATCH (o:Observation {id: $observation_id})
OPTIONAL MATCH (entity:Entity)-[:ENTITY_HAS_OBSERVATION]->(o)
OPTIONAL MATCH (o)-[:OCCURRED_ON]->(day:Day)
OPTIONAL MATCH (day)-[:PART_OF_MONTH]->(month:Month)
OPTIONAL MATCH (month)-[:PART_OF_YEAR]->(year:Year)
OPTIONAL MATCH (session:ConversationSession {session_id: o.conversation_id})

RETURN
  // Observation properties
  o.id as observation_id,
  o.content as content,
  o.conversation_id as conversation_id,
  o.source as source,
  o.created_by as created_by,
  o.semantic_theme as theme,

  // Embedding properties
  o.has_embedding as has_embedding,
  o.jina_vec_v3 IS NOT NULL as embedding_vector_exists,
  size(o.jina_vec_v3) as embedding_size,  // Should be 256
  o.embedding_model as embedding_model,
  o.embedding_dimensions as embedding_dimensions,

  // Relationships
  entity.name as linked_entity,
  day.date as temporal_day,
  month.year_month as temporal_month,
  year.year as temporal_year,
  session.session_id as session_found,

  // Validation flags
  entity IS NOT NULL as has_entity_link,
  day IS NOT NULL as has_temporal_binding,
  session IS NOT NULL as session_exists
```

---

## Test 3: Check Embedding Generation Status

```cypher
// Count observations by embedding status
MATCH (o:Observation:Perennial)
WHERE o.source = 'mcp_tool'
  AND o.created_at > datetime('2025-10-10T00:00:00')
WITH
  count(o) as total_observations,
  count(CASE WHEN o.has_embedding = true THEN 1 END) as claimed_embeddings,
  count(CASE WHEN o.jina_vec_v3 IS NOT NULL THEN 1 END) as actual_embeddings,
  count(CASE WHEN o.conversation_id IS NOT NULL THEN 1 END) as has_conversation_id
RETURN
  total_observations,
  claimed_embeddings,
  actual_embeddings,
  has_conversation_id,
  claimed_embeddings = actual_embeddings as embedding_match
```

---

## Test 4: Verify Relationship Patterns

```cypher
// Check relationship directions (CORRECT pattern per local validation)
MATCH (o:Observation:Perennial)
WHERE o.id = $observation_id
OPTIONAL MATCH (entity)-[:ENTITY_HAS_OBSERVATION]->(o)  // Entity → Observation (CORRECT)
OPTIONAL MATCH (session)-[:CONVERSATION_SESSION_ADDED_OBSERVATION]->(entity)
RETURN
  entity.name as entity_name,
  type((entity)-[]-(o)) as relationship_type,
  session.session_id as session_id,
  exists((entity)-[:ENTITY_HAS_OBSERVATION]->(o)) as has_correct_direction
```

---

## Expected Results (If Working Correctly)

### For add_observations Response:
```json
{
  "v5_completed": true,
  "v6_completed": true,
  "observations_added": 3,
  "session_id": "session_2025-10-10T..._abc123",
  "observation_ids": ["uuid1", "uuid2", "uuid3"],
  "observations_created": 3,
  "embeddings_generated": 3  // ← Should match actual_embeddings from Test 3
}
```

### For Graph Query (Test 2):
```
✅ has_embedding: true
✅ embedding_vector_exists: true
✅ embedding_size: 256
✅ embedding_model: "jina-embeddings-v3"
✅ conversation_id: "session_2025-10-10T..._abc123"
✅ has_entity_link: true
✅ has_temporal_binding: true
✅ session_exists: true
```

---

## Troubleshooting Guide

### If embeddings_generated > 0 but embedding_vector_exists = false:

1. **Check JinaV3 initialization in Railway logs**:
   - Look for: `"✅ JinaV3 embedder initialized"`
   - Or: `"⚠️ JinaV3 initialization failed"`

2. **Verify property naming**:
   - Use `o.jina_vec_v3` NOT `o.embedding_jina_v3`
   - Use `o.conversation_id` NOT `o.session_id`

3. **Check embedding vector storage**:
   ```cypher
   MATCH (o:Observation {id: $obs_id})
   RETURN
     o.jina_vec_v3[0..5] as first_5_dims,  // First 5 dimensions
     size(o.jina_vec_v3) as vector_length
   ```

### If session_exists = false:

The ConversationSession is created with:
```cypher
MATCH (session:ConversationSession {session_id: o.conversation_id})
```

Session should exist if V6 handler ran correctly. Check:
```cypher
MATCH (session:ConversationSession)
WHERE session.session_id STARTS WITH 'session_2025-10-10'
RETURN session.session_id, session.source, session.context
ORDER BY session.created_at DESC
LIMIT 10
```

---

## Relationship Pattern (Validated Oct 10, 2025)

**CORRECT Railway Pattern** (matches local validation):
```
(Entity)-[:ENTITY_HAS_OBSERVATION]->(Observation)
(ConversationSession)-[:CONVERSATION_SESSION_ADDED_OBSERVATION]->(Entity)
(Observation)-[:OCCURRED_ON]->(Day)
```

**NOT** the reverse direction. This is the validated V6 architecture.

---

## Next Steps for Validation

1. Run **Test 1** with CORRECT property names (`jina_vec_v3`, `conversation_id`)
2. If embeddings still NULL, run **Test 3** to compare claimed vs actual
3. Check Railway deployment logs for JinaV3 initialization messages
4. Run **Test 2** on one specific observation ID to verify complete structure

**Expected Outcome**: If Railway is deployed correctly (commit bbc5e5d), all tests should pass with the correct property names.

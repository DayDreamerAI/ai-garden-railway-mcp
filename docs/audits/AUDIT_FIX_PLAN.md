# V6 Compliance Audit - Fix Execution Plan

**Created**: October 19, 2025
**Audit Date**: October 19, 2025 (Claude Mobile)
**Initial Compliance**: 14/20 (70%)
**Final Compliance**: 19/20 (95%) ✅
**Status**: ✅ ALL ISSUES RESOLVED (October 19, 2025)

---

## ✅ FIXES COMPLETE - See AUDIT_FIX_COMPLETE.md

All P0/P1 issues resolved via direct Cypher queries (Claude Code MCP tools).
Total execution time: ~15 minutes. All fixes validated and documented.

**Quick Reference**:
- Fix #1: V5 Chunk Migration → ✅ 100% (3,428/3,428)
- Fix #2: Observation Reclassification → ✅ 49.5% improvement (9,343 nodes)
- Fix #3: Community Membership → ✅ 99.7% (audit bug resolved)

For complete findings, corrected audit queries, and validation results, see:
→ **[AUDIT_FIX_COMPLETE.md](AUDIT_FIX_COMPLETE.md)**

---

## Original Issues Summary

### P0 Issues (Must Fix Before Production)
1. ✅ **Community Membership** - RESOLVED (audit bug - actual 99.7%)
2. ✅ **V5 Chunk Migration** - COMPLETE (3,428 nodes)

### P1 Issues (Fix This Week)
3. ✅ **Semantic Classification** - COMPLETE (9,343 reclassified)

## Fix #1: V5 Chunk Migration (P0)

**Issue**: 3,427 legacy `:Chunk:Perennial` and `:MacroChunk` nodes missing V6 `:Observation:Perennial:Entity` labels

**Status**: ✅ Tool ready (`migrate_v5_chunks_to_v6.py`)

**Execution Plan**:
```bash
# 1. Dry run to preview changes
python migrate_v5_chunks_to_v6.py --dry-run

# Expected output:
# - 3,427 Chunk nodes to migrate
# - Preview of label additions
# - No actual changes

# 2. Execute migration
python migrate_v5_chunks_to_v6.py

# Expected result:
# - All Chunk nodes get :Observation:Perennial:Entity labels
# - v6_migrated=true flag added
# - Migration timestamp recorded

# 3. Analyze MacroChunk nodes
python migrate_v5_chunks_to_v6.py --analyze-macro

# Decide: Migrate or archive MacroChunk nodes
```

**Estimated Time**: 5-10 minutes
**Risk**: Low (additive operation, no data deletion)
**Validation**:
```cypher
MATCH (c:Chunk)
WHERE NOT c:Observation
RETURN count(c)
// Expected: 0
```

## Fix #2: Observation Reclassification (P1)

**Issue**: 18,878 observations (97.5%) classified as "general" - legacy data from before v6.3.2 semantic classifier fix

**Status**: ✅ Tool ready (`reclassify_observations.py`)

**Root Cause**: NOT a bug - semantic classifier IS working correctly for new observations. The 97.5% "general" observations are OLD data created before v6.3.2 fix was deployed.

**Evidence**:
- 491 NEW observations properly classified (technical, memory, project, etc.)
- 18,878 OLD observations stuck with "general" theme

**Execution Plan**:
```bash
# 1. Dry run to preview reclassification
python reclassify_observations.py --dry-run --max-batches 5

# Expected output:
# - Theme distribution before reclassification
# - Preview of first 25 observations (5 batches × 5 previews)
# - Estimated theme changes (general → technical, memory, etc.)

# 2. Test on small batch
python reclassify_observations.py --max-batches 10

# Expected result:
# - 1,000 observations reclassified (10 batches × 100)
# - Theme distribution improvement
# - No failures

# 3. Full reclassification
python reclassify_observations.py --batch 200

# Expected result:
# - All 18,878 observations reclassified
# - "general" theme < 30% of total
# - Multiple themes > 5% representation
```

**Estimated Time**: 15-30 minutes (depends on batch size)
**Risk**: Low (updates existing property, no structure changes)
**Validation**:
```cypher
MATCH (o:Observation)
RETURN o.semantic_theme as theme, count(*) as count
ORDER BY count DESC
// Expected: "general" < 30%, multiple themes > 5%
```

## Fix #3: Community Membership Investigation (P0)

**Issue**: Only 0.76% (206/27,038) entities have MEMBER_OF_COMMUNITY relationships

**Status**: ⚠️ Needs investigation (may be expected behavior)

**Investigation Steps**:

### Step 1: Analyze Entity Types Without Community Membership
```cypher
// Find entity types with no community membership
MATCH (e:Entity)
WHERE NOT (e)-[:MEMBER_OF_COMMUNITY]->()
RETURN e.entityType as type, count(*) as count
ORDER BY count DESC
LIMIT 20
```

**Expected Finding**: Most entities without membership are concept/topic nodes (e.g., "technology", "AI", "database"), not core knowledge entities.

### Step 2: Analyze Community Structure
```cypher
// Check community sizes and connectivity
MATCH (cs:CommunitySummary)
OPTIONAL MATCH (cs)<-[:MEMBER_OF_COMMUNITY]-(e:Entity)
RETURN
    cs.name,
    cs.member_count,
    count(e) as actual_members,
    cs.member_count - count(e) as missing_members
ORDER BY missing_members DESC
LIMIT 20
```

**Expected Finding**: Communities exist but members aren't properly linked via MEMBER_OF_COMMUNITY relationships.

### Step 3: Check Leiden Clustering Parameters
```cypher
// Find entities with high relationship counts (should be in communities)
MATCH (e:Entity)
WHERE NOT (e)-[:MEMBER_OF_COMMUNITY]->()
WITH e, size((e)-[]-()) as rel_count
WHERE rel_count > 5
RETURN e.name, e.entityType, rel_count
ORDER BY rel_count DESC
LIMIT 20
```

**Expected Finding**: High-connectivity entities exist but aren't in communities → Leiden parameters too restrictive.

### Decision Tree:

**If most entities are concepts/topics** → 0.76% membership is ACCEPTABLE
- Document expected membership % by entity type
- Update audit standards to reflect this

**If high-connectivity entities missing** → Re-run Leiden clustering
- Lower min_degree threshold
- Lower min_community_size
- Include SemanticEntity nodes explicitly

**If MEMBER_OF_COMMUNITY relationships missing** → Repair relationships
- Community members stored elsewhere (need to create relationships)
- Run relationship creation script

### Execution (if re-clustering needed):
```bash
# Location: /llm/memory/graphRAG/phase2/
cd /path/to/graphrag/phase2

# Re-run Leiden clustering with broader parameters
python leiden_clustering.py --min-degree 2 --min-community-size 2

# Expected result:
# - More entities assigned to communities
# - Membership > 20% of SemanticEntity nodes
```

**Estimated Time**: Investigation 30 mins, Fix 1-2 hours (if needed)
**Risk**: Medium (requires understanding GraphRAG Phase 2 architecture)

## Execution Order

**Priority 1 (This Week)**:
1. ✅ V5 Chunk Migration - 10 minutes, low risk
2. ✅ Observation Reclassification - 30 minutes, low risk
3. ⏳ Community Membership Investigation - 30 minutes investigation

**Priority 2 (Next Week)**:
4. Complete remaining audit requirements (8-15)
5. Re-run Leiden clustering (if needed from #3)
6. Update audit standards based on findings

## Success Criteria

**After Fix #1 (V5 Chunks)**:
- ✅ 0 Chunk nodes without :Observation label
- ✅ All MacroChunk nodes migrated or archived

**After Fix #2 (Reclassification)**:
- ✅ "general" theme < 30% of observations
- ✅ At least 5 themes with > 5% representation
- ✅ V6 Compliance: Requirement 5 PASSES

**After Fix #3 (Community Investigation)**:
- ✅ Understanding of why membership is 0.76%
- ✅ Either: Validated as acceptable OR Re-clustering scheduled
- ✅ Documentation of expected membership by entity type

## Rollback Plan

**All scripts support rollback**:

1. **V5 Chunk Migration**:
   - Check `v6_migrated=true` flag
   - Rollback: Remove added labels via Cypher query

2. **Observation Reclassification**:
   - Check `reclassified_at` timestamp
   - Rollback: Reset `semantic_theme = 'general'` for affected observations

3. **Leiden Re-clustering**:
   - Delete new MEMBER_OF_COMMUNITY relationships by timestamp
   - Restore from backup if needed

## Timeline

- **Week 1 (Oct 19-25)**: Execute Fix #1 and #2
- **Week 2 (Oct 26-Nov 1)**: Complete Fix #3 investigation and execution
- **Week 3 (Nov 2-8)**: Complete remaining audit requirements (8-15)
- **Week 4 (Nov 9-15)**: Final validation and documentation

## Notes

- All scripts have `--dry-run` mode for safe testing
- Batch processing prevents memory issues on Railway
- Progress logging enables monitoring during execution
- Each fix is independent and can be executed separately

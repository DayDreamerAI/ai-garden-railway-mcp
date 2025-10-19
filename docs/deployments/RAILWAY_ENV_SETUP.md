# Railway Environment Variable Setup Guide
**Created**: October 18, 2025
**Purpose**: Enable GraphRAG Phase 3 tools in Railway deployment

## Issue Discovery

**Mobile Audit Finding**: GraphRAG tools disabled despite infrastructure being ready
- ✅ 241 community nodes with embeddings and summaries
- ✅ 1,379 entities connected via MEMBER_OF_COMMUNITY
- ❌ Feature flags show `graphrag_enabled: false`

**Root Cause**: Railway dashboard environment variables not configured

## Required Environment Variables

### GraphRAG Phase 3 Feature Flags

Add these to Railway dashboard → Environment Variables:

```bash
GRAPHRAG_ENABLED=true
GRAPHRAG_GLOBAL_SEARCH=true
GRAPHRAG_LOCAL_SEARCH=true
```

### How Environment Variables Work in Railway

**Priority Order** (highest to lowest):
1. Railway Dashboard Environment Variables (overrides everything)
2. `.env.production` file in repository (committed, but overridden)
3. `.env` file in repository (not committed, local only)

**Current State**:
- ✅ `.env.production` has flags set to `true` (lines 130-132)
- ❌ Railway dashboard variables override this to `false`

## Setup Steps

### Via Railway Dashboard

1. Go to Railway project: <https://railway.app/project/your-project-id>
2. Click on **Variables** tab
3. Add three new variables:
   - `GRAPHRAG_ENABLED` = `true`
   - `GRAPHRAG_GLOBAL_SEARCH` = `true`
   - `GRAPHRAG_LOCAL_SEARCH` = `true`
4. Click **Deploy** to restart server with new variables

### Via Railway CLI (Alternative)

```bash
# Set environment variables
railway variables set GRAPHRAG_ENABLED=true
railway variables set GRAPHRAG_GLOBAL_SEARCH=true
railway variables set GRAPHRAG_LOCAL_SEARCH=true

# Redeploy
railway up
```

## Verification

### 1. Check Feature Flags via MCP

After Railway redeploys, test from Claude Mobile:

```python
# Use memory_stats tool
{
  "graphrag_enabled": true,  # ← Should be true
  "graphrag_global_search": true,  # ← Should be true
  "graphrag_local_search": true   # ← Should be true
}
```

### 2. Test Global Search

```python
# Test global search tool
graphrag_global_search(
  query="What is Daydreamer's core architecture?"
)
# Should return: Community-level synthesis results
```

### 3. Test Local Search

```python
# Test local search tool
graphrag_local_search(
  entity_name="Claude (Daydreamer Conversations)"
)
# Should return: Entity neighborhood with relationships
```

## Expected Impact

**Before** (Current State):
- Mobile Audit: 15/20 passing (75%)
- Requirement 20: ❌ FAILING (tools disabled)

**After** (Environment Variables Set):
- Mobile Audit: 18/20 passing (90%)
- Requirement 20: ✅ PASSING (tools enabled and functional)

## Deployment Timeline

**Code Deployment**: ✅ Complete (commit `5e470d4` pushed Oct 18, 20:08)
**Railway Auto-Deploy**: ⏳ In progress (typical: 2-5 minutes)
**Environment Variables**: ⏳ Pending manual setup via Railway dashboard

**Note**: Code deployment alone is not sufficient. Railway dashboard environment variables **must be configured** to enable the tools.

## Troubleshooting

### If tools still show as disabled:

1. **Verify Railway deployment completed**:
   ```bash
   railway logs
   # Look for: "Server started successfully"
   ```

2. **Check environment variable loading**:
   ```bash
   railway logs | grep "GRAPHRAG"
   # Should show: GRAPHRAG_ENABLED=true
   ```

3. **Verify feature flag logic**:
   ```python
   # In mcp_integration.py load_feature_flags()
   # Priority: env vars → file → defaults
   if os.getenv("GRAPHRAG_ENABLED") is not None:
       return env vars  # ← This should execute
   ```

### Common Issues

**Issue**: "Feature flags still show false after deployment"
**Solution**: Railway dashboard variables override `.env.production`. Set in dashboard.

**Issue**: "Server not restarting after variable changes"
**Solution**: Click **Deploy** button in Railway dashboard to trigger restart.

**Issue**: "Environment variables not taking effect"
**Solution**: Check variable names are exact (case-sensitive, no quotes).

## References

- **Railway Documentation**: <https://docs.railway.app/guides/variables>
- **Code Implementation**: `/llm/mcp/connectors/mcp-claude-connector/neo4j-mcp-railway-repo/mcp_integration.py`
- **Environment File**: `/llm/mcp/connectors/mcp-claude-connector/neo4j-mcp-railway-repo/.env.production`
- **GraphRAG Infrastructure**: `/llm/memory/graphRAG/README.md`

---

**Action Required**: Julian needs to set these 3 environment variables in Railway dashboard to enable GraphRAG Phase 3 tools.

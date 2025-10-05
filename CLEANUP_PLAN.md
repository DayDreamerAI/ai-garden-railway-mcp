# Repository Cleanup Plan - neo4j-mcp-railway-repo

**Date:** October 5, 2025
**Issue:** Directory contains deprecated files from ai-garden-railway-mcp repo migration

---

## Current Situation

### Two Repositories
1. **Production Railway Repo:** https://github.com/DayDreamerAI/ai-garden-railway-mcp
   - Connected to Railway deployment
   - Currently serving: minimal_sse_server.py (1 tool)

2. **Main Daydreamer Repo:** `/Users/daydreamer/Documents/VibeProjects/daydreamer-mcp`
   - Contains copied files from Railway repo
   - NEW Tier 1 implementation (not deployed yet)
   - Many deprecated files

### Problem
- Files copied from Railway repo but not cleaned up
- Deployment disconnected (Railway watches other repo)
- Multiple deprecated servers, scripts, and docs
- Confusing file structure

---

## File Classification

### ✅ KEEP - Active Production Files (11 files)

**Core Servers:**
- `mcp-claude-connector-memory-server.py` - NEW Tier 1 server (530 lines) ✨
- `minimal_sse_server.py` - Current production (11KB)
- `daydreamer_mcp_memory_server.py` - Full server reference (74KB)

**Supporting Code:**
- `mcp_server.py` - MCP protocol implementation (21KB)
- `conversational_memory_search.py` - Memory search tool (27KB)
- `jina_v3_optimized_embedder.py` - Embeddings (19KB)
- `v6_mcp_bridge.py` - V6 integration (29KB)

**Testing & Deployment:**
- `test_railway_memory_server.py` - NEW test suite (390 lines) ✨
- `deploy_autonomous.sh` - NEW deployment script (159 lines) ✨

**Configuration:**
- `railway.toml` - Railway config ✨
- `requirements.txt` - Python deps

### 📁 ARCHIVE - Old Implementations (15 files → archive/)

**Deprecated Servers:**
- `app.py` (343B) - Old entry point
- `index.py` (340B) - Old entry point
- `server_enhanced.py` (383B) - Old entry point
- `debug_server.py` (2.4KB) - Debug tool
- `enhanced_health_server.py` (12KB) - Old health server
- `simple_health_server.py` (3.1KB) - Old health server
- `health_check.py` (702B) - Old health check
- `flask_api.py` (6.4KB) - Old Flask attempt
- `rest_api_server.py` (13KB) - Old REST API
- `simple_api_server.py` (8.1KB) - Old simple API
- `minimal_test_server.py` (8.6KB) - Old test server

**Deprecated Wrappers:**
- `mcp_http_wrapper.py` (8.0KB) - Old HTTP wrapper
- `mcp_v5_http_wrapper.py` (8.1KB) - V5 wrapper
- `logging_config.py` (8.2KB) - Old logging setup

**Duplicate Large Files:**
- `mcp_neo4j_semantic_server_with_consolidation_railway.py` (87KB) - Duplicate
- `mcp_neo4j_semantic_server_with_consolidation.py` (87KB) - Duplicate

### 📁 ARCHIVE - Old Scripts (13 files → archive/scripts/)

**Deprecated Deployment:**
- `deploy.sh` (7.3KB) - Old deploy
- `deploy_railway_api.sh` (4.9KB) - Old API deploy
- `quick_deploy_railway.sh` (2.5KB) - Old quick deploy
- `setup_github.sh` (7.0KB) - Old GitHub setup

**Old Validation:**
- `validate_deployment.sh` (8.4KB)
- `validate_env.sh` (7.6KB)
- `check_env.sh` (781B)
- `smoke.sh` (284B)
- `test_live_mcp.sh` (1.1KB)
- `test_production.sh` (723B)

**Old Testing:**
- `test_env.py` (1.3KB)
- `test_neo4j_connection.py` (1.7KB)
- `test_mcp_server.py` (3.2KB)

**Old Data Tools:**
- `populate_auradb.py` (6.3KB) - One-time seeding
- `seed_auradb.py` (5.1KB) - One-time seeding
- `security_middleware.py` (18KB) - Old security
- `simple_diagnostic.py` (6.2KB) - Old diagnostic

### 📄 CONSOLIDATE - Documentation (11 files → 3 files)

**Current Docs (11 files):**
1. README.md (8.9KB) - Main docs ✅ KEEP
2. CUSTOM_CONNECTOR_SETUP.md (7.8KB) - User guide ✅ KEEP
3. DEPLOYMENT_STATUS.md (9.3KB) - NEW status ✅ KEEP
4. AI_GARDEN_DEPLOYMENT_GUIDE.md (11KB)
5. DEPLOYMENT_GUIDE.md (9.1KB)
6. DEPLOYMENT_INSTRUCTIONS.md (1.6KB)
7. DEPLOYMENT_READINESS_REPORT.md (9.3KB)
8. ENVIRONMENT_GUIDE.md (7.6KB)
9. MCP_SERVER_README.md (3.0KB)
10. PHASE_4_DEPLOYMENT_STEPS.md (4.2KB)
11. CUSTOM_CONNECTOR_JOURNEY.md (11KB)
12. ORGANIZATION_PLAN.md (7.2KB)
13. ARCHITECTURE.md (26KB) - ✅ KEEP (good reference)

**Consolidation Plan:**
- Keep: README.md, CUSTOM_CONNECTOR_SETUP.md, ARCHITECTURE.md, DEPLOYMENT_STATUS.md
- Archive rest → `archive/old_docs/`

### 🗑️ DELETE - Environment Files (keep .env.template only)

Check which .env files are actually needed:
- `.env.template` - ✅ KEEP
- `.env`, `.env.development`, `.env.production`, `.env.staging` - Archive (may contain secrets)

---

## Proposed Structure

```
neo4j-mcp-railway-repo/
├── README.md                              # Main documentation
├── ARCHITECTURE.md                        # System architecture
├── CUSTOM_CONNECTOR_SETUP.md              # User setup guide
├── DEPLOYMENT_STATUS.md                   # Current deployment status
│
├── mcp-claude-connector-memory-server.py  # Tier 1 server (NEW)
├── minimal_sse_server.py                  # Production fallback
├── daydreamer_mcp_memory_server.py        # Full server reference
│
├── mcp_server.py                          # MCP protocol core
├── conversational_memory_search.py        # Memory search
├── jina_v3_optimized_embedder.py          # Embeddings
├── v6_mcp_bridge.py                       # V6 integration
│
├── test_railway_memory_server.py          # Test suite (NEW)
├── deploy_autonomous.sh                   # Deployment (NEW)
│
├── railway.toml                           # Railway config
├── requirements.txt                       # Dependencies
├── .env.template                          # Env template
│
└── archive/                               # Deprecated files
    ├── old_servers/                       # 15 old implementations
    ├── old_scripts/                       # 13 old scripts
    └── old_docs/                          # 9 old documentation files
```

---

## Cleanup Commands

### Step 1: Create Archive Directory
```bash
mkdir -p archive/{old_servers,old_scripts,old_docs}
```

### Step 2: Archive Old Servers
```bash
mv app.py index.py server_enhanced.py debug_server.py archive/old_servers/
mv enhanced_health_server.py simple_health_server.py health_check.py archive/old_servers/
mv flask_api.py rest_api_server.py simple_api_server.py archive/old_servers/
mv minimal_test_server.py mcp_http_wrapper.py mcp_v5_http_wrapper.py archive/old_servers/
mv logging_config.py archive/old_servers/
mv mcp_neo4j_semantic_server_with_consolidation*.py archive/old_servers/
```

### Step 3: Archive Old Scripts
```bash
mv deploy.sh deploy_railway_api.sh quick_deploy_railway.sh setup_github.sh archive/old_scripts/
mv validate_deployment.sh validate_env.sh check_env.sh smoke.sh archive/old_scripts/
mv test_live_mcp.sh test_production.sh test_env.py archive/old_scripts/
mv test_neo4j_connection.py test_mcp_server.py archive/old_scripts/
mv populate_auradb.py seed_auradb.py security_middleware.py archive/old_scripts/
mv simple_diagnostic.py archive/old_scripts/
```

### Step 4: Archive Old Docs
```bash
mv AI_GARDEN_DEPLOYMENT_GUIDE.md DEPLOYMENT_GUIDE.md archive/old_docs/
mv DEPLOYMENT_INSTRUCTIONS.md DEPLOYMENT_READINESS_REPORT.md archive/old_docs/
mv ENVIRONMENT_GUIDE.md MCP_SERVER_README.md archive/old_docs/
mv PHASE_4_DEPLOYMENT_STEPS.md CUSTOM_CONNECTOR_JOURNEY.md archive/old_docs/
mv ORGANIZATION_PLAN.md archive/old_docs/
```

### Step 5: Archive Environment Files
```bash
mv .env* archive/ 2>/dev/null || true
git checkout .env.template  # Restore template
```

### Step 6: Create Archive README
```bash
cat > archive/README.md << 'EOF'
# Archived Files

This directory contains deprecated files from the ai-garden-railway-mcp migration.

## Directories
- `old_servers/` - 15 deprecated server implementations
- `old_scripts/` - 13 old deployment/test scripts
- `old_docs/` - 9 old documentation files

## Archived Date
October 5, 2025

## Reason
Repository cleanup after migration from separate Railway repo.
Files kept for reference but not actively maintained.
EOF
```

---

## Deployment Strategy

### Current State
- **Production Railway:** Connected to https://github.com/DayDreamerAI/ai-garden-railway-mcp
- **New Implementation:** In daydreamer-mcp repo (not connected to Railway)

### Options

#### Option A: Deploy via Original Railway Repo (Fastest)
1. Clone ai-garden-railway-mcp repo
2. Copy NEW files: mcp-claude-connector-memory-server.py, test suite, deploy script
3. Update railway.toml
4. Push to trigger deployment

**Pros:** Immediate deployment, existing Railway connection
**Cons:** Maintaining two repos, potential drift

#### Option B: Reconnect Railway to daydreamer-mcp Repo
1. Railway Dashboard → Project Settings
2. Change GitHub repo to: DayDreamerAI/daydreamer-mcp
3. Set deployment path: llm/mcp/connectors/mcp-claude-connector/neo4j-mcp-railway-repo
4. Push to main branch triggers deployment

**Pros:** Single source of truth, proper integration
**Cons:** Requires Railway dashboard access, deployment path configuration

#### Option C: Archive Old Repo, Full Migration
1. Clean up this directory (execute cleanup plan)
2. Reconnect Railway to daydreamer-mcp
3. Archive ai-garden-railway-mcp repo
4. Document migration in memory

**Pros:** Clean architecture, no redundancy
**Cons:** More setup work, coordination needed

---

## Recommended Action

**Two-Phase Approach:**

### Phase 1: Quick Deploy (Today)
1. Use Option A - deploy via original Railway repo
2. Test Tier 1 server in production
3. Validate all 7 tests passing

### Phase 2: Repository Consolidation (Next Session)
1. Execute cleanup plan (archive deprecated files)
2. Reconnect Railway to daydreamer-mcp (Option B)
3. Archive old Railway repo
4. Document migration complete

---

## Execute Cleanup (When Ready)

```bash
# Run all cleanup steps
cd /Users/daydreamer/Documents/VibeProjects/daydreamer-mcp/llm/mcp/connectors/mcp-claude-connector/neo4j-mcp-railway-repo

# Create archive structure
mkdir -p archive/{old_servers,old_scripts,old_docs}

# Execute moves (from Step 2-5 above)
# ... all mv commands ...

# Create archive README
cat > archive/README.md << 'EOF'
[Archive README content]
EOF

# Commit cleanup
git add -A
git commit -m "chore: archive deprecated files from Railway repo migration

- Move 15 old server implementations to archive/old_servers/
- Move 13 old scripts to archive/old_scripts/
- Move 9 old docs to archive/old_docs/
- Streamline to 14 active files + CLEANUP_PLAN.md

Structure now focuses on:
- Tier 1 server (NEW)
- Production fallback (minimal_sse_server.py)
- Test suite and deployment automation
- Core MCP protocol and tools

🤖 Generated with Claude Code

Co-Authored-By: Claude <noreply@anthropic.com>"

# Result: Clean, organized repository
```

---

**Status:** Plan created, awaiting execution decision
**Impact:** Reduces directory from 60+ files to 14 active files + organized archive
**Next:** Deploy Tier 1 server via original Railway repo, then execute cleanup

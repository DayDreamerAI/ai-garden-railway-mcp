# Repository Organization Plan

**Created:** October 5, 2025
**Purpose:** Clean up neo4j-mcp-railway-repo directory structure

## Current State Analysis

**Total Files:** 72 files in root directory
**Issues Identified:**
- Multiple backup files (`.bak`, `backup_original/`)
- Duplicate deployment scripts
- Test files mixed with production code
- Multiple environment file variants
- Unclear file ownership and purpose

## Proposed Directory Structure

```
neo4j-mcp-railway-repo/
├── README.md                          # Main documentation
├── CUSTOM_CONNECTOR_SETUP.md          # User-facing setup guide
├── ARCHITECTURE.md                    # System architecture
│
├── deployment/                        # Deployment configurations
│   ├── Dockerfile
│   ├── Procfile
│   ├── railway.toml
│   ├── requirements.txt
│   ├── .env.example
│   ├── .env.template
│   └── deploy.sh
│
├── src/                               # Production source code
│   ├── server/
│   │   ├── mcp_server.py             # Main MCP server
│   │   ├── daydreamer_mcp_memory_server.py
│   │   ├── mcp_http_wrapper.py
│   │   └── minimal_sse_server.py
│   ├── tools/
│   │   ├── conversational_memory_search.py
│   │   ├── jina_v3_optimized_embedder.py
│   │   └── v6_mcp_bridge.py
│   ├── middleware/
│   │   ├── security_middleware.py
│   │   └── logging_config.py
│   └── utils/
│       └── seed_auradb.py
│
├── tests/                             # Test files
│   ├── test_mcp_server.py
│   ├── test_neo4j_connection.py
│   ├── test_env.py
│   └── smoke.sh
│
├── scripts/                           # Deployment and utility scripts
│   ├── deploy_railway_api.sh
│   ├── validate_deployment.sh
│   ├── validate_env.sh
│   ├── check_env.sh
│   └── setup_github.sh
│
├── docs/                              # Documentation
│   ├── CUSTOM_CONNECTOR_JOURNEY.md
│   ├── DEPLOYMENT_GUIDE.md
│   ├── ENVIRONMENT_GUIDE.md
│   └── migration/                     # Migration-specific docs
│       └── auradb-migration-notes.md
│
└── archive/                           # Deprecated/backup files
    ├── backup_original/
    ├── *.bak files
    ├── old deployment scripts
    └── deprecated server implementations
```

## Files to Archive

**Backup Files:**
- `Dockerfile.bak`
- `deploy_railway_api.sh.bak`
- `backup_original/` (entire directory)

**Deprecated/Duplicate Files:**
- `app.py` (duplicate entry point)
- `index.py` (duplicate entry point)
- `debug_server.py` (use test files instead)
- `flask_api.py` (superseded by minimal_sse_server.py)
- `rest_api_server.py` (superseded)
- `simple_api_server.py` (superseded)
- `simple_diagnostic.py` (use tests/)
- `simple_health_server.py` (use enhanced_health_server.py)
- `enhanced_health_server.py` (if not used)
- `server_enhanced.py` (unclear purpose)
- `mcp_neo4j_semantic_server_with_consolidation_railway.py` (superseded)

**Test Files to Move:**
- `test_*.py` → `tests/`
- `test_*.sh` → `tests/`
- `smoke.sh` → `tests/`

**Documentation to Organize:**
- Move deployment guides to `docs/`
- Consolidate redundant guides

**Environment Files:**
- Keep: `.env.example`, `.env.template`
- Archive: `.env.development`, `.env.production`, `.env.staging` (should be in Railway/local only)
- Add to .gitignore: `.env` (actual credentials)

## Active Production Files

**Core Server Implementation:**
- `daydreamer_mcp_memory_server.py` - Main MCP memory server (75KB)
- `mcp_server.py` - MCP protocol implementation
- `minimal_sse_server.py` - SSE transport for Custom Connectors
- `mcp_http_wrapper.py` - HTTP adapter for MCP

**Tools & Utilities:**
- `conversational_memory_search.py` - Natural language memory search
- `jina_v3_optimized_embedder.py` - Embedding generation
- `v6_mcp_bridge.py` - V6 architecture bridge
- `security_middleware.py` - Authentication and rate limiting
- `logging_config.py` - Structured logging

**Deployment:**
- `Procfile` - Railway process definition
- `railway.toml` - Railway configuration
- `requirements.txt` - Python dependencies
- `deploy.sh` - Deployment automation
- `deploy_railway_api.sh` - API deployment
- `validate_deployment.sh` - Post-deployment checks

**Configuration:**
- `.env.example` - Template with placeholders
- `.env.template` - Alternative template
- `mcp_config.json` - MCP configuration

## Migration Strategy

### Phase 1: Create Directory Structure
```bash
mkdir -p src/{server,tools,middleware,utils}
mkdir -p tests
mkdir -p scripts
mkdir -p archive
mkdir -p docs/migration
```

### Phase 2: Move Active Files
```bash
# Server files
mv *_server.py src/server/ (except deprecated)
mv mcp_*.py src/server/

# Tools
mv conversational_memory_search.py src/tools/
mv jina_v3_optimized_embedder.py src/tools/
mv v6_mcp_bridge.py src/tools/
mv seed_auradb.py src/utils/

# Middleware
mv security_middleware.py src/middleware/
mv logging_config.py src/middleware/

# Tests
mv test_*.py tests/
mv *_test.sh tests/
mv smoke.sh tests/

# Scripts
mv deploy*.sh scripts/
mv validate*.sh scripts/
mv check_env.sh scripts/
mv setup_github.sh scripts/
```

### Phase 3: Archive Old Files
```bash
# Backup files
mv *.bak archive/
mv backup_original/ archive/

# Deprecated implementations
mv app.py archive/
mv index.py archive/
mv debug_server.py archive/
mv flask_api.py archive/
mv rest_api_server.py archive/
mv simple_*.py archive/
mv enhanced_health_server.py archive/
mv mcp_neo4j_semantic_server_with_consolidation_railway.py archive/

# Environment files
mv .env.development archive/
mv .env.production archive/
mv .env.staging archive/
```

### Phase 4: Update Documentation
- Update README.md with new structure
- Update import paths in code
- Update deployment scripts with new paths
- Update .gitignore for new structure

### Phase 5: Update Railway Configuration
- Update Procfile with new server path
- Test deployment with new structure
- Validate all endpoints still work

## Benefits of Organization

1. **Clarity:** Clear separation of concerns (server/tools/tests/docs)
2. **Maintainability:** Easier to find and update files
3. **Safety:** Backups preserved but out of the way
4. **Professionalism:** Standard Python project structure
5. **Scalability:** Room to grow without clutter

## Risks and Mitigation

**Risk:** Breaking Railway deployment
**Mitigation:** Test locally first, update Procfile carefully

**Risk:** Import path changes break code
**Mitigation:** Update all imports, test thoroughly before deploy

**Risk:** Losing important backup files
**Mitigation:** Move to archive/ not delete, can restore if needed

## Timeline

- **Phase 1-2:** 10 minutes (create directories, move files)
- **Phase 3:** 5 minutes (archive old files)
- **Phase 4:** 15 minutes (update documentation)
- **Phase 5:** 10 minutes (test deployment)
- **Total:** ~40 minutes

## Approval Required

This organization plan requires approval before execution to avoid disrupting production deployment.

**Status:** ⏸️ PENDING APPROVAL

---

**Next Action:** Review with Julian, execute if approved

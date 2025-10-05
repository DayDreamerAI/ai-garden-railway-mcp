# Archived Files

This directory contains deprecated files from the ai-garden-railway-mcp migration.

## Directories

- `old_servers/` - 15 deprecated server implementations
- `old_scripts/` - 17 old deployment/test scripts
- `old_docs/` - 9 old documentation files

## Archived Date
October 5, 2025

## Reason
Repository cleanup after migration from separate Railway repo.
Files kept for reference but not actively maintained.

## What Was Removed

### Old Servers (15 files)
- Multiple entry points: app.py, index.py, server_enhanced.py
- Debug/test servers: debug_server.py, minimal_test_server.py
- Health check variants: enhanced_health_server.py, simple_health_server.py, health_check.py
- API implementations: flask_api.py, rest_api_server.py, simple_api_server.py
- HTTP wrappers: mcp_http_wrapper.py, mcp_v5_http_wrapper.py
- Duplicate large files: mcp_neo4j_semantic_server_with_consolidation*.py (2x 87KB)
- Support: logging_config.py

### Old Scripts (17 files)
- Deployment: deploy.sh, deploy_railway_api.sh, quick_deploy_railway.sh, setup_github.sh
- Validation: validate_deployment.sh, validate_env.sh, check_env.sh, smoke.sh
- Testing: test_live_mcp.sh, test_production.sh, test_env.py, test_neo4j_connection.py, test_mcp_server.py
- Data tools: populate_auradb.py, seed_auradb.py
- Security: security_middleware.py
- Diagnostic: simple_diagnostic.py

### Old Documentation (9 files)
- AI_GARDEN_DEPLOYMENT_GUIDE.md
- DEPLOYMENT_GUIDE.md
- DEPLOYMENT_INSTRUCTIONS.md
- DEPLOYMENT_READINESS_REPORT.md
- ENVIRONMENT_GUIDE.md
- MCP_SERVER_README.md
- PHASE_4_DEPLOYMENT_STEPS.md
- CUSTOM_CONNECTOR_JOURNEY.md
- ORGANIZATION_PLAN.md

## Active Files (14 + docs)

### Core Servers (3)
- mcp-claude-connector-memory-server.py - NEW Tier 1 server
- minimal_sse_server.py - Production fallback
- daydreamer_mcp_memory_server.py - Full server reference

### Supporting Code (4)
- mcp_server.py - MCP protocol
- conversational_memory_search.py - Memory search
- jina_v3_optimized_embedder.py - Embeddings
- v6_mcp_bridge.py - V6 integration

### Testing & Deployment (3)
- test_railway_memory_server.py - Test suite
- deploy_autonomous.sh - Railway deployment
- deploy_to_railway.sh - Sync script (NEW)

### Configuration (4)
- railway.toml
- requirements.txt
- .env.template

### Documentation (5)
- README.md
- ARCHITECTURE.md
- CUSTOM_CONNECTOR_SETUP.md
- DEPLOYMENT_STATUS.md
- CLEANUP_PLAN.md

## Recovery

If you need to restore any archived file:
```bash
cp archive/[old_servers|old_scripts|old_docs]/[filename] ./
```

# Railway MCP Archive

**Archived**: October 19, 2025

This directory contains deprecated files from Railway MCP production deployment history.

## Archive Structure

### old-servers/
**12 deprecated server implementations**

Replaced by: `mcp-claude-connector-memory-server.py` (production MCP server)

Files:
- `app.py` - Early Flask API experiment
- `debug_server.py` - Debug version
- `enhanced_health_server.py` - Health check server variant
- `flask_api.py` - Flask API variant
- `index.py` - Index server attempt
- `mcp_neo4j_semantic_server_with_consolidation_railway.py` - Early MCP server
- `mcp_server.py` - Generic MCP server
- `rest_api_server.py` - REST API variant
- `server_enhanced.py` - Enhanced server variant
- `simple_api_server.py` - Simplified API server
- `simple_diagnostic.py` - Diagnostic server
- `simple_health_server.py` - Simple health check

### tests/
**5 test and validation scripts**

Files:
- `health_check.py` - Health check validation
- `populate_auradb.py` - Database population script
- `test_env.py` - Environment validation
- `test_mcp_server.py` - MCP server tests
- `test_neo4j_connection.py` - Neo4j connection tests

### deployment/
**11 deployment and validation scripts**

Replaced by: Railway auto-deploy from GitHub

Files:
- `deploy.sh` - Manual deployment script
- `deploy_railway_api.sh` - API deployment variant
- `quick_deploy_railway.sh` - Quick deploy script
- `setup_github.sh` - GitHub setup
- `smoke.sh` - Smoke tests
- `test_live_mcp.sh` - Live MCP testing
- `test_production.sh` - Production validation
- `validate_deployment.sh` - Deployment validation
- `validate_env.sh` - Environment validation
- `Procfile` - Process configuration
- `Procfile.test` - Test process configuration

### config/
**8 configuration files**

Replaced by: Railway environment variables + `railway.toml`

Files:
- `.dockerignore` - Docker ignore patterns
- `.env.development` - Development environment
- `.env.example` - Environment template
- `Dockerfile.bak` - Backup Dockerfile
- `logging_config.py` - Logging configuration
- `mcp_config.json` - MCP configuration
- `security_middleware.py` - Security middleware
- `ai-garden-deployment-manifest.json` - Deployment manifest

### docs/
**11 documentation files**

Replaced by: Root `README.md` + `CHANGELOG.md` (consolidated documentation)

Files:
- `AI_GARDEN_DEPLOYMENT_GUIDE.md` - Deployment guide
- `ARCHITECTURE.md` - Architecture documentation
- `DEPLOYMENT_INSTRUCTIONS.md` - Deployment instructions
- `DEPLOYMENT_READINESS_REPORT.md` - Readiness report
- `ENVIRONMENT_GUIDE.md` - Environment guide
- `MCP_SERVER_README.md` - MCP server README
- `PHASE_4_DEPLOYMENT_STEPS.md` - Phase 4 deployment
- `RAILWAY_V6_COMPLIANCE_UPDATE_PLAN.md` - V6 compliance plan
- `RAILWAY_V6_MIGRATION_PLAN_V2.md` - V6 migration plan v2
- `RAILWAY_MEMORY_FIX_OCT18.md` - Memory fix documentation (Oct 18)
- `RAILWAY_V6_VALIDATION_QUERIES.md` - V6 validation queries

### schema/
**1 deprecated schema file**

Replaced by: `property_names.py` (synced from `/llm/memory/schemas/`)

Files:
- `v6_schema.py` - Old V6 schema definitions

## Production Files (Remain in Root)

**13 active production files:**

### Core MCP Server
- `mcp-claude-connector-memory-server.py` - Main MCP server (SSE transport)
- `v6_mcp_bridge.py` - V6 architecture bridge
- `schema_enforcement.py` - Schema validation
- `property_names.py` - Canonical schema (synced from `/llm/memory/schemas/`)

### Embeddings & Classification
- `jina_v3_optimized_embedder.py` - JinaV3 embedding generation
- `semantic_classifier.py` - Theme classification (9 themes)

### GraphRAG Tools
- `global_search.py` - GraphRAG global search
- `local_search.py` - GraphRAG local search
- `mcp_integration.py` - GraphRAG MCP integration

### Configuration & Documentation
- `railway.toml` - Railway deployment config
- `requirements.txt` - Python dependencies
- `README.md` - Production status
- `CHANGELOG.md` - Version history

## Rationale

**Why Archive?**
1. **Deployment Evolution**: Multiple server implementations tried before settling on production SSE transport
2. **Configuration Consolidation**: Railway environment variables replaced multiple config files
3. **Documentation Consolidation**: Root README.md + CHANGELOG.md replaced scattered docs
4. **Schema Consolidation**: Single source of truth at `/llm/memory/schemas/property_names.py`

**Why Keep History?**
- Preserves deployment evolution for future reference
- Maintains context for architectural decisions
- Enables rollback if needed (though unlikely)

---

**Last Updated**: October 19, 2025
**Archive Reason**: Railway v6.3.3 repository cleanup
**Production Version**: v6.3.3 (True lazy loading, V6 compliance)

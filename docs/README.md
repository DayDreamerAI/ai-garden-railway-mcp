# Railway MCP Server Documentation

Complete technical documentation for the Daydreamer Railway MCP server deployment.

## 📁 Directory Structure

```
docs/
├── README.md                          # This file - documentation index
├── audits/                            # V6 compliance audits
│   ├── README.md                      # Audit summary
│   ├── AUDIT_RESPONSE_OCT19.md        # Latest audit response (95% compliance)
│   ├── AUDIT_FIX_COMPLETE.md          # Fix completion report
│   └── AUDIT_FIX_PLAN.md              # Original fix plan (resolved)
├── deployments/                       # Deployment guides and history
├── EMBEDDING_DISCREPANCY_OCT14.md     # JinaV3 dimension investigation
├── RAILWAY_CPU_FIX_OCT15.md           # Railway CPU optimization
└── RAILWAY_MOBILE_TESTING_OCT14.md    # Mobile testing validation
```

## 🎯 Quick Navigation

### For Developers

**Setting Up**:
- Main [README.md](../README.md) - Quick start and deployment
- [deployments/](deployments/) - Deployment configurations and history

**Current Status**:
- [audits/](audits/) - V6 compliance status (19/20 - 95%)
- [CHANGELOG.md](../CHANGELOG.md) - Version history (latest: v6.3.6)

### For Auditors

**Compliance Documentation**:
- [audits/AUDIT_RESPONSE_OCT19.md](audits/AUDIT_RESPONSE_OCT19.md) - Latest audit findings
- [audits/AUDIT_FIX_COMPLETE.md](audits/AUDIT_FIX_COMPLETE.md) - Fix validation
- V6 Standards: `/llm/memory/perennial/docs/standards/V6_COMPLIANCE_AUDIT_STANDARDS.md`

**System Validation**:
- V6 Core: 11/11 (100%) ✅
- GraphRAG: 5/5 (100%) ✅  
- Schema: 3/3 (100%) ✅
- Code Path: 0/4 (pending)

### For Troubleshooting

**Common Issues**:
- [RAILWAY_CPU_FIX_OCT15.md](RAILWAY_CPU_FIX_OCT15.md) - Memory/CPU optimization
- [EMBEDDING_DISCREPANCY_OCT14.md](EMBEDDING_DISCREPANCY_OCT14.md) - Embedding dimension validation
- [RAILWAY_MOBILE_TESTING_OCT14.md](RAILWAY_MOBILE_TESTING_OCT14.md) - Mobile connectivity

**Debug Resources**:
- Railway logs: `railway logs`
- Health check: `curl https://ai-garden-railway-mcp-production.up.railway.app/health`
- Memory stats: Use `memory_stats` MCP tool

## 📊 System Status (October 19, 2025)

**Production Metrics**:
- Observations: 22,797 (99.996% with embeddings)
- SemanticEntity nodes: 1,344 (99.7% in communities)
- Communities: 241 (100% with embeddings)
- Temporal coverage: 100% (Day→Month→Year)

**V6 Compliance**: 19/20 (95%) ✅ PRODUCTION READY

**Outstanding**:
- 1 observation missing embedding (0.004%)
- Code path validation pending (requires repo access)
- 3,428 null source orphans (data quality opportunity)

## 🔄 Recent Major Updates

### v6.3.6 (October 19, 2025) - Audit Fix Completion
- ✅ V5 chunk migration complete (3,428 nodes)
- ✅ Observation reclassification (9,343 nodes)
- ✅ Community coverage clarified (99.7%)
- ✅ Minor gaps fixed (temporal binding)

### v6.3.4-6.3.5 (October 19, 2025) - Critical Fixes
- ✅ MCP protocol compliance (4 missing handlers)
- ✅ GraphRAG global search embedder isolation
- ✅ True lazy loading (startup memory <1GB)
- ✅ SSE connection management (5→10 limit)

### v6.3.2 (October 18, 2025) - V6 Compliance
- ✅ Semantic theme classifier integration
- ✅ V5 property cleanup (100% V6 schema)
- ✅ CPU-only Railway optimization

## 📖 Related Documentation

**Main Repository**:
- `/llm/memory/perennial/` - V6 conversation processing
- `/llm/memory/schemas/` - Canonical schemas
- `/llm/memory/graphRAG/` - GraphRAG implementation

**Standards**:
- V6 Compliance: `/llm/memory/perennial/docs/standards/V6_COMPLIANCE_AUDIT_STANDARDS.md`
- Schema Enforcement: `/llm/mcp/servers/daydreamer-memory-mcp/SCHEMA_ENFORCEMENT_README.md`

## 🤝 Contributing

When adding documentation:
1. Place in appropriate subdirectory (audits/, deployments/, etc.)
2. Update relevant README.md files
3. Link from main README.md if user-facing
4. Follow existing naming conventions (TOPIC_DATE.md)

## 📞 Support

For issues or questions:
- Railway logs: `railway logs --tail 100`
- MCP server status: `memory_stats` tool
- GitHub Issues: [daydreamer-mcp repository]

---

**Last Updated**: October 19, 2025  
**Current Version**: v6.3.6  
**Status**: Production Ready (95% V6 compliant)

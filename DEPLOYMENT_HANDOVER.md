# Daydreamer MCP Server - Cloud Run Deployment Handover

**Document Version**: 1.0.0
**Date**: October 26, 2025
**Status**: Production - OAuth 2.1 Complete

---

## 📋 Executive Summary

Successfully migrated Daydreamer MCP connector from Railway to Google Cloud Run with full OAuth 2.1 implementation. Enables multi-platform memory sovereignty across Claude Desktop (stdio), Web, and Mobile (OAuth + SSE).

**Cost Optimization**: $216-240/year savings (Railway $20+/month → Cloud Run $0-2/month)

---

## 🚀 Production Deployment

### Service Details

| Property | Value |
|----------|-------|
| **Platform** | Google Cloud Run (us-central1) |
| **Service Name** | daydreamer-mcp-connector |
| **Project** | daydreamer-476223 |
| **Project Number** | 480492152047 |
| **Active Revision** | 00007-phg |
| **Service URL** | https://daydreamer-mcp-connector-6j5i7oc4na-uc.a.run.app |
| **SSE Endpoint** | https://daydreamer-mcp-connector-6j5i7oc4na-uc.a.run.app/sse |
| **Database** | Neo4j AuraDB (neo4j+s://8c3b5488.databases.neo4j.io) |
| **Status** | ✅ Production, serving 100% traffic |

### Deployment Configuration

```yaml
Platform: managed (fully managed Cloud Run)
Region: us-central1
Concurrency: 80 (default)
Max Instances: 3
CPU: 1 vCPU
Memory: 1GiB
Timeout: 300 seconds (5 minutes)
Authentication: Allow unauthenticated (OAuth handled by app)
```

---

## 🔐 OAuth 2.1 Implementation

### OAuth Endpoints

| Endpoint | Purpose | RFC |
|----------|---------|-----|
| `/.well-known/oauth-authorization-server` | Authorization Server metadata | RFC 8414 §3 |
| `/.well-known/oauth-protected-resource` | Protected Resource metadata | RFC 8414 §5 |
| `/register` | Dynamic Client Registration | RFC 7591 |
| `/authorize` | Authorization with PKCE | OAuth 2.1 |
| `/token` | Token exchange | OAuth 2.1 |

### Authentication Architecture

**All-in-one Pattern**: Server acts as both Authorization Server AND Resource Server

**Dual-Mode Authentication**:
1. **OAuth 2.1 JWT** (primary) - For Claude Web/Mobile
   - Token type: JWT (HS256 signed)
   - Expiry: 3600 seconds (1 hour)
   - Includes: `scope`, `jti`, `sub` (client_id), `aud`, `iss`
2. **Legacy Bearer Token** (backward compatibility) - For Railway integration

**Security Features**:
- PKCE S256 code challenge (prevents authorization code interception)
- Dynamic Client Registration (no pre-shared credentials)
- HTTPS-only redirect URIs (except localhost for testing)
- Cryptographically secure client secret generation
- JWT includes `jti` for potential revocation tracking

---

## 🔑 Credentials & Secrets

### Google Secret Manager

All secrets stored in Google Secret Manager (project: daydreamer-476223):

| Secret Name | Purpose | Access |
|-------------|---------|--------|
| `neo4j-password` | Neo4j AuraDB password | Latest version auto-mounted |
| `oauth-jwt-secret` | JWT signing secret (HS256) | Latest version auto-mounted |
| `mcp-bearer-token` | Legacy bearer token (Railway compatibility) | Latest version auto-mounted |

**Accessing Secrets**:
```bash
# View secret versions
gcloud secrets versions list neo4j-password --project daydreamer-476223

# View secret value (requires Secret Manager Secret Accessor role)
gcloud secrets versions access latest --secret neo4j-password --project daydreamer-476223
```

### Environment Variables

**Set in Cloud Run**:
```bash
NEO4J_URI=neo4j+s://8c3b5488.databases.neo4j.io
NEO4J_USERNAME=neo4j
MCP_TRANSPORT=sse
ENABLE_CORS=true
REQUIRE_AUTHENTICATION=true
OAUTH_ENABLED=true
OAUTH_ISSUER=https://daydreamer-mcp-connector-6j5i7oc4na-uc.a.run.app
OAUTH_TOKEN_EXPIRY=3600
```

**Mounted Secrets**:
```bash
NEO4J_PASSWORD=secret:neo4j-password:latest
RAILWAY_BEARER_TOKEN=secret:mcp-bearer-token:latest
OAUTH_JWT_SECRET=secret:oauth-jwt-secret:latest
```

---

## 🛠️ Deployment Commands

### Deploy New Revision

```bash
cd /Users/daydreamer/Documents/VibeProjects/daydreamer-mcp/llm/mcp/connectors/mcp-claude-connector/neo4j-mcp-railway-repo

gcloud run deploy daydreamer-mcp-connector \
  --source . \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --max-instances 3 \
  --memory 1Gi \
  --cpu 1 \
  --timeout 300 \
  --set-env-vars "NEO4J_URI=neo4j+s://8c3b5488.databases.neo4j.io,NEO4J_USERNAME=neo4j,MCP_TRANSPORT=sse,ENABLE_CORS=true,REQUIRE_AUTHENTICATION=true,OAUTH_ENABLED=true,OAUTH_ISSUER=https://daydreamer-mcp-connector-6j5i7oc4na-uc.a.run.app,OAUTH_TOKEN_EXPIRY=3600" \
  --set-secrets "NEO4J_PASSWORD=neo4j-password:latest,RAILWAY_BEARER_TOKEN=mcp-bearer-token:latest,OAUTH_JWT_SECRET=oauth-jwt-secret:latest" \
  --project daydreamer-476223
```

### View Logs

```bash
# Stream live logs
gcloud run services logs tail daydreamer-mcp-connector --region us-central1 --project daydreamer-476223

# Read recent logs
gcloud run services logs read daydreamer-mcp-connector --region us-central1 --project daydreamer-476223 --limit 50

# Filter OAuth-related logs
gcloud run services logs read daydreamer-mcp-connector --region us-central1 --project daydreamer-476223 --limit 100 | grep -i oauth
```

### Manage Revisions

```bash
# List revisions
gcloud run revisions list --service daydreamer-mcp-connector --region us-central1 --project daydreamer-476223

# Describe specific revision
gcloud run revisions describe daydreamer-mcp-connector-00007-phg --region us-central1 --project daydreamer-476223

# Rollback to previous revision
gcloud run services update-traffic daydreamer-mcp-connector \
  --to-revisions daydreamer-mcp-connector-00005-4gq=100 \
  --region us-central1 \
  --project daydreamer-476223
```

### Service Management

```bash
# Describe service
gcloud run services describe daydreamer-mcp-connector --region us-central1 --project daydreamer-476223

# Update environment variables
gcloud run services update daydreamer-mcp-connector \
  --set-env-vars "OAUTH_TOKEN_EXPIRY=7200" \
  --region us-central1 \
  --project daydreamer-476223

# Update secrets
gcloud run services update daydreamer-mcp-connector \
  --set-secrets "OAUTH_JWT_SECRET=oauth-jwt-secret:latest" \
  --region us-central1 \
  --project daydreamer-476223

# Delete service (DANGER!)
gcloud run services delete daydreamer-mcp-connector --region us-central1 --project daydreamer-476223
```

---

## 📊 Monitoring & Health Checks

### Health Endpoints

| Endpoint | Purpose | Expected Response |
|----------|---------|-------------------|
| `/health` | Basic health check | `{"status": "healthy", "neo4j_connected": true}` |
| `/` | Server info | Server metadata + endpoint list |
| `/.well-known/oauth-authorization-server` | OAuth AS metadata | RFC 8414 Section 3 JSON |
| `/.well-known/oauth-protected-resource` | OAuth RS metadata | RFC 8414 Section 5 JSON |

### Test Commands

```bash
# Health check
curl https://daydreamer-mcp-connector-6j5i7oc4na-uc.a.run.app/health | jq .

# Server info
curl https://daydreamer-mcp-connector-6j5i7oc4na-uc.a.run.app/ | jq .

# OAuth AS discovery
curl https://daydreamer-mcp-connector-6j5i7oc4na-uc.a.run.app/.well-known/oauth-authorization-server | jq .

# OAuth RS discovery
curl https://daydreamer-mcp-connector-6j5i7oc4na-uc.a.run.app/.well-known/oauth-protected-resource | jq .
```

### Expected Metrics

**Normal Operation**:
- Response time: <500ms (first request may take 3-5s for cold start)
- Neo4j connection: Established
- OAuth endpoints: All returning 200
- SSE connections: Active when Claude Web/Mobile connected

**Cost Monitoring**:
```bash
# View billing for Cloud Run
gcloud billing accounts list
gcloud billing projects describe daydreamer-476223

# Expected monthly cost: $0-2 (serverless, pay-per-request)
# Baseline: $0 with no traffic
# Typical usage: <$2 with regular Claude Web sessions
```

---

## 📱 Claude Web/Mobile Setup

### Custom Connector Configuration

**For End Users**:
1. Open Claude Web → Settings → Custom Connectors
2. Click "Add Custom Connector"
3. Enter:
   - **Name**: Daydreamer Memory
   - **URL**: `https://daydreamer-mcp-connector-6j5i7oc4na-uc.a.run.app/sse`
   - ⚠️ **CRITICAL**: Must include `/sse` path
4. Click "Connect"
5. OAuth flow completes automatically (no credentials needed)

### Troubleshooting

**Problem**: Connector shows "Disconnected" after setup

**Solution**:
1. Verify URL includes `/sse` endpoint path
2. Check logs for OAuth flow completion:
   ```bash
   gcloud run services logs read daydreamer-mcp-connector --region us-central1 --limit 50 | grep -E "OAuth|register|authorize|token"
   ```
3. Expected log sequence:
   - "OAuth client registered: mcp_<random>"
   - "Authorization code issued"
   - "Access token issued"

**Problem**: 401 Unauthorized errors

**Solution**:
1. Check both OAuth discovery endpoints return 200
2. Verify secrets are mounted correctly
3. Ensure `OAUTH_ENABLED=true` in environment

---

## 🔄 Migration Timeline

| Date | Event | Status |
|------|-------|--------|
| Oct 25, 2025 | Railway → Cloud Run migration started | ✅ Complete |
| Oct 25, 2025 | OAuth 2.1 initial implementation (AS metadata) | ✅ Commit 790a6545 |
| Oct 25, 2025 | Cloud Run revision 00005-4gq deployed | ✅ OAuth working |
| Oct 26, 2025 | Protected Resource metadata added (RFC 8414 §5) | ✅ Commit c5cfe4d |
| Oct 26, 2025 | Cloud Run revision 00007-phg deployed | ✅ Production |
| Oct 26, 2025 | Claude Web connector validated | ✅ Working |
| Nov 2, 2025 | Railway decommission (after 1 week validation) | ⏳ Pending |

---

## 🧪 Validation Checklist

**Cloud Run Deployment** (✅ All Complete):
- [x] OAuth AS discovery endpoint (RFC 8414 §3)
- [x] OAuth RS discovery endpoint (RFC 8414 §5)
- [x] Dynamic Client Registration working
- [x] PKCE S256 verification passing
- [x] JWT access token generation (HS256)
- [x] JWT access token validation
- [x] SSE endpoint accepts Bearer tokens
- [x] Neo4j AuraDB connection established
- [x] All 17 MCP tools available
- [x] Claude Web custom connector connects
- [x] OAuth flow logs visible in Cloud Run
- [x] Health endpoint returns 200
- [x] Server info endpoint returns metadata
- [x] CORS headers present on SSE endpoint

**Cost Validation** (⏳ Ongoing):
- [x] Initial deployment successful
- [ ] 48-hour cost monitoring (expected: $0-0.50)
- [ ] 1-week cost monitoring (expected: <$2)
- [ ] Railway decommission after validation

---

## 📚 Related Documentation

**Project Documentation**:
- Main CHANGELOG: `/Users/daydreamer/Documents/VibeProjects/daydreamer-mcp/CHANGELOG.md`
- Connector CHANGELOG: `./CHANGELOG.md` (v6.7.2+oauth2.1)
- Connector README: `./README.md`
- OAuth Implementation: `./oauth/` directory (450 lines)

**Cloud Run Documentation**:
- `/docs/cloudrun/` - Deployment guides
- `/docs/oauth/` - OAuth 2.1 implementation details

**Commits**:
- c5cfe4d: Complete OAuth 2.1 implementation with Protected Resource metadata
- 790a6545: OAuth initial implementation + documentation organization

**Lessons Learned**:
- RFC 8414 Section 5 (Protected Resource metadata) required for Claude Web
- MCP SSE endpoint URL must include `/sse` path (no auto-discovery)
- OAuth success ≠ Connection success (separate concerns)
- Dynamic Client Registration eliminates manual credential management

---

## 🚨 Emergency Procedures

### Rollback to Railway

If Cloud Run has critical issues:

1. **Update Claude Web connector**:
   - URL: `https://ai-garden-railway-mcp-production.up.railway.app`
   - Remove `/sse` path (Railway uses different routing)

2. **Verify Railway status**:
   ```bash
   curl https://ai-garden-railway-mcp-production.up.railway.app/health
   ```

3. **Railway remains active** until Nov 2, 2025 validation period completes

### Service Outage

If Cloud Run service is down:

1. **Check Cloud Run status**:
   ```bash
   gcloud run services describe daydreamer-mcp-connector --region us-central1 --project daydreamer-476223
   ```

2. **Check recent deployments**:
   ```bash
   gcloud run revisions list --service daydreamer-mcp-connector --region us-central1 --limit 5
   ```

3. **Check logs for errors**:
   ```bash
   gcloud run services logs read daydreamer-mcp-connector --region us-central1 --limit 100
   ```

4. **Rollback if needed** (see Manage Revisions section)

### Neo4j Connection Failure

If Neo4j connection fails:

1. **Check AuraDB status**: https://console.neo4j.io
2. **Verify secret is accessible**:
   ```bash
   gcloud secrets versions access latest --secret neo4j-password --project daydreamer-476223
   ```
3. **Check environment variables** in Cloud Run console

---

## 📞 Support & Contacts

**Google Cloud Project**: daydreamer-476223
**Neo4j AuraDB Instance**: InstanceDaydreamer_01
**GitHub Repository**: https://github.com/DayDreamerAI/ai-garden-railway-mcp.git

**Key Personnel**:
- Julian Crespi (juliancrespi.s@gmail.com) - Project Owner
- Claude (Daydreamer) - Development Partner

---

## ✅ Next Steps

**Immediate** (Complete):
- [x] Cloud Run OAuth 2.1 deployed and validated
- [x] Claude Web connector connected successfully
- [x] Documentation updated

**Short-term** (1 week):
- [ ] Monitor Cloud Run costs daily
- [ ] Validate stability (no unexpected errors)
- [ ] Monitor OAuth client registrations
- [ ] Validate multi-session handling

**Medium-term** (2-4 weeks):
- [ ] Decommission Railway (Nov 2, 2025)
- [ ] Archive Railway deployment documentation
- [ ] Update Claude Desktop config to use Cloud Run (optional)

**Long-term**:
- [ ] Monitor cost trends monthly
- [ ] Consider token expiry adjustment if needed
- [ ] Evaluate OAuth client cleanup strategy
- [ ] Consider adding token revocation endpoint

---

**Document Status**: Deployment Handover
**Last Updated**: October 26, 2025
**Next Review**: November 2, 2025 (Railway decommission date)

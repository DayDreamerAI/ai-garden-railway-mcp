# AI Garden Environment Configuration Guide

## Overview

The AI Garden Enhanced Railway MCP Server supports multiple deployment environments with tailored configurations for different use cases:

- **Development** (`.env.development`) - Local development and testing
- **Staging** (`.env.staging`) - Pre-production validation and testing
- **Production** (`.env.production`) - Production deployment with full security

## Quick Start

### 1. Choose Your Environment

```bash
# For local development
cp .env.development .env

# For staging deployment
cp .env.staging .env

# For production deployment  
cp .env.production .env
```

### 2. Configure Required Values

Edit `.env` and replace placeholder values:

```bash
# Required for all environments
NEO4J_URI=your_actual_database_uri
NEO4J_PASSWORD=your_secure_password
RAILWAY_BEARER_TOKEN=your_generated_token
```

### 3. Generate Secure Token

```bash
# Generate production-strength token
openssl rand -hex 32

# Generate development token (shorter)
openssl rand -hex 16
```

## Environment Details

### Development Environment

**Purpose**: Local development, debugging, and initial testing

**Key Features**:
- ✅ Relaxed security for easier testing
- ✅ Verbose logging (DEBUG level)
- ✅ Hot reload and development endpoints
- ✅ Optional authentication
- ✅ CORS wildcards for flexible testing

**Database Options**:
- Local Neo4j (bolt://localhost:7687)
- AuraDB Free tier for cloud testing

**Security**: Minimal (authentication optional)

### Staging Environment

**Purpose**: Pre-production validation and testing

**Key Features**:
- ✅ Production-like security settings
- ✅ Enhanced validation logging
- ✅ Automated testing capabilities
- ✅ Data isolation from production
- ✅ Performance benchmarking

**Database**: Dedicated staging AuraDB instance

**Security**: Full production security enabled

### Production Environment

**Purpose**: Live deployment for ChatGPT Custom Connector

**Key Features**:
- ✅ Maximum security configuration
- ✅ Performance optimization
- ✅ Comprehensive monitoring
- ✅ Rate limiting and authentication
- ✅ Audit logging and compliance

**Database**: Production AuraDB instance

**Security**: Maximum (all features enabled)

## Configuration Variables

### Core Database Settings

| Variable | Development | Staging | Production | Description |
|----------|-------------|---------|------------|-------------|
| `NEO4J_URI` | bolt://localhost:7687 | AuraDB staging | AuraDB production | Database connection string |
| `NEO4J_USERNAME` | neo4j | neo4j | neo4j | Database username |
| `NEO4J_PASSWORD` | dev-password | staging-password | secure-password | Database password |

### Security Settings

| Variable | Development | Staging | Production | Description |
|----------|-------------|---------|------------|-------------|
| `REQUIRE_AUTHENTICATION` | false | true | true | Bearer token required |
| `RAILWAY_BEARER_TOKEN` | dev-token | staging-token | production-token | API authentication token |
| `RATE_LIMIT_PER_MINUTE` | 120 | 60 | 60 | Request rate limiting |
| `ENABLE_SECURITY_HEADERS` | false | true | true | Security headers |

### Logging Settings

| Variable | Development | Staging | Production | Description |
|----------|-------------|---------|------------|-------------|
| `LOG_LEVEL` | DEBUG | INFO | INFO | Logging verbosity |
| `ENABLE_AUDIT_LOGGING` | true | true | true | Audit trail logging |
| `LOG_RETENTION_DAYS` | 7 | 14 | 30 | Log retention period |

## Environment Validation

### Validate Configuration

```bash
# Validate current environment
python3 -c "
import os
from pathlib import Path

# Load environment
if Path('.env').exists():
    with open('.env') as f:
        for line in f:
            if '=' in line and not line.startswith('#'):
                key, value = line.strip().split('=', 1)
                os.environ[key] = value

# Check critical variables
required_vars = ['NEO4J_URI', 'NEO4J_USERNAME', 'NEO4J_PASSWORD']
missing = [var for var in required_vars if not os.environ.get(var)]

if missing:
    print(f'❌ Missing required variables: {missing}')
else:
    print('✅ All required variables present')
    
# Check security settings
env_type = os.environ.get('RAILWAY_ENVIRONMENT', 'unknown')
auth_required = os.environ.get('REQUIRE_AUTHENTICATION', 'false').lower() == 'true'
has_token = bool(os.environ.get('RAILWAY_BEARER_TOKEN', '').strip())

print(f'Environment: {env_type}')
print(f'Authentication: {\"enabled\" if auth_required else \"disabled\"}')
print(f'Bearer token: {\"configured\" if has_token else \"missing\"}')
"
```

### Test Database Connection

```bash
# Test Neo4j connection
python3 -c "
import os
from neo4j import GraphDatabase

# Load environment
if os.path.exists('.env'):
    with open('.env') as f:
        for line in f:
            if '=' in line and not line.startswith('#'):
                key, value = line.strip().split('=', 1)
                os.environ[key] = value

uri = os.environ.get('NEO4J_URI')
username = os.environ.get('NEO4J_USERNAME')
password = os.environ.get('NEO4J_PASSWORD')

try:
    driver = GraphDatabase.driver(uri, auth=(username, password))
    with driver.session() as session:
        result = session.run('RETURN 1 as test')
        print('✅ Neo4j connection successful')
        driver.close()
except Exception as e:
    print(f'❌ Neo4j connection failed: {e}')
"
```

## Railway Deployment

### Environment Variable Setup

In Railway dashboard → Variables, add:

```
NEO4J_URI=neo4j+s://your-db-id.databases.neo4j.io:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your-password
RAILWAY_BEARER_TOKEN=your-generated-token
REQUIRE_AUTHENTICATION=true
RATE_LIMIT_PER_MINUTE=60
```

### Production Checklist

Before deploying to production:

- [ ] Production AuraDB instance created
- [ ] Secure bearer token generated (32 bytes)
- [ ] All placeholder values replaced
- [ ] Authentication enabled (`REQUIRE_AUTHENTICATION=true`)
- [ ] Security headers enabled
- [ ] Debug endpoints disabled
- [ ] Log level set to INFO or higher
- [ ] Rate limiting configured appropriately

## Security Best Practices

### Token Generation

```bash
# Production token (32 bytes = 64 hex characters)
openssl rand -hex 32

# Staging token (32 bytes)
openssl rand -hex 32

# Development token (16 bytes = 32 hex characters)
openssl rand -hex 16
```

### Database Security

1. **Use strong passwords** (minimum 16 characters)
2. **Enable authentication** in production and staging
3. **Use AuraDB** for cloud deployments (includes encryption)
4. **Separate databases** for each environment

### Network Security

1. **HTTPS only** in production (Railway provides automatically)
2. **Proper CORS** configuration for ChatGPT integration
3. **Rate limiting** to prevent abuse
4. **Security headers** for protection against common attacks

## Troubleshooting

### Common Issues

**Connection Refused**
- Check NEO4J_URI format
- Verify database is running
- Check network connectivity

**Authentication Failed**
- Verify NEO4J_USERNAME and NEO4J_PASSWORD
- Check if database requires authentication
- Ensure credentials match database setup

**Rate Limited**
- Check RATE_LIMIT_PER_MINUTE setting
- Wait for rate limit to reset
- Use appropriate bearer token

**CORS Errors**
- Check CORS_ALLOWED_ORIGINS setting
- Ensure ChatGPT domain is allowed
- Verify ENABLE_CORS=true

### Getting Help

1. Check deployment logs: `railway logs`
2. Validate configuration with provided scripts
3. Test endpoints with `./validate_deployment.sh`
4. Check Railway environment variables dashboard

---

**Generated**: 2025-09-12T23:56:00Z  
**Version**: AI Garden Enhanced Railway MCP Server v2.3.0  
**Phase**: 3.3 - Environment Configuration Templates
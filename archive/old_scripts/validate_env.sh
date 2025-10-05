#!/bin/bash

# AI Garden Enhanced Railway MCP Server - Environment Validation
# Phase 3.3 - Environment configuration validation script
# Created: 2025-09-12T23:58:00Z

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log() {
    echo -e "${BLUE}[${TIMESTAMP}]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[${TIMESTAMP}] ✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}[${TIMESTAMP}] ⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}[${TIMESTAMP}] ❌ $1${NC}"
}

# Banner
echo -e "${BLUE}"
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║                                                                  ║"
echo "║       🔍 AI Garden Environment Validation v2.3.0                ║"
echo "║                                                                  ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

log "🎯 Starting environment configuration validation..."

# Check for .env file
if [[ ! -f ".env" ]]; then
    log_error ".env file not found"
    log "Available templates:"
    echo "   .env.development - Local development configuration"
    echo "   .env.staging - Pre-production testing configuration"
    echo "   .env.production - Production deployment configuration"
    echo ""
    log "Copy a template to .env:"
    echo "   cp .env.development .env  # For local development"
    echo "   cp .env.staging .env      # For staging deployment"
    echo "   cp .env.production .env   # For production deployment"
    exit 1
fi

log_success ".env file found"

# Load environment variables
set -a
source .env 2>/dev/null || true
set +a

# Validate required variables
log "📋 Validating required environment variables..."

REQUIRED_VARS=("NEO4J_URI" "NEO4J_USERNAME" "NEO4J_PASSWORD")
MISSING_VARS=()
PLACEHOLDER_VARS=()

for var in "${REQUIRED_VARS[@]}"; do
    value="${!var:-}"
    if [[ -z "$value" ]]; then
        MISSING_VARS+=("$var")
    elif [[ "$value" =~ (YOUR_|CHANGE|PLACEHOLDER|REPLACE|your-|change-me) ]]; then
        PLACEHOLDER_VARS+=("$var")
    else
        log_success "$var is configured"
    fi
done

# Check for missing variables
if [[ ${#MISSING_VARS[@]} -gt 0 ]]; then
    log_error "Missing required variables: ${MISSING_VARS[*]}"
    exit 1
fi

# Check for placeholder values
if [[ ${#PLACEHOLDER_VARS[@]} -gt 0 ]]; then
    log_warning "Variables with placeholder values: ${PLACEHOLDER_VARS[*]}"
    log "Please replace placeholder values with actual configuration"
fi

# Validate NEO4J_URI format
log "📋 Validating database configuration..."

if [[ "$NEO4J_URI" =~ ^neo4j\+s:// ]]; then
    log_success "AuraDB connection URI format (secure)"
elif [[ "$NEO4J_URI" =~ ^bolt:// ]]; then
    log_success "Local Neo4j connection URI format"
    if [[ "$NEO4J_URI" != *"localhost"* ]]; then
        log_warning "Non-localhost bolt:// connection - ensure security"
    fi
else
    log_error "Invalid NEO4J_URI format. Expected neo4j+s:// or bolt://"
fi

# Environment detection
log "📋 Detecting environment configuration..."

ENVIRONMENT="${RAILWAY_ENVIRONMENT:-unknown}"
AUTH_REQUIRED="${REQUIRE_AUTHENTICATION:-true}"
BEARER_TOKEN="${RAILWAY_BEARER_TOKEN:-}"
LOG_LEVEL="${LOG_LEVEL:-INFO}"

log "Environment: $ENVIRONMENT"
log "Authentication required: $AUTH_REQUIRED"
log "Log level: $LOG_LEVEL"

# Security validation
log "📋 Validating security configuration..."

if [[ "$AUTH_REQUIRED" == "true" ]]; then
    if [[ -z "$BEARER_TOKEN" ]]; then
        log_error "Authentication required but RAILWAY_BEARER_TOKEN not set"
        log "Generate a secure token with: openssl rand -hex 32"
        exit 1
    elif [[ ${#BEARER_TOKEN} -lt 32 ]]; then
        log_warning "Bearer token is shorter than recommended (32+ characters)"
        log "Generate a longer token with: openssl rand -hex 32"
    else
        log_success "Bearer token configured with appropriate length"
    fi
else
    log_warning "Authentication disabled - not recommended for production"
fi

# Production-specific validations
if [[ "$ENVIRONMENT" == "production" ]]; then
    log "📋 Validating production-specific settings..."
    
    PROD_ISSUES=()
    
    if [[ "$LOG_LEVEL" == "DEBUG" ]]; then
        PROD_ISSUES+=("LOG_LEVEL should not be DEBUG in production")
    fi
    
    if [[ "${ENABLE_DEBUG_ENDPOINTS:-false}" == "true" ]]; then
        PROD_ISSUES+=("ENABLE_DEBUG_ENDPOINTS should be false in production")
    fi
    
    if [[ "${ENABLE_EXPERIMENTAL_FEATURES:-false}" == "true" ]]; then
        PROD_ISSUES+=("ENABLE_EXPERIMENTAL_FEATURES should be false in production")
    fi
    
    if [[ ${#PROD_ISSUES[@]} -gt 0 ]]; then
        log_warning "Production configuration issues found:"
        for issue in "${PROD_ISSUES[@]}"; do
            echo "   • $issue"
        done
    else
        log_success "Production configuration validated"
    fi
fi

# Test database connection if possible
log "📋 Testing database connectivity..."

if command -v python3 &> /dev/null; then
    python3 -c "
import sys
import os

try:
    from neo4j import GraphDatabase
    
    uri = os.environ.get('NEO4J_URI')
    username = os.environ.get('NEO4J_USERNAME') 
    password = os.environ.get('NEO4J_PASSWORD')
    
    print('Testing connection to:', uri)
    driver = GraphDatabase.driver(uri, auth=(username, password))
    
    with driver.session() as session:
        result = session.run('RETURN 1 as test')
        record = result.single()
        
    driver.close()
    print('✅ Database connection successful')
    
except ImportError:
    print('⚠️  neo4j package not installed - skipping connection test')
    print('   Install with: pip install neo4j')
except Exception as e:
    print(f'❌ Database connection failed: {e}')
    sys.exit(1)
" 2>/dev/null || log_warning "Python not available - skipping database connection test"
else
    log_warning "Python not available - skipping database connection test"
fi

# Final summary
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                                                                  ║${NC}"
echo -e "${GREEN}║              🎉 Environment Validation Complete                  ║${NC}"
echo -e "${GREEN}║                                                                  ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Next steps
log "🚀 Next steps:"
echo ""

if [[ ${#PLACEHOLDER_VARS[@]} -gt 0 ]]; then
    echo "   1. Replace placeholder values in .env file"
    echo "   2. Re-run validation: ./validate_env.sh"
else
    echo "   1. Environment configuration is valid ✅"
fi

echo "   2. Test deployment: ./deploy.sh"
echo "   3. Deploy to Railway following DEPLOYMENT_INSTRUCTIONS.md"
echo "   4. Validate deployed service: ./validate_deployment.sh [url] [token]"
echo ""

log_success "Environment validation completed successfully!"
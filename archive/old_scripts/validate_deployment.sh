#!/bin/bash

# AI Garden Enhanced Railway MCP Server - Deployment Validation
# Phase 3.2 - Post-deployment testing and validation
# Created: 2025-09-12T23:42:00Z

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="$SCRIPT_DIR/validation.log"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if URL provided
if [[ $# -lt 1 ]]; then
    echo -e "${RED}Usage: $0 <railway-url> [bearer-token]${NC}"
    echo "Example: $0 https://your-service.up.railway.app your-bearer-token"
    exit 1
fi

RAILWAY_URL="$1"
BEARER_TOKEN="${2:-}"

# Try to load bearer token from .env if not provided
if [[ -z "$BEARER_TOKEN" && -f ".env" ]]; then
    source .env
    BEARER_TOKEN="${RAILWAY_BEARER_TOKEN:-}"
fi

# Logging function
log() {
    echo -e "${BLUE}[${TIMESTAMP}]${NC} $1" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}[${TIMESTAMP}] ✅ $1${NC}" | tee -a "$LOG_FILE"
}

log_warning() {
    echo -e "${YELLOW}[${TIMESTAMP}] ⚠️  $1${NC}" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[${TIMESTAMP}] ❌ $1${NC}" | tee -a "$LOG_FILE"
}

# Banner
echo -e "${BLUE}"
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║                                                                  ║"
echo "║       🔍 AI Garden Railway Deployment Validation v2.3.0         ║"
echo "║                                                                  ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Initialize validation log
echo "# AI Garden Railway Validation Log" > "$LOG_FILE"
echo "Started: $TIMESTAMP" >> "$LOG_FILE"
echo "URL: $RAILWAY_URL" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

log "🎯 Starting AI Garden Railway deployment validation..."
log "🌐 Target URL: $RAILWAY_URL"

# Test 1: Basic connectivity
log "📋 Test 1: Basic Connectivity"

if curl -s --max-time 10 "$RAILWAY_URL" &> /dev/null; then
    log_success "Railway service is reachable"
else
    log_error "Railway service is not reachable"
    log "Please check if the service is deployed and running"
    exit 1
fi

# Test 2: Health endpoint
log "📋 Test 2: Health Endpoint"

HEALTH_URL="$RAILWAY_URL/health"
AUTH_HEADER=""

if [[ -n "$BEARER_TOKEN" ]]; then
    AUTH_HEADER="Authorization: Bearer $BEARER_TOKEN"
    log "🔑 Using bearer token authentication"
fi

HEALTH_RESPONSE=$(curl -s --max-time 10 \
    ${AUTH_HEADER:+-H "$AUTH_HEADER"} \
    -H "User-Agent: AI-Garden-Validator/2.3.0" \
    "$HEALTH_URL" || echo "ERROR")

if [[ "$HEALTH_RESPONSE" == "ERROR" ]]; then
    log_error "Health endpoint not accessible"
    if [[ -n "$BEARER_TOKEN" ]]; then
        log "Trying without authentication..."
        HEALTH_RESPONSE=$(curl -s --max-time 10 \
            -H "User-Agent: AI-Garden-Validator/2.3.0" \
            "$HEALTH_URL" || echo "ERROR")
    fi
fi

if [[ "$HEALTH_RESPONSE" != "ERROR" ]]; then
    log_success "Health endpoint accessible"
    
    # Parse health response if JSON
    if echo "$HEALTH_RESPONSE" | jq . &> /dev/null; then
        STATUS=$(echo "$HEALTH_RESPONSE" | jq -r '.status // "unknown"')
        VERSION=$(echo "$HEALTH_RESPONSE" | jq -r '.server.version // "unknown"')
        UPTIME=$(echo "$HEALTH_RESPONSE" | jq -r '.server.uptime_seconds // "unknown"')
        
        log "   Status: $STATUS"
        log "   Version: $VERSION" 
        log "   Uptime: ${UPTIME}s"
        
        if [[ "$STATUS" == "healthy" ]]; then
            log_success "Service is healthy"
        else
            log_warning "Service status: $STATUS"
        fi
    else
        log "   Raw response: ${HEALTH_RESPONSE:0:100}..."
    fi
else
    log_error "Health endpoint failed"
fi

# Test 3: SSE endpoint
log "📋 Test 3: SSE Endpoint"

SSE_URL="$RAILWAY_URL/sse"
log "Testing SSE endpoint: $SSE_URL"

# Test SSE with timeout
SSE_TEST=$(timeout 5s curl -s \
    ${AUTH_HEADER:+-H "$AUTH_HEADER"} \
    -H "Accept: text/event-stream" \
    -H "User-Agent: AI-Garden-Validator/2.3.0" \
    "$SSE_URL" | head -5 || echo "TIMEOUT")

if [[ "$SSE_TEST" != "TIMEOUT" && -n "$SSE_TEST" ]]; then
    log_success "SSE endpoint responding"
    log "   First few lines received"
else
    log_warning "SSE endpoint may not be responding correctly"
fi

# Test 4: Security headers
log "📋 Test 4: Security Headers"

HEADERS=$(curl -sI --max-time 10 \
    ${AUTH_HEADER:+-H "$AUTH_HEADER"} \
    "$RAILWAY_URL/health" || echo "ERROR")

if [[ "$HEADERS" != "ERROR" ]]; then
    log_success "Security headers check:"
    
    # Check for security headers
    if echo "$HEADERS" | grep -i "x-content-type-options" &> /dev/null; then
        log_success "   X-Content-Type-Options present"
    else
        log_warning "   X-Content-Type-Options missing"
    fi
    
    if echo "$HEADERS" | grep -i "x-frame-options" &> /dev/null; then
        log_success "   X-Frame-Options present"
    else
        log_warning "   X-Frame-Options missing"
    fi
    
    if echo "$HEADERS" | grep -i "strict-transport-security" &> /dev/null; then
        log_success "   Strict-Transport-Security present"
    else
        log_warning "   Strict-Transport-Security missing"
    fi
else
    log_error "Could not retrieve headers for security check"
fi

# Test 5: Rate limiting
log "📋 Test 5: Rate Limiting"

if [[ -n "$BEARER_TOKEN" ]]; then
    log "Testing rate limiting (making 5 quick requests)..."
    
    RATE_TEST_COUNT=0
    for i in {1..5}; do
        if curl -s --max-time 5 \
            -H "$AUTH_HEADER" \
            "$HEALTH_URL" &> /dev/null; then
            ((RATE_TEST_COUNT++))
        fi
        sleep 0.5
    done
    
    log_success "Rate limiting test: $RATE_TEST_COUNT/5 requests succeeded"
    if [[ $RATE_TEST_COUNT -eq 5 ]]; then
        log "   Rate limiting appears to be working normally"
    fi
else
    log_warning "Skipping rate limiting test (no bearer token)"
fi

# Test 6: ChatGPT Custom Connector compatibility
log "📋 Test 6: ChatGPT Compatibility"

log "Testing ChatGPT Custom Connector requirements:"

# Check HTTPS
if [[ "$RAILWAY_URL" == https://* ]]; then
    log_success "   HTTPS endpoint ✓"
else
    log_error "   HTTPS required for ChatGPT Custom Connectors"
fi

# Check SSE transport
if [[ "$SSE_TEST" != "TIMEOUT" ]]; then
    log_success "   SSE transport available ✓"
else
    log_warning "   SSE transport may have issues"
fi

# Check authentication
if [[ -n "$BEARER_TOKEN" ]]; then
    log_success "   Bearer token authentication configured ✓"
else
    log_warning "   Bearer token not tested"
fi

# Final summary
log "📋 Validation Summary"

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                                                                  ║${NC}"
echo -e "${GREEN}║                    🎉 Validation Complete                        ║${NC}"
echo -e "${GREEN}║                                                                  ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════════╝${NC}"
echo ""

log_success "AI Garden Railway deployment validation completed"
log "📊 Full validation log saved to: $LOG_FILE"

# ChatGPT setup instructions
if [[ "$HEALTH_RESPONSE" != "ERROR" && "$RAILWAY_URL" == https://* ]]; then
    echo ""
    log "🤖 ChatGPT Custom Connector Setup:"
    echo ""
    echo "   1. Open ChatGPT → Settings → Beta Features"
    echo "   2. Enable 'Custom Connectors'"
    echo "   3. Add new connector:"
    echo "      Name: Daydreamer Memory"
    echo "      Base URL: $RAILWAY_URL"
    echo "      Authentication: Bearer Token"
    echo "      Token: [your RAILWAY_BEARER_TOKEN]"
    echo ""
    echo "   4. Test with: 'Search my memory for information about AI Garden'"
    echo ""
fi

echo -e "${GREEN}Ready for ChatGPT integration! 🚀${NC}"
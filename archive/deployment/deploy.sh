#!/bin/bash

# AI Garden Enhanced Railway MCP Server - Deployment Automation
# Phase 3.2 - Comprehensive deployment automation with validation
# Created: 2025-09-12T23:40:00Z

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="$SCRIPT_DIR/deploy.log"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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
echo "║       🚀 AI Garden Enhanced Railway MCP Server v2.3.0           ║"
echo "║          Phase 3.2 - Deployment Automation                      ║"
echo "║                                                                  ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Initialize deployment log
echo "# AI Garden Railway Deployment Log" > "$LOG_FILE"
echo "Started: $TIMESTAMP" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

log "🎯 Starting AI Garden Railway deployment automation..."

# Phase 1: Environment Validation
log "📋 Phase 1: Environment Validation"

# Check required commands
REQUIRED_COMMANDS=("git" "python3" "pip3")
for cmd in "${REQUIRED_COMMANDS[@]}"; do
    if ! command -v "$cmd" &> /dev/null; then
        log_error "$cmd is not installed or not in PATH"
        exit 1
    else
        log_success "$cmd is available"
    fi
done

# Check Python version
PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
log "🐍 Python version: $PYTHON_VERSION"

# Check if we're in the correct directory
if [[ ! -f "server_enhanced.py" ]]; then
    log_error "server_enhanced.py not found. Please run from Railway repository root."
    exit 1
fi

# Phase 2: GitHub Repository Setup
log "📋 Phase 2: GitHub Repository Setup"

# Check if git repository is initialized
if [[ ! -d ".git" ]]; then
    log_error "Git repository not initialized. Run 'git init' first."
    exit 1
fi

# Check for uncommitted changes
if [[ -n $(git status --porcelain) ]]; then
    log_warning "Uncommitted changes detected. Committing..."
    git add .
    git commit -m "chore: auto-commit before deployment - $TIMESTAMP"
    log_success "Changes committed"
fi

# Phase 3: Environment Configuration
log "📋 Phase 3: Environment Configuration"

# Check for .env file
if [[ ! -f ".env" ]]; then
    log_warning ".env file not found. Creating from template..."
    if [[ -f ".env.example" ]]; then
        cp ".env.example" ".env"
        log "⚠️  Please edit .env file with your actual values before continuing"
        log "   Required variables: NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD, RAILWAY_BEARER_TOKEN"
        echo ""
        read -p "Press Enter after you've configured .env file..."
    else
        log_error ".env.example not found. Cannot create configuration."
        exit 1
    fi
fi

# Validate critical environment variables
source .env 2>/dev/null || true

REQUIRED_VARS=("NEO4J_URI" "NEO4J_USERNAME" "NEO4J_PASSWORD")
MISSING_VARS=()

for var in "${REQUIRED_VARS[@]}"; do
    if [[ -z "${!var:-}" ]]; then
        MISSING_VARS+=("$var")
    fi
done

if [[ ${#MISSING_VARS[@]} -gt 0 ]]; then
    log_error "Missing required environment variables: ${MISSING_VARS[*]}"
    log "Please configure these in your .env file"
    exit 1
fi

log_success "Environment variables validated"

# Phase 4: Security Token Generation
log "📋 Phase 4: Security Token Generation"

if [[ -z "${RAILWAY_BEARER_TOKEN:-}" ]]; then
    log_warning "RAILWAY_BEARER_TOKEN not set. Generating secure token..."
    
    # Generate secure 32-byte token
    if command -v openssl &> /dev/null; then
        BEARER_TOKEN=$(openssl rand -hex 32)
        echo "RAILWAY_BEARER_TOKEN=$BEARER_TOKEN" >> .env
        log_success "Bearer token generated and added to .env"
        log "🔑 Token: $BEARER_TOKEN"
        log "⚠️  Save this token securely - you'll need it for Railway deployment"
    else
        log_error "OpenSSL not available for token generation"
        log "Please manually generate a secure token and add RAILWAY_BEARER_TOKEN to .env"
        exit 1
    fi
else
    log_success "RAILWAY_BEARER_TOKEN already configured"
fi

# Phase 5: Pre-deployment Testing
log "📋 Phase 5: Pre-deployment Testing"

log "🧪 Testing Python dependencies..."
if python3 -c "import requirements; print('Requirements import test passed')" 2>/dev/null; then
    log_success "Python environment ready"
else
    log "Installing dependencies..."
    pip3 install -r requirements.txt
    log_success "Dependencies installed"
fi

# Test import of main modules
log "🧪 Testing module imports..."
python3 -c "
import sys
sys.path.append('.')

try:
    from server_enhanced import EnhancedRailwayMCPServer
    from security_middleware import SecurityAuditLogger
    from logging_config import AIGardenLogger
    print('✅ All critical modules import successfully')
except Exception as e:
    print(f'❌ Module import failed: {e}')
    sys.exit(1)
"

if [[ $? -eq 0 ]]; then
    log_success "Module imports validated"
else
    log_error "Module import validation failed"
    exit 1
fi

# Phase 6: Deployment Instructions
log "📋 Phase 6: Deployment Instructions"

echo ""
log "🎉 Pre-deployment validation complete!"
echo ""
log "📝 Next steps for Railway deployment:"
echo ""
echo "   1. Push to GitHub:"
echo "      git remote add origin https://github.com/YOUR_USERNAME/neo4j-mcp-railway.git"
echo "      git push -u origin main"
echo ""
echo "   2. Deploy on Railway:"
echo "      - Go to railway.app"
echo "      - Connect your GitHub repository"  
echo "      - Set environment variables (see .env file)"
echo ""
echo "   3. Required Railway Environment Variables:"
echo "      NEO4J_URI=${NEO4J_URI}"
echo "      NEO4J_USERNAME=${NEO4J_USERNAME}"
echo "      NEO4J_PASSWORD=[your_password]"
echo "      RAILWAY_BEARER_TOKEN=[your_generated_token]"
echo ""
echo "   4. Test deployment:"
echo "      ./validate_deployment.sh https://your-service.up.railway.app"
echo ""

# Save deployment manifest
cat > "deployment_manifest.json" << EOF
{
  "deployment": {
    "timestamp": "$TIMESTAMP",
    "version": "2.3.0",
    "phase": "3.2",
    "status": "ready",
    "validation": {
      "environment": "passed",
      "dependencies": "passed",
      "modules": "passed",
      "security": "passed"
    }
  },
  "next_steps": [
    "Push to GitHub repository",
    "Deploy on Railway platform", 
    "Configure environment variables",
    "Validate deployment endpoint"
  ]
}
EOF

log_success "Deployment manifest saved to deployment_manifest.json"
log_success "🚀 AI Garden Railway deployment automation complete!"

echo ""
echo -e "${GREEN}Ready for Railway deployment! 🎯${NC}"
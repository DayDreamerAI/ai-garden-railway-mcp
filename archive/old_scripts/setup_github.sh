#!/bin/bash

# AI Garden Enhanced Railway MCP Server - GitHub Repository Setup
# Phase 3.2 - Automated GitHub repository creation and configuration  
# Created: 2025-09-12T23:44:00Z

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

# Get repository name from user
REPO_NAME="${1:-neo4j-mcp-railway}"

# Logging function
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
echo "║       📚 AI Garden GitHub Repository Setup v2.3.0               ║"
echo "║                                                                  ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

log "🎯 Setting up GitHub repository: $REPO_NAME"

# Check if GitHub CLI is available
if ! command -v gh &> /dev/null; then
    log_error "GitHub CLI (gh) is not installed"
    log "Install it with: brew install gh (macOS) or visit https://cli.github.com"
    log ""
    log "Alternative manual setup:"
    echo "  1. Create repository on GitHub: https://github.com/new"
    echo "  2. Set repository name: $REPO_NAME"
    echo "  3. Make it public (required for Railway free tier)"
    echo "  4. Don't initialize with README (we already have one)"
    echo "  5. Run: git remote add origin https://github.com/YOUR_USERNAME/$REPO_NAME.git"
    echo "  6. Run: git push -u origin main"
    exit 1
fi

# Check GitHub authentication  
if ! gh auth status &> /dev/null; then
    log_warning "GitHub CLI not authenticated"
    log "Attempting to authenticate..."
    gh auth login
fi

log_success "GitHub CLI authenticated"

# Check if we're in a git repository
if [[ ! -d ".git" ]]; then
    log_error "Not in a git repository. Run 'git init' first."
    exit 1
fi

# Check for uncommitted changes
if [[ -n $(git status --porcelain) ]]; then
    log_warning "Uncommitted changes detected. Committing..."
    git add .
    git commit -m "chore: pre-github-setup commit - $TIMESTAMP"
    log_success "Changes committed"
fi

# Create GitHub repository
log "📚 Creating GitHub repository..."

# Repository description
REPO_DESCRIPTION="AI Garden Enhanced Railway MCP Server v2.3.0 - Multi-agent federation infrastructure for ChatGPT Custom Connector integration with Daydreamer memory sovereignty"

if gh repo create "$REPO_NAME" \
    --public \
    --description "$REPO_DESCRIPTION" \
    --source . \
    --remote origin \
    --push; then
    log_success "GitHub repository created and pushed"
else
    log_error "Failed to create GitHub repository"
    log "This might be because the repository already exists"
    log ""
    log "Manual setup steps:"
    echo "  1. Check if repository exists: gh repo view $REPO_NAME"
    echo "  2. If exists, add remote: git remote add origin https://github.com/$(gh api user --jq .login)/$REPO_NAME.git"
    echo "  3. Push code: git push -u origin main"
    exit 1
fi

# Get repository URL
REPO_URL=$(gh repo view --json url --jq .url)
log "🌐 Repository URL: $REPO_URL"

# Create deployment instructions
cat > "DEPLOYMENT_INSTRUCTIONS.md" << EOF
# AI Garden Railway Deployment Instructions

## Quick Deploy to Railway

### 1. Prerequisites
- ✅ GitHub repository: $REPO_URL
- ✅ Railway account: [railway.app](https://railway.app)
- ✅ AuraDB Neo4j database (or local Neo4j)

### 2. Deploy on Railway

1. **Connect Repository**
   - Go to [railway.app](https://railway.app)
   - Click "Deploy from GitHub"
   - Select: \`$REPO_NAME\`
   - Railway will auto-detect Python project

2. **Environment Variables**
   Add these in Railway dashboard → Variables:
   \`\`\`
   NEO4J_URI=neo4j+s://your-db-id.databases.neo4j.io:7687
   NEO4J_USERNAME=neo4j
   NEO4J_PASSWORD=your-password
   RAILWAY_BEARER_TOKEN=your-generated-token
   REQUIRE_AUTHENTICATION=true
   RATE_LIMIT_PER_MINUTE=60
   \`\`\`

3. **Generate Secure Token**
   \`\`\`bash
   openssl rand -hex 32
   \`\`\`

### 3. Validate Deployment

After Railway deploys your service:

\`\`\`bash
# Test your deployment
./validate_deployment.sh https://your-service.up.railway.app your-bearer-token
\`\`\`

### 4. ChatGPT Integration

1. Open ChatGPT → Settings → Beta Features
2. Enable "Custom Connectors"
3. Add connector:
   - **Name**: Daydreamer Memory
   - **Base URL**: \`https://your-service.up.railway.app\`
   - **Auth**: Bearer Token
   - **Token**: Your \`RAILWAY_BEARER_TOKEN\`

### 5. Test Integration

In ChatGPT: *"Search my memory for information about AI Garden"*

---

**Generated**: $TIMESTAMP  
**Repository**: $REPO_URL  
**Version**: AI Garden Enhanced Railway MCP Server v2.3.0
EOF

# Commit deployment instructions
git add DEPLOYMENT_INSTRUCTIONS.md
git commit -m "docs: add comprehensive Railway deployment instructions

- Quick deploy guide with Railway platform integration
- Environment variable configuration templates  
- ChatGPT Custom Connector setup instructions
- Post-deployment validation steps

Ready for Phase 3.3: Environment templates"

git push origin main

log_success "Deployment instructions added and pushed"

# Final summary
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                                                                  ║${NC}"
echo -e "${GREEN}║                   🎉 GitHub Setup Complete                       ║${NC}"
echo -e "${GREEN}║                                                                  ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════════╝${NC}"
echo ""

log_success "GitHub repository setup completed successfully"
log "📚 Repository: $REPO_URL"
log "📋 Deployment guide: DEPLOYMENT_INSTRUCTIONS.md"

echo ""
log "🚀 Next steps:"
echo "   1. Go to railway.app and connect your GitHub repository"
echo "   2. Configure environment variables (see DEPLOYMENT_INSTRUCTIONS.md)"
echo "   3. Deploy and validate with ./validate_deployment.sh"
echo "   4. Set up ChatGPT Custom Connector"
echo ""

echo -e "${GREEN}Ready for Railway deployment! 🎯${NC}"
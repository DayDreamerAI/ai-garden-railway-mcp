#!/bin/bash
# Deploy to Railway - Sync Script
# Private (daydreamer-mcp) → Public (ai-garden-railway-mcp)

set -euo pipefail

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}🚀 Daydreamer → Railway Deployment Sync${NC}"
echo -e "${BLUE}==========================================${NC}\n"

# Configuration
PRIVATE_REPO_PATH="/Users/daydreamer/Documents/VibeProjects/daydreamer-mcp/llm/mcp/connectors/mcp-claude-connector/neo4j-mcp-railway-repo"
PUBLIC_REPO_URL="https://github.com/DayDreamerAI/ai-garden-railway-mcp.git"
PUBLIC_REPO_NAME="ai-garden-railway-mcp"
DEPLOYMENT_DIR="/tmp/${PUBLIC_REPO_NAME}"
VERSION=$(date +"%Y.%m.%d-%H%M")

# Deployment files to sync
DEPLOYMENT_FILES=(
    "mcp-claude-connector-memory-server.py"
    "railway.toml"
    "requirements.txt"
    "README.md"
)

# Supporting files (optional)
OPTIONAL_FILES=(
    ".env.template"
)

# Step 1: Validate source files
echo -e "${YELLOW}📋 Step 1: Validating source files...${NC}"
cd "$PRIVATE_REPO_PATH"

for file in "${DEPLOYMENT_FILES[@]}"; do
    if [ ! -f "$file" ]; then
        echo -e "${RED}❌ Required file missing: $file${NC}"
        exit 1
    fi

    # Security check: no hardcoded secrets (but allow env var assignments)
    if grep -iE "password.*=.*['\"][^'\"]+['\"]" "$file" 2>/dev/null | grep -v "YOUR_.*_HERE\|REPLACE\|TEMPLATE\|os\.environ\|getenv\|env\.get"; then
        echo -e "${RED}❌ Hardcoded secret detected in $file${NC}"
        exit 1
    fi
done

echo -e "${GREEN}✅ All source files validated${NC}\n"

# Step 2: Clone/update public deployment repo
echo -e "${YELLOW}📋 Step 2: Preparing deployment repository...${NC}"

if [ -d "$DEPLOYMENT_DIR" ]; then
    echo -e "${BLUE}Updating existing clone...${NC}"
    cd "$DEPLOYMENT_DIR"
    git fetch origin
    git checkout main
    git pull origin main
else
    echo -e "${BLUE}Cloning deployment repository...${NC}"
    git clone "$PUBLIC_REPO_URL" "$DEPLOYMENT_DIR"
    cd "$DEPLOYMENT_DIR"
fi

echo -e "${GREEN}✅ Deployment repository ready${NC}\n"

# Step 3: Clean deployment directory
echo -e "${YELLOW}📋 Step 3: Cleaning deployment directory...${NC}"

# Remove old files (keep .git and README.md)
find . -type f ! -path "./.git/*" ! -name "README.md" ! -name ".gitignore" -delete 2>/dev/null || true

echo -e "${GREEN}✅ Deployment directory cleaned${NC}\n"

# Step 4: Copy deployment files
echo -e "${YELLOW}📋 Step 4: Copying deployment files...${NC}"

for file in "${DEPLOYMENT_FILES[@]}"; do
    cp "$PRIVATE_REPO_PATH/$file" "./"
    echo -e "${GREEN}  ✓ Copied: $file${NC}"
done

# Copy optional files if they exist
for file in "${OPTIONAL_FILES[@]}"; do
    if [ -f "$PRIVATE_REPO_PATH/$file" ]; then
        cp "$PRIVATE_REPO_PATH/$file" "./"
        echo -e "${GREEN}  ✓ Copied: $file (optional)${NC}"
    fi
done

echo -e "${GREEN}✅ Files copied successfully${NC}\n"

# Step 5: Update deployment README
echo -e "${YELLOW}📋 Step 5: Updating deployment README...${NC}"

cat > README.md << 'EOF'
# Daydreamer Railway MCP Server

**Production Deployment for Claude Custom Connectors**

## 🚀 Live Deployment

- **URL**: https://ai-garden-railway-mcp-production.up.railway.app
- **Protocol**: SSE Transport (Custom Connector compatible)
- **Database**: Neo4j AuraDB InstanceDaydreamer_01

## 🛠️ Current Deployment

### Tier 1: Core Memory Tools (5 tools)

1. **search_nodes** - Semantic search via JinaV3 or exact name lookup
2. **memory_stats** - Graph statistics with V6 status
3. **create_entities** - Entity creation with embeddings
4. **add_observations** - Observation management
5. **raw_cypher_query** - Direct Cypher access

## 📊 Production Data

- **Entities**: 27,487
- **Relationships**: 110,449
- **V6 Observations**: 14,414
- **Conversation Sessions**: 537

## 🔧 Environment Variables

Required environment variables (set in Railway):

```env
NEO4J_URI=neo4j+s://8c3b5488.databases.neo4j.io
NEO4J_PASSWORD=<your-auradb-password>
JINA_API_KEY=<your-jina-api-key>
```

## 📦 Deployment

Railway auto-deploys from `main` branch.

### Manual Deployment

```bash
# Install Railway CLI
brew install railway

# Login
railway login

# Deploy
railway up
```

## 🧪 Testing

```bash
# Test production endpoint
curl https://ai-garden-railway-mcp-production.up.railway.app/health
```

## 📚 Documentation

- **Setup Guide**: See main daydreamer-mcp repository
- **Architecture**: Custom Connector + SSE transport
- **Memory System**: V6 observation nodes, temporal binding

---

**Deployment Version**: Tier 1 (5 tools)
**Last Updated**: $(date +"%Y-%m-%d")
**Source**: Private daydreamer-mcp repository
EOF

echo -e "${GREEN}✅ README updated${NC}\n"

# Step 6: Create .gitignore if missing
if [ ! -f ".gitignore" ]; then
    echo -e "${YELLOW}📋 Step 6: Creating .gitignore...${NC}"
    cat > .gitignore << 'EOF'
# Environment
.env
.env.local
.env.production

# Python
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
*.so
*.egg
*.egg-info/
dist/
build/

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# Logs
*.log
logs/
EOF
    echo -e "${GREEN}✅ .gitignore created${NC}\n"
fi

# Step 7: Commit changes
echo -e "${YELLOW}📋 Step 7: Committing deployment...${NC}"

git add -A

if git diff --staged --quiet; then
    echo -e "${YELLOW}⚠️  No changes to commit${NC}"
else
    git commit -m "deploy: Tier 1 memory server v${VERSION}

Deployment includes:
- mcp-claude-connector-memory-server.py (Tier 1: 5 tools)
- railway.toml (Railway configuration)
- requirements.txt (Python dependencies)
- README.md (deployment documentation)

Tools deployed:
1. search_nodes - Semantic search or exact lookup
2. memory_stats - Graph statistics
3. create_entities - Entity creation
4. add_observations - Observation management
5. raw_cypher_query - Direct Cypher access

🤖 Synced from private daydreamer-mcp repository
Version: ${VERSION}"

    echo -e "${GREEN}✅ Changes committed${NC}\n"
fi

# Step 8: Push to trigger deployment
echo -e "${YELLOW}📋 Step 8: Pushing to Railway...${NC}"

git push origin main

echo -e "${GREEN}✅ Pushed to public repository${NC}\n"

# Step 9: Wait for deployment
echo -e "${YELLOW}📋 Step 9: Waiting for Railway deployment...${NC}"
echo -e "${BLUE}Railway will auto-deploy from main branch${NC}"
echo -e "${BLUE}Monitor deployment: https://railway.app${NC}\n"

sleep 15

# Step 10: Test deployment
echo -e "${YELLOW}📋 Step 10: Testing deployment...${NC}"

HEALTH_URL="https://ai-garden-railway-mcp-production.up.railway.app/health"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$HEALTH_URL" || echo "000")

if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✅ Health check passed (HTTP $HTTP_CODE)${NC}"
elif [ "$HTTP_CODE" = "000" ]; then
    echo -e "${YELLOW}⚠️  Server not responding (may still be deploying)${NC}"
else
    echo -e "${RED}❌ Health check failed (HTTP $HTTP_CODE)${NC}"
fi

echo ""
echo -e "${BLUE}==========================================${NC}"
echo -e "${GREEN}📦 Deployment Summary${NC}"
echo -e "${BLUE}==========================================${NC}"
echo -e "Version: ${VERSION}"
echo -e "Files synced: ${#DEPLOYMENT_FILES[@]}"
echo -e "Public repo: ${PUBLIC_REPO_URL}"
echo -e "Production URL: https://ai-garden-railway-mcp-production.up.railway.app"
echo -e "${BLUE}==========================================${NC}\n"

echo -e "${GREEN}✅ Deployment sync complete!${NC}"
echo -e "${YELLOW}Next step: Run test suite${NC}"
echo -e "  cd $PRIVATE_REPO_PATH"
echo -e "  RAILWAY_SERVER_URL=\"https://ai-garden-railway-mcp-production.up.railway.app\" TEST_MODE=railway python3 test_railway_memory_server.py\n"

# Cleanup
cd "$PRIVATE_REPO_PATH"

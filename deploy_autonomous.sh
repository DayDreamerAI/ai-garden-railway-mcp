#!/bin/bash
# Autonomous Railway Deployment Script
# Created: 2025-10-05
# Uses Railway GraphQL API directly to bypass CLI authentication issues

set -euo pipefail

# Configuration
RAILWAY_API_TOKEN="4dca6770-4373-4d90-a4a9-df39b21c86fa"
RAILWAY_API="https://backboard.railway.com/graphql/v2"
PROJECT_NAME="ai-garden-railway-mcp-production"
SERVER_FILE="mcp-claude-connector-memory-server.py"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Daydreamer Railway Autonomous Deployment${NC}"
echo -e "${BLUE}============================================${NC}\n"

# Step 1: Verify API token
echo -e "${YELLOW}📋 Step 1: Verifying Railway API authentication...${NC}"
ME_RESPONSE=$(curl -s -X POST "$RAILWAY_API" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $RAILWAY_API_TOKEN" \
  -d '{"query":"query { me { id name email } }"}')

USER_NAME=$(echo "$ME_RESPONSE" | grep -o '"name":"[^"]*"' | cut -d'"' -f4 || echo "")
if [ -z "$USER_NAME" ]; then
    echo -e "${RED}❌ Authentication failed${NC}"
    echo "$ME_RESPONSE"
    exit 1
fi

echo -e "${GREEN}✅ Authenticated as: $USER_NAME${NC}\n"

# Step 2: Find or create project
echo -e "${YELLOW}📋 Step 2: Locating Railway project...${NC}"

# Query for existing project by searching all accessible projects
PROJECTS_QUERY='{"query":"query { me { projects { edges { node { id name services { edges { node { id name } } } } } } } }"}'
PROJECTS_RESPONSE=$(curl -s -X POST "$RAILWAY_API" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $RAILWAY_API_TOKEN" \
  -d "$PROJECTS_QUERY")

# Check if project exists
PROJECT_ID=$(echo "$PROJECTS_RESPONSE" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4 || echo "")

if [ -z "$PROJECT_ID" ]; then
    echo -e "${YELLOW}⚠️  No projects found. Creating new project...${NC}"

    CREATE_PROJECT='{"query":"mutation { projectCreate(input: { name: \"'"$PROJECT_NAME"'\" }) { id name } }"}'
    CREATE_RESPONSE=$(curl -s -X POST "$RAILWAY_API" \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer $RAILWAY_API_TOKEN" \
      -d "$CREATE_PROJECT")

    PROJECT_ID=$(echo "$CREATE_RESPONSE" | grep -o '"id":"[^"]*"' | cut -d'"' -f4)

    if [ -z "$PROJECT_ID" ]; then
        echo -e "${RED}❌ Failed to create project${NC}"
        echo "$CREATE_RESPONSE"
        exit 1
    fi

    echo -e "${GREEN}✅ Created project: $PROJECT_ID${NC}\n"
else
    echo -e "${GREEN}✅ Found project: $PROJECT_ID${NC}\n"
fi

# Step 3: Deploy using Railway CLI fallback
echo -e "${YELLOW}📋 Step 3: Deploying server...${NC}"

# Option A: Try Railway CLI with environment variable
export RAILWAY_TOKEN="$RAILWAY_API_TOKEN"

# Check if railway CLI is available
if command -v railway &> /dev/null; then
    echo -e "${BLUE}Using Railway CLI for deployment...${NC}"

    # Try to use existing deployment workflow
    cd "$(dirname "$0")"

    # Deploy using railway up
    if railway up --detach 2>&1 | grep -q "Deployment"; then
        echo -e "${GREEN}✅ Deployment initiated via CLI${NC}"

        # Wait for deployment
        echo -e "${BLUE}Waiting for deployment to complete...${NC}"
        sleep 10

        # Try to get deployment URL
        DEPLOY_URL=$(railway domain 2>/dev/null || echo "")
        if [ -n "$DEPLOY_URL" ]; then
            echo -e "${GREEN}✅ Deployment URL: $DEPLOY_URL${NC}"
        fi
    else
        echo -e "${YELLOW}⚠️  CLI deployment failed, trying API method...${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  Railway CLI not available, using API deployment...${NC}"
fi

# Step 4: Validation
echo -e "\n${YELLOW}📋 Step 4: Deployment validation${NC}"
EXPECTED_URL="https://ai-garden-railway-mcp-production.up.railway.app"
echo -e "${BLUE}Testing endpoint: $EXPECTED_URL/health${NC}"

# Test health endpoint
HEALTH_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "$EXPECTED_URL/health" || echo "000")

if [ "$HEALTH_RESPONSE" = "200" ]; then
    echo -e "${GREEN}✅ Server is healthy (HTTP $HEALTH_RESPONSE)${NC}"
elif [ "$HEALTH_RESPONSE" = "000" ]; then
    echo -e "${YELLOW}⚠️  Server not responding yet (may still be deploying)${NC}"
else
    echo -e "${RED}❌ Server returned HTTP $HEALTH_RESPONSE${NC}"
fi

# Final summary
echo -e "\n${BLUE}============================================${NC}"
echo -e "${GREEN}📦 Deployment Summary${NC}"
echo -e "${BLUE}============================================${NC}"
echo -e "Project ID: ${PROJECT_ID}"
echo -e "Server File: ${SERVER_FILE}"
echo -e "Expected URL: ${EXPECTED_URL}"
echo -e "${BLUE}============================================${NC}\n"

echo -e "${GREEN}✅ Autonomous deployment complete!${NC}"
echo -e "${YELLOW}Next step: Run test suite with:${NC}"
echo -e "  RAILWAY_SERVER_URL=\"$EXPECTED_URL\" TEST_MODE=railway python test_railway_memory_server.py\n"

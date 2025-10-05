#!/bin/bash

# AI Garden Railway Quick Deploy - Phase 4.2
# Run this script with your Railway API key for automated deployment
# Usage: ./quick_deploy_railway.sh [your-api-key]

set -euo pipefail

API_KEY="${1:-}"
if [[ -z "$API_KEY" ]]; then
    echo "❌ Usage: ./quick_deploy_railway.sh [your-railway-api-key]"
    echo "   Get your API key from: https://railway.app/account/tokens"
    exit 1
fi

echo "🚀 AI Garden Railway Quick Deploy v2.3.0"
echo "⚠️  Using API key: ${API_KEY:0:8}..."

# Install Railway CLI via npm (if available)
if ! command -v railway &> /dev/null; then
    echo "📦 Installing Railway CLI..."
    if command -v npm &> /dev/null; then
        npm install -g @railway/cli
    elif command -v brew &> /dev/null; then
        brew install railway
    else
        echo "❌ Please install Railway CLI manually:"
        echo "   npm install -g @railway/cli"
        echo "   OR brew install railway"
        echo "   OR curl -fsSL https://railway.app/install.sh | sh"
        exit 1
    fi
fi

# Login with API key
echo "🔑 Authenticating with Railway..."
echo "$API_KEY" | railway login --api-key

# Initialize project
echo "🎯 Creating Railway project..."
railway project create ai-garden-mcp --name "AI Garden MCP Server"

# Connect to current directory
echo "📁 Linking current directory..."
railway link

# Set environment variables
echo "⚙️  Setting environment variables..."
railway variables set NEO4J_URI="bolt://localhost:7687"
railway variables set NEO4J_USERNAME="neo4j"
railway variables set NEO4J_PASSWORD="daydreamer2025"
railway variables set RAILWAY_BEARER_TOKEN="c457969f6d9c3716ac9352e564c35d75d3952aa746982bea91ec5d23df73b827"
railway variables set REQUIRE_AUTHENTICATION="true"
railway variables set RATE_LIMIT_PER_MINUTE="60"
railway variables set AI_GARDEN_FEDERATION_ENABLED="true"
railway variables set AI_GARDEN_VERSION="2.3.0"

# Deploy
echo "🚀 Deploying to Railway..."
railway up --detach

# Get deployment URL
echo "🌐 Getting deployment URL..."
DEPLOYMENT_URL=$(railway domain)

echo ""
echo "✅ Deployment complete!"
echo "🌐 URL: $DEPLOYMENT_URL"
echo ""
echo "🧪 Testing deployment..."
./validate_deployment.sh "$DEPLOYMENT_URL" "c457969f6d9c3716ac9352e564c35d75d3952aa746982bea91ec5d23df73b827"

echo ""
echo "🎉 Phase 4.2 Complete! Ready for ChatGPT integration."
echo "📋 Next: Set up ChatGPT Custom Connector with:"
echo "   - Base URL: $DEPLOYMENT_URL"
echo "   - Token: c457969f6d9c3716ac9352e564c35d75d3952aa746982bea91ec5d23df73b827"
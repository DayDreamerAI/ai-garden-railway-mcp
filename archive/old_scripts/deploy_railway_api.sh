#!/bin/bash

# AI Garden Railway API Deployment - Phase 4.2
# Direct API deployment using Railway REST API

set -euo pipefail

API_TOKEN="${RAILWAY_API_TOKEN:-}"
GITHUB_REPO="JulianCrespi/ai-garden-railway-mcp"

if [ -z "$API_TOKEN" ]; then
    echo "❌ Error: RAILWAY_API_TOKEN environment variable not set"
    echo "Set it with: export RAILWAY_API_TOKEN='your-token'"
    exit 1
fi

echo "🚀 AI Garden Railway API Deployment v2.3.0"
echo "🔑 Using API token for direct deployment..."

# Create project
echo "📦 Creating Railway project..."
PROJECT_RESPONSE=$(curl -s -X POST "https://backboard.railway.app/graphql" \
  -H "Authorization: Bearer $API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "mutation projectCreate($input: ProjectCreateInput!) { projectCreate(input: $input) { id name } }",
    "variables": {
      "input": {
        "name": "ai-garden-mcp-server",
        "description": "AI Garden Enhanced Railway MCP Server v2.3.0"
      }
    }
  }')

echo "📋 Project response: $PROJECT_RESPONSE"

PROJECT_ID=$(echo "$PROJECT_RESPONSE" | jq -r '.data.projectCreate.id')

if [[ "$PROJECT_ID" == "null" ]]; then
  echo "❌ Failed to create project"
  echo "Response: $PROJECT_RESPONSE"
  exit 1
fi

echo "✅ Project created with ID: $PROJECT_ID"

# Connect GitHub repo
echo "🔗 Connecting GitHub repository..."
SERVICE_RESPONSE=$(curl -s -X POST "https://backboard.railway.app/graphql" \
  -H "Authorization: Bearer $API_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"query\": \"mutation serviceCreate(\$input: ServiceCreateInput!) { serviceCreate(input: \$input) { id name } }\",
    \"variables\": {
      \"input\": {
        \"projectId\": \"$PROJECT_ID\",
        \"name\": \"ai-garden-mcp\",
        \"source\": {
          \"repo\": \"$GITHUB_REPO\",
          \"branch\": \"main\"
        }
      }
    }
  }")

echo "📋 Service response: $SERVICE_RESPONSE"

SERVICE_ID=$(echo "$SERVICE_RESPONSE" | jq -r '.data.serviceCreate.id')
echo "✅ Service created with ID: $SERVICE_ID"

# Set environment variables
echo "⚙️  Setting environment variables..."

ENV_VARS=(
  "NEO4J_URI:bolt://localhost:7687"
  "NEO4J_USERNAME:neo4j"
  "NEO4J_PASSWORD:daydreamer2025"
  "RAILWAY_BEARER_TOKEN:c457969f6d9c3716ac9352e564c35d75d3952aa746982bea91ec5d23df73b827"
  "REQUIRE_AUTHENTICATION:true"
  "RATE_LIMIT_PER_MINUTE:60"
  "AI_GARDEN_FEDERATION_ENABLED:true"
  "AI_GARDEN_VERSION:2.3.0"
  "MCP_TRANSPORT:sse"
)

for env_var in "${ENV_VARS[@]}"; do
  KEY="${env_var%%:*}"
  VALUE="${env_var#*:}"
  
  curl -s -X POST "https://backboard.railway.app/graphql" \
    -H "Authorization: Bearer $API_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{
      \"query\": \"mutation variableUpsert(\$input: VariableUpsertInput!) { variableUpsert(input: \$input) { id } }\",
      \"variables\": {
        \"input\": {
          \"projectId\": \"$PROJECT_ID\",
          \"serviceId\": \"$SERVICE_ID\",
          \"name\": \"$KEY\",
          \"value\": \"$VALUE\"
        }
      }
    }" > /dev/null
    
  echo "✅ Set $KEY"
done

# Generate domain
echo "🌐 Generating Railway domain..."
DOMAIN_RESPONSE=$(curl -s -X POST "https://backboard.railway.app/graphql" \
  -H "Authorization: Bearer $API_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"query\": \"mutation serviceDomainCreate(\$input: ServiceDomainCreateInput!) { serviceDomainCreate(input: \$input) { domain } }\",
    \"variables\": {
      \"input\": {
        \"serviceId\": \"$SERVICE_ID\"
      }
    }
  }")

DEPLOYMENT_URL=$(echo "$DOMAIN_RESPONSE" | jq -r '.data.serviceDomainCreate.domain')

if [[ "$DEPLOYMENT_URL" != "null" ]]; then
  DEPLOYMENT_URL="https://$DEPLOYMENT_URL"
  echo "✅ Domain created: $DEPLOYMENT_URL"
else
  echo "⚠️  Domain creation failed, will get URL after deployment"
fi

# Trigger deployment
echo "🚀 Triggering deployment..."
DEPLOY_RESPONSE=$(curl -s -X POST "https://backboard.railway.app/graphql" \
  -H "Authorization: Bearer $API_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"query\": \"mutation serviceInstanceRedeploy(\$input: ServiceInstanceRedeployInput!) { serviceInstanceRedeploy(input: \$input) { id } }\",
    \"variables\": {
      \"input\": {
        \"serviceId\": \"$SERVICE_ID\"
      }
    }
  }")

echo "📋 Deploy response: $DEPLOY_RESPONSE"

echo ""
echo "🎉 Railway deployment initiated!"
echo "📋 Project ID: $PROJECT_ID"
echo "📋 Service ID: $SERVICE_ID"

if [[ "$DEPLOYMENT_URL" != "null" ]]; then
  echo "🌐 Deployment URL: $DEPLOYMENT_URL"
  echo ""
  echo "⏳ Waiting for deployment to complete (60 seconds)..."
  sleep 60
  
  echo "🧪 Testing deployment..."
  ./validate_deployment.sh "$DEPLOYMENT_URL" "c457969f6d9c3716ac9352e564c35d75d3952aa746982bea91ec5d23df73b827"
else
  echo "🌐 Check Railway dashboard for deployment URL: https://railway.app/project/$PROJECT_ID"
fi

echo ""
echo "✅ Phase 4.2 Complete!"
echo "🔑 Bearer Token: c457969f6d9c3716ac9352e564c35d75d3952aa746982bea91ec5d23df73b827"
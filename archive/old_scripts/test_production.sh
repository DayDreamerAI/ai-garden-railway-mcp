#!/bin/bash

echo "Testing MCP Server at Railway Production"
echo "========================================="

URL="https://ai-garden-railway-mcp-production.up.railway.app"

echo -e "\n1. Testing root endpoint..."
curl -s "$URL/" | python3 -m json.tool

echo -e "\n2. Testing MCP tools/list..."
curl -X POST "$URL/mcp" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/list","params":{},"id":1}' \
  -s | python3 -m json.tool

echo -e "\n3. Testing MCP search_entities..."
curl -X POST "$URL/mcp" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"search_entities","arguments":{"query":"AI Garden"}},"id":2}' \
  -s | python3 -m json.tool
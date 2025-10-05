#!/bin/bash

echo "Testing MCP Server with Live Neo4j Data"
echo "========================================"

URL="https://ai-garden-railway-mcp-production.up.railway.app"

echo -e "\n1. Testing server status..."
curl -s "$URL/" | python3 -m json.tool

echo -e "\n2. Testing search for 'Claude'..."
curl -X POST "$URL/mcp" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"search_entities","arguments":{"query":"Claude","limit":5}},"id":1}' \
  -s | python3 -m json.tool | head -50

echo -e "\n3. Testing search for 'AI Garden'..."
curl -X POST "$URL/mcp" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"search_entities","arguments":{"query":"AI Garden","limit":3}},"id":2}' \
  -s | python3 -m json.tool | head -50

echo -e "\n4. Testing get specific entity..."
curl -X POST "$URL/mcp" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"get_entity","arguments":{"name":"Julian Crespi"}},"id":3}' \
  -s | python3 -m json.tool | head -50
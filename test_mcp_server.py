#!/usr/bin/env python3
"""
Test script for MCP server
"""

import asyncio
import aiohttp
import json
import sys

async def test_mcp_server():
    """Test the MCP server endpoints"""
    base_url = "http://localhost:8081"

    async with aiohttp.ClientSession() as session:
        # Test health endpoint
        print("Testing /health endpoint...")
        async with session.get(f"{base_url}/health") as resp:
            if resp.status == 200:
                print("✅ Health check passed")
            else:
                print(f"❌ Health check failed: {resp.status}")

        # Test root endpoint
        print("\nTesting / endpoint...")
        async with session.get(f"{base_url}/") as resp:
            if resp.status == 200:
                data = await resp.json()
                print(f"✅ Root endpoint: {json.dumps(data, indent=2)}")
            else:
                print(f"❌ Root endpoint failed: {resp.status}")

        # Test MCP initialize
        print("\nTesting MCP initialize...")
        mcp_request = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {}
            },
            "id": 1
        }

        async with session.post(f"{base_url}/mcp", json=mcp_request) as resp:
            if resp.status == 200:
                data = await resp.json()
                print(f"✅ MCP initialize: {json.dumps(data, indent=2)}")
            else:
                print(f"❌ MCP initialize failed: {resp.status}")

        # Test MCP tools/list
        print("\nTesting MCP tools/list...")
        mcp_request = {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "params": {},
            "id": 2
        }

        async with session.post(f"{base_url}/mcp", json=mcp_request) as resp:
            if resp.status == 200:
                data = await resp.json()
                print(f"✅ MCP tools/list: Found {len(data['result']['tools'])} tools")
                for tool in data['result']['tools']:
                    print(f"  - {tool['name']}: {tool['description']}")
            else:
                print(f"❌ MCP tools/list failed: {resp.status}")

        # Test MCP search_entities
        print("\nTesting MCP search_entities...")
        mcp_request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "search_entities",
                "arguments": {
                    "query": "AI Garden",
                    "limit": 3
                }
            },
            "id": 3
        }

        async with session.post(f"{base_url}/mcp", json=mcp_request) as resp:
            if resp.status == 200:
                data = await resp.json()
                content = json.loads(data['result']['content'][0]['text'])
                print(f"✅ MCP search_entities: Found {content['count']} entities")
                print(f"   {json.dumps(content, indent=2)}")
            else:
                print(f"❌ MCP search_entities failed: {resp.status}")

if __name__ == "__main__":
    print("MCP Server Test Suite")
    print("=" * 50)
    asyncio.run(test_mcp_server())
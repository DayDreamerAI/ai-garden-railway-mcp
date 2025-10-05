#!/usr/bin/env python3
"""
Test Suite for Daydreamer Railway MCP Memory Server
Validates all tools tier-by-tier for production deployment.

Test Tiers:
- Tier 1: Core Operations (5 tools)
- Tier 2: Conversation Tools (4 tools)
- Tier 3: Advanced Search (3 tools)

Created: October 5, 2025
"""

import asyncio
import json
import aiohttp
import os
from dotenv import load_dotenv
from typing import Dict, Any, List
from datetime import datetime

load_dotenv()

# Configuration
BASE_URL = os.getenv("RAILWAY_SERVER_URL", "http://localhost:8080")
TEST_MODE = os.getenv("TEST_MODE", "local")  # local or railway

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'

class RailwayMCPTester:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session_id = None
        self.sse_session = None
        self.message_endpoint = None
        self.test_results = []

    async def connect_sse(self):
        """Establish SSE connection"""
        print(f"{Colors.BLUE}📡 Connecting to SSE endpoint...{Colors.RESET}")

        try:
            self.sse_session = aiohttp.ClientSession()
            response = await self.sse_session.get(f"{self.base_url}/sse")

            # Read endpoint event
            async for line in response.content:
                line_str = line.decode('utf-8').strip()

                if line_str.startswith('event: endpoint'):
                    continue
                elif line_str.startswith('data: '):
                    endpoint_uri = line_str[6:]
                    self.message_endpoint = f"{self.base_url}{endpoint_uri}"
                    self.session_id = endpoint_uri.split('session_id=')[1]
                    print(f"{Colors.GREEN}✅ SSE connected - Session: {self.session_id[:8]}...{Colors.RESET}")
                    print(f"{Colors.BLUE}📍 Message endpoint: {self.message_endpoint}{Colors.RESET}")
                    return True

        except Exception as e:
            print(f"{Colors.RED}❌ SSE connection failed: {e}{Colors.RESET}")
            return False

    async def send_mcp_request(self, method: str, params: Dict = None) -> Dict:
        """Send MCP JSON-RPC request"""
        request_id = f"test-{datetime.now().timestamp()}"

        payload = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params or {}
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(self.message_endpoint, json=payload) as response:
                return await response.json()

    async def test_initialize(self):
        """Test 1: Initialize MCP connection"""
        print(f"\n{Colors.YELLOW}🔧 Test 1: Initialize MCP Connection{Colors.RESET}")

        try:
            result = await self.send_mcp_request("initialize", {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "railway-test-client",
                    "version": "1.0.0"
                }
            })

            if result.get("result"):
                server_info = result["result"].get("serverInfo", {})
                print(f"{Colors.GREEN}✅ Server initialized: {server_info.get('name')} v{server_info.get('version')}{Colors.RESET}")
                print(f"   Features: {server_info.get('features', {})}")
                self.test_results.append(("initialize", True, server_info))
                return True
            else:
                print(f"{Colors.RED}❌ Initialize failed: {result}{Colors.RESET}")
                self.test_results.append(("initialize", False, result))
                return False

        except Exception as e:
            print(f"{Colors.RED}❌ Initialize error: {e}{Colors.RESET}")
            self.test_results.append(("initialize", False, str(e)))
            return False

    async def test_tools_list(self):
        """Test 2: List available tools"""
        print(f"\n{Colors.YELLOW}🔧 Test 2: List Available Tools{Colors.RESET}")

        try:
            result = await self.send_mcp_request("tools/list")

            if result.get("result"):
                tools = result["result"].get("tools", [])
                print(f"{Colors.GREEN}✅ Found {len(tools)} tools:{Colors.RESET}")
                for tool in tools:
                    print(f"   • {tool['name']}: {tool['description']}")

                self.test_results.append(("tools/list", True, {"count": len(tools)}))
                return True
            else:
                print(f"{Colors.RED}❌ Tools list failed: {result}{Colors.RESET}")
                self.test_results.append(("tools/list", False, result))
                return False

        except Exception as e:
            print(f"{Colors.RED}❌ Tools list error: {e}{Colors.RESET}")
            self.test_results.append(("tools/list", False, str(e)))
            return False

    # =================== TIER 1: CORE TOOLS TESTS ===================

    async def test_search_nodes(self):
        """Test 3: Search nodes by name"""
        print(f"\n{Colors.YELLOW}🔧 Test 3: Search Nodes (Exact Name Lookup){Colors.RESET}")

        try:
            result = await self.send_mcp_request("tools/call", {
                "name": "search_nodes",
                "arguments": {
                    "names": ["Julian Crespi", "Claude (Daydreamer Conversations)"]
                }
            })

            if result.get("result"):
                content = json.loads(result["result"]["content"][0]["text"])
                entities = content.get("entities", [])

                print(f"{Colors.GREEN}✅ Found {len(entities)} entities{Colors.RESET}")
                for entity in entities:
                    print(f"   • {entity.get('e.name')} ({entity.get('e.entityType')})")
                    obs = entity.get('e.observations', [])
                    print(f"     Observations: {len(obs)}")

                self.test_results.append(("search_nodes", True, {"count": len(entities)}))
                return True
            else:
                print(f"{Colors.RED}❌ Search nodes failed: {result}{Colors.RESET}")
                self.test_results.append(("search_nodes", False, result))
                return False

        except Exception as e:
            print(f"{Colors.RED}❌ Search nodes error: {e}{Colors.RESET}")
            self.test_results.append(("search_nodes", False, str(e)))
            return False

    async def test_memory_stats(self):
        """Test 4: Get memory statistics"""
        print(f"\n{Colors.YELLOW}🔧 Test 4: Memory Statistics{Colors.RESET}")

        try:
            result = await self.send_mcp_request("tools/call", {
                "name": "memory_stats",
                "arguments": {}
            })

            if result.get("result"):
                content = json.loads(result["result"]["content"][0]["text"])
                stats = content.get("graph_statistics", {})

                print(f"{Colors.GREEN}✅ Memory Statistics:{Colors.RESET}")
                print(f"   • Entities: {stats.get('entities', 0)}")
                print(f"   • Relationships: {stats.get('relationships', 0)}")
                print(f"   • Chunks: {stats.get('chunks', 0)}")
                print(f"   • Conversation Sessions: {stats.get('conversation_sessions', 0)}")
                print(f"   • Observation Nodes: {stats.get('observation_nodes', 0)}")
                print(f"   • V6 Features: {content.get('v6_features', {})}")

                self.test_results.append(("memory_stats", True, stats))
                return True
            else:
                print(f"{Colors.RED}❌ Memory stats failed: {result}{Colors.RESET}")
                self.test_results.append(("memory_stats", False, result))
                return False

        except Exception as e:
            print(f"{Colors.RED}❌ Memory stats error: {e}{Colors.RESET}")
            self.test_results.append(("memory_stats", False, str(e)))
            return False

    async def test_create_entities(self):
        """Test 5: Create test entity"""
        print(f"\n{Colors.YELLOW}🔧 Test 5: Create Test Entity{Colors.RESET}")

        timestamp = datetime.now().isoformat()
        test_entity = {
            "name": f"Railway Test Entity {timestamp}",
            "entityType": "test",
            "observations": [
                "Created during Railway MCP server validation",
                f"Test timestamp: {timestamp}",
                "Validates entity creation via SSE transport"
            ]
        }

        try:
            result = await self.send_mcp_request("tools/call", {
                "name": "create_entities",
                "arguments": {
                    "entities": [test_entity]
                }
            })

            if result.get("result"):
                content = json.loads(result["result"]["content"][0]["text"])
                created = content.get("created_entities", [])

                print(f"{Colors.GREEN}✅ Created {len(created)} entity:{Colors.RESET}")
                for entity_name in created:
                    print(f"   • {entity_name}")

                self.test_results.append(("create_entities", True, {"created": created}))
                return True
            else:
                print(f"{Colors.RED}❌ Create entities failed: {result}{Colors.RESET}")
                self.test_results.append(("create_entities", False, result))
                return False

        except Exception as e:
            print(f"{Colors.RED}❌ Create entities error: {e}{Colors.RESET}")
            self.test_results.append(("create_entities", False, str(e)))
            return False

    async def test_add_observations(self):
        """Test 6: Add observations to existing entity"""
        print(f"\n{Colors.YELLOW}🔧 Test 6: Add Observations{Colors.RESET}")

        timestamp = datetime.now().isoformat()

        try:
            result = await self.send_mcp_request("tools/call", {
                "name": "add_observations",
                "arguments": {
                    "entity_name": "Julian Crespi",
                    "observations": [
                        f"Test observation added via Railway MCP at {timestamp}",
                        "Validates observation addition via SSE transport"
                    ]
                }
            })

            if result.get("result"):
                content = json.loads(result["result"]["content"][0]["text"])

                print(f"{Colors.GREEN}✅ Added observations:{Colors.RESET}")
                print(f"   • Entity: {content.get('entity_name')}")
                print(f"   • Observations added: {content.get('observations_added')}")
                print(f"   • Total observations: {content.get('total_observations')}")

                self.test_results.append(("add_observations", True, content))
                return True
            else:
                print(f"{Colors.RED}❌ Add observations failed: {result}{Colors.RESET}")
                self.test_results.append(("add_observations", False, result))
                return False

        except Exception as e:
            print(f"{Colors.RED}❌ Add observations error: {e}{Colors.RESET}")
            self.test_results.append(("add_observations", False, str(e)))
            return False

    async def test_raw_cypher_query(self):
        """Test 7: Execute raw Cypher query"""
        print(f"\n{Colors.YELLOW}🔧 Test 7: Raw Cypher Query{Colors.RESET}")

        try:
            result = await self.send_mcp_request("tools/call", {
                "name": "raw_cypher_query",
                "arguments": {
                    "query": "MATCH (e:Entity) RETURN e.name, labels(e), e.entityType LIMIT 5",
                    "limit": 5
                }
            })

            if result.get("result"):
                content = json.loads(result["result"]["content"][0]["text"])
                records = content.get("results", [])

                print(f"{Colors.GREEN}✅ Query returned {len(records)} results:{Colors.RESET}")
                for record in records[:3]:
                    print(f"   • {record.get('e.name')} - {record.get('labels(e)')}")

                self.test_results.append(("raw_cypher_query", True, {"count": len(records)}))
                return True
            else:
                print(f"{Colors.RED}❌ Raw Cypher failed: {result}{Colors.RESET}")
                self.test_results.append(("raw_cypher_query", False, result))
                return False

        except Exception as e:
            print(f"{Colors.RED}❌ Raw Cypher error: {e}{Colors.RESET}")
            self.test_results.append(("raw_cypher_query", False, str(e)))
            return False

    async def print_summary(self):
        """Print test summary"""
        print(f"\n{Colors.BLUE}{'='*60}{Colors.RESET}")
        print(f"{Colors.BLUE}TEST SUMMARY{Colors.RESET}")
        print(f"{Colors.BLUE}{'='*60}{Colors.RESET}")

        total = len(self.test_results)
        passed = sum(1 for _, success, _ in self.test_results if success)
        failed = total - passed

        print(f"\nTotal Tests: {total}")
        print(f"{Colors.GREEN}✅ Passed: {passed}{Colors.RESET}")
        if failed > 0:
            print(f"{Colors.RED}❌ Failed: {failed}{Colors.RESET}")

        print(f"\n{Colors.YELLOW}Detailed Results:{Colors.RESET}")
        for test_name, success, data in self.test_results:
            status = f"{Colors.GREEN}✅{Colors.RESET}" if success else f"{Colors.RED}❌{Colors.RESET}"
            print(f"{status} {test_name}")

        print(f"\n{Colors.BLUE}{'='*60}{Colors.RESET}")

        if failed == 0:
            print(f"{Colors.GREEN}🎉 ALL TESTS PASSED! Railway server is ready for deployment.{Colors.RESET}")
        else:
            print(f"{Colors.YELLOW}⚠️  Some tests failed. Review errors above.{Colors.RESET}")

    async def run_tier1_tests(self):
        """Run all Tier 1 (Core) tests"""
        print(f"\n{Colors.BLUE}{'='*60}{Colors.RESET}")
        print(f"{Colors.BLUE}TIER 1: CORE TOOLS VALIDATION{Colors.RESET}")
        print(f"{Colors.BLUE}{'='*60}{Colors.RESET}")

        # Connect
        if not await self.connect_sse():
            return False

        # Run tests
        await self.test_initialize()
        await self.test_tools_list()
        await self.test_search_nodes()
        await self.test_memory_stats()
        await self.test_create_entities()
        await self.test_add_observations()
        await self.test_raw_cypher_query()

        # Summary
        await self.print_summary()

        # Cleanup
        if self.sse_session:
            await self.sse_session.close()

async def main():
    """Main test runner"""
    print(f"{Colors.BLUE}{'='*60}{Colors.RESET}")
    print(f"{Colors.BLUE}DAYDREAMER RAILWAY MCP SERVER - TEST SUITE{Colors.RESET}")
    print(f"{Colors.BLUE}{'='*60}{Colors.RESET}")
    print(f"\nServer URL: {BASE_URL}")
    print(f"Test Mode: {TEST_MODE}")
    print(f"Timestamp: {datetime.now().isoformat()}")

    tester = RailwayMCPTester(BASE_URL)
    await tester.run_tier1_tests()

if __name__ == "__main__":
    asyncio.run(main())

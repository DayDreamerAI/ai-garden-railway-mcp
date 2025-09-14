#!/usr/bin/env python3
"""
MCP (Model Context Protocol) Server for AI Garden
Compliant with MCP specification for OpenAI/Anthropic integration
"""

import os
import sys
import json
import asyncio
from datetime import datetime, timezone, UTC
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from neo4j import GraphDatabase
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# MCP Protocol Constants
MCP_VERSION = "2024-11-05"
SERVER_INFO = {
    "name": "ai-garden-mcp",
    "version": "1.0.0",
    "description": "AI Garden Knowledge Graph MCP Server"
}

# Environment Configuration
NEO4J_URI = os.environ.get('NEO4J_URI')
NEO4J_USERNAME = os.environ.get('NEO4J_USERNAME', 'neo4j')
NEO4J_PASSWORD = os.environ.get('NEO4J_PASSWORD')
BEARER_TOKEN = os.environ.get('RAILWAY_BEARER_TOKEN', '')
PORT = int(os.environ.get('PORT', 8080))

# Debug logging
logger.info(f"Environment check - NEO4J_URI present: {bool(NEO4J_URI)}")
logger.info(f"Environment check - NEO4J_PASSWORD present: {bool(NEO4J_PASSWORD)}")
if NEO4J_URI:
    logger.info(f"NEO4J_URI starts with: {NEO4J_URI[:20]}...")

@dataclass
class MCPRequest:
    """MCP Request structure"""
    jsonrpc: str = "2.0"
    method: str = ""
    params: Dict[str, Any] = None
    id: Optional[int] = None

@dataclass
class MCPResponse:
    """MCP Response structure"""
    jsonrpc: str = "2.0"
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None
    id: Optional[int] = None

@dataclass
class Tool:
    """MCP Tool definition"""
    name: str
    description: str
    inputSchema: Dict[str, Any]

class MCPServer:
    """MCP Protocol Server for AI Garden"""

    def __init__(self):
        self.driver = None
        self.neo4j_connected = False
        self._init_neo4j()

    def _init_neo4j(self):
        """Initialize Neo4j connection"""
        try:
            if NEO4J_URI and NEO4J_PASSWORD:
                self.driver = GraphDatabase.driver(
                    NEO4J_URI,
                    auth=(NEO4J_USERNAME, NEO4J_PASSWORD)
                )
                # Test connection
                with self.driver.session() as session:
                    session.run("RETURN 1")
                self.neo4j_connected = True
                logger.info(f"Connected to Neo4j at {NEO4J_URI}")
            else:
                logger.warning("Neo4j credentials not configured")
        except Exception as e:
            logger.error(f"Neo4j connection failed: {e}")
            self.neo4j_connected = False

    async def handle_initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle initialize request"""
        return {
            "protocolVersion": MCP_VERSION,
            "capabilities": {
                "tools": {},
                "resources": {},
                "prompts": {}
            },
            "serverInfo": SERVER_INFO
        }

    async def handle_tools_list(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """List available tools"""
        tools = [
            Tool(
                name="search_entities",
                description="Search for entities in the AI Garden knowledge graph",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query for entities"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results",
                            "default": 5
                        }
                    },
                    "required": ["query"]
                }
            ),
            Tool(
                name="get_entity",
                description="Get detailed information about a specific entity",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Name of the entity to retrieve"
                        }
                    },
                    "required": ["name"]
                }
            ),
            Tool(
                name="get_relationships",
                description="Get relationships for a specific entity",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "entity_name": {
                            "type": "string",
                            "description": "Name of the entity"
                        },
                        "relationship_type": {
                            "type": "string",
                            "description": "Optional: filter by relationship type"
                        }
                    },
                    "required": ["entity_name"]
                }
            )
        ]

        return {
            "tools": [asdict(tool) for tool in tools]
        }

    async def handle_tools_call(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool call"""
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        if tool_name == "search_entities":
            return await self.search_entities(arguments)
        elif tool_name == "get_entity":
            return await self.get_entity(arguments)
        elif tool_name == "get_relationships":
            return await self.get_relationships(arguments)
        else:
            raise ValueError(f"Unknown tool: {tool_name}")

    async def search_entities(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Search for entities in the knowledge graph"""
        query = args.get("query", "")
        limit = args.get("limit", 5)

        if self.neo4j_connected and self.driver:
            try:
                with self.driver.session() as session:
                    result = session.run("""
                        MATCH (n:Entity)
                        WHERE toLower(n.name) CONTAINS toLower($search_term)
                        RETURN n.name as name, n.entityType as type,
                               n.observations as observations
                        LIMIT $limit
                    """, search_term=query, limit=limit)

                    entities = []
                    for record in result:
                        entity_data = {
                            "name": record["name"],
                            "type": record["type"]
                        }
                        if record["observations"]:
                            entity_data["observations"] = record["observations"][:3]
                        entities.append(entity_data)

                    return {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps({
                                    "entities": entities,
                                    "query": query,
                                    "count": len(entities)
                                }, indent=2)
                            }
                        ]
                    }
            except Exception as e:
                logger.error(f"Search error: {e}")
                return self._mock_search_response(query)
        else:
            return self._mock_search_response(query)

    async def get_entity(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed information about an entity"""
        name = args.get("name", "")

        if self.neo4j_connected and self.driver:
            try:
                with self.driver.session() as session:
                    result = session.run("""
                        MATCH (n:Entity {name: $entity_name})
                        OPTIONAL MATCH (n)-[r]->(related:Entity)
                        RETURN n.name as name, n.entityType as type,
                               n.observations as observations,
                               collect(DISTINCT {
                                   type: type(r),
                                   related: related.name
                               }) as relationships
                    """, entity_name=name)

                    record = result.single()
                    if record:
                        return {
                            "content": [
                                {
                                    "type": "text",
                                    "text": json.dumps({
                                        "name": record["name"],
                                        "type": record["type"],
                                        "observations": record["observations"],
                                        "relationships": record["relationships"]
                                    }, indent=2)
                                }
                            ]
                        }
                    else:
                        return {
                            "content": [
                                {
                                    "type": "text",
                                    "text": f"Entity '{name}' not found"
                                }
                            ]
                        }
            except Exception as e:
                logger.error(f"Get entity error: {e}")
                return self._mock_entity_response(name)
        else:
            return self._mock_entity_response(name)

    async def get_relationships(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get relationships for an entity"""
        entity_name = args.get("entity_name", "")
        relationship_type = args.get("relationship_type")

        if self.neo4j_connected and self.driver:
            try:
                with self.driver.session() as session:
                    if relationship_type:
                        query = """
                            MATCH (n:Entity {name: $entity_name})-[r:`""" + relationship_type + """`]-(related)
                            RETURN type(r) as rel_type,
                                   collect(DISTINCT related.name) as related_entities
                        """
                    else:
                        query = """
                            MATCH (n:Entity {name: $entity_name})-[r]-(related)
                            RETURN type(r) as rel_type,
                                   collect(DISTINCT related.name) as related_entities
                            ORDER BY size(collect(DISTINCT related.name)) DESC
                        """

                    result = session.run(query, entity_name=entity_name)

                    relationships = []
                    for record in result:
                        relationships.append({
                            "type": record["rel_type"],
                            "entities": record["related_entities"]
                        })

                    return {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps({
                                    "entity": entity_name,
                                    "relationships": relationships,
                                    "total_connections": sum(len(r["entities"]) for r in relationships)
                                }, indent=2)
                            }
                        ]
                    }
            except Exception as e:
                logger.error(f"Get relationships error: {e}")
                return self._mock_relationships_response(entity_name)
        else:
            return self._mock_relationships_response(entity_name)

    def _mock_search_response(self, query: str) -> Dict[str, Any]:
        """Return mock search results when Neo4j is not connected"""
        mock_entities = []
        if "ai" in query.lower() or "garden" in query.lower():
            mock_entities = [
                {"name": "AI Garden", "type": "strategic_initiative"},
                {"name": "Claude (Daydreamer Conversations)", "type": "ai_agent"},
                {"name": "ChatGPT (AI Garden Agent)", "type": "ai_agent"}
            ]

        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps({
                        "entities": mock_entities,
                        "query": query,
                        "count": len(mock_entities),
                        "note": "Mock data - Neo4j not connected"
                    }, indent=2)
                }
            ]
        }

    def _mock_entity_response(self, name: str) -> Dict[str, Any]:
        """Return mock entity data when Neo4j is not connected"""
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps({
                        "name": name,
                        "type": "mock",
                        "note": "Mock data - Neo4j not connected"
                    }, indent=2)
                }
            ]
        }

    def _mock_relationships_response(self, entity_name: str) -> Dict[str, Any]:
        """Return mock relationship data when Neo4j is not connected"""
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps({
                        "entity": entity_name,
                        "relationships": [],
                        "note": "Mock data - Neo4j not connected"
                    }, indent=2)
                }
            ]
        }

    async def handle_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Main request handler"""
        request = MCPRequest(**request_data)

        try:
            if request.method == "initialize":
                result = await self.handle_initialize(request.params or {})
            elif request.method == "tools/list":
                result = await self.handle_tools_list(request.params or {})
            elif request.method == "tools/call":
                result = await self.handle_tools_call(request.params or {})
            else:
                raise ValueError(f"Unknown method: {request.method}")

            return asdict(MCPResponse(
                jsonrpc="2.0",
                result=result,
                id=request.id
            ))
        except Exception as e:
            logger.error(f"Request handling error: {e}")
            return asdict(MCPResponse(
                jsonrpc="2.0",
                error={
                    "code": -32603,
                    "message": str(e)
                },
                id=request.id
            ))

async def handle_sse_request(server: MCPServer, request_line: str) -> str:
    """Handle Server-Sent Events request"""
    try:
        request_data = json.loads(request_line)
        response = await server.handle_request(request_data)
        return json.dumps(response)
    except Exception as e:
        logger.error(f"SSE handling error: {e}")
        return json.dumps({
            "jsonrpc": "2.0",
            "error": {
                "code": -32700,
                "message": "Parse error"
            }
        })

async def main():
    """Main server loop"""
    server = MCPServer()

    logger.info(f"Starting MCP Server on port {PORT}")
    logger.info(f"Neo4j connected: {server.neo4j_connected}")
    logger.info("MCP Server ready for connections")

    # For Railway deployment, we need to handle HTTP/SSE
    from aiohttp import web

    async def handle_mcp(request):
        """Handle MCP requests over HTTP/SSE"""
        if request.headers.get('Accept') == 'text/event-stream':
            # SSE mode
            response = web.StreamResponse()
            response.headers['Content-Type'] = 'text/event-stream'
            response.headers['Cache-Control'] = 'no-cache'
            response.headers['Access-Control-Allow-Origin'] = '*'
            await response.prepare(request)

            async for line in request.content:
                if line:
                    result = await handle_sse_request(server, line.decode())
                    await response.write(f"data: {result}\n\n".encode())

            return response
        else:
            # Regular HTTP POST
            data = await request.json()
            result = await server.handle_request(data)
            return web.json_response(result)

    async def health_check(request):
        """Health check endpoint"""
        return web.Response(text="OK")

    async def root_info(request):
        """Root endpoint with server info"""
        return web.json_response({
            "type": "mcp",
            "server": SERVER_INFO,
            "neo4j": "connected" if server.neo4j_connected else "disconnected",
            "timestamp": datetime.now(UTC).isoformat()
        })

    app = web.Application()
    app.router.add_post('/mcp', handle_mcp)
    app.router.add_get('/health', health_check)
    app.router.add_get('/', root_info)

    # Handle CORS
    app.router.add_route('OPTIONS', '/mcp', lambda r: web.Response(
        headers={
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization'
        }
    ))

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()

    logger.info(f"MCP Server listening on http://0.0.0.0:{PORT}")
    logger.info("Endpoints: /mcp (MCP protocol), /health, /")

    # Keep server running
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
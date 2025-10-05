#!/usr/bin/env python3
"""
Minimal MCP Test Server for Custom Connector Validation
Single tool: raw_cypher_query for testing Neo4j connectivity
"""

import os
import json
import asyncio
import logging
from datetime import datetime, UTC
from aiohttp import web
from dotenv import load_dotenv
from neo4j import GraphDatabase

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Environment Configuration
PORT = int(os.environ.get('PORT', 8080))
NEO4J_URI = os.environ.get('NEO4J_URI')
NEO4J_USERNAME = os.environ.get('NEO4J_USERNAME', 'neo4j')
NEO4J_PASSWORD = os.environ.get('NEO4J_PASSWORD')

# MCP Protocol Constants
MCP_VERSION = "2024-11-05"
SERVER_INFO = {
    "name": "daydreamer-memory-test",
    "version": "1.0.0",
    "description": "Minimal test server for Custom Connector validation"
}

# Neo4j driver
driver = None
neo4j_connected = False

async def initialize_neo4j():
    """Initialize Neo4j connection"""
    global driver, neo4j_connected

    if neo4j_connected:
        return True

    try:
        if not NEO4J_URI or not NEO4J_PASSWORD:
            logger.error("❌ NEO4J_URI or NEO4J_PASSWORD not configured")
            return False

        logger.info(f"🔌 Connecting to Neo4j: {NEO4J_URI}")

        driver = GraphDatabase.driver(
            NEO4J_URI,
            auth=(NEO4J_USERNAME, NEO4J_PASSWORD)
        )

        # Test connection
        driver.verify_connectivity()

        neo4j_connected = True
        logger.info("✅ Neo4j connected successfully")
        return True

    except Exception as e:
        logger.error(f"❌ Neo4j connection failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def execute_cypher(query: str, parameters: dict = None, limit: int = 100):
    """Execute Cypher query and return results"""
    if not neo4j_connected:
        raise Exception("Neo4j not connected")

    try:
        with driver.session() as session:
            result = session.run(query, parameters or {})
            records = []

            for record in result[:limit]:
                # Convert record to dict
                record_dict = {}
                for key in record.keys():
                    value = record[key]
                    # Handle Neo4j types
                    if hasattr(value, '__dict__'):
                        record_dict[key] = dict(value)
                    else:
                        record_dict[key] = value

                records.append(record_dict)

            return records

    except Exception as e:
        logger.error(f"❌ Cypher query failed: {e}")
        raise

async def handle_mcp_request(data: dict) -> dict:
    """Handle MCP protocol requests"""
    method = data.get("method", "")
    params = data.get("params", {})
    request_id = data.get("id")

    try:
        if method == "initialize":
            result = {
                "protocolVersion": MCP_VERSION,
                "capabilities": {
                    "tools": {}
                },
                "serverInfo": SERVER_INFO
            }

        elif method == "tools/list":
            result = {
                "tools": [
                    {
                        "name": "raw_cypher_query",
                        "description": "Execute raw Cypher query against Neo4j AuraDB",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "query": {
                                    "type": "string",
                                    "description": "Cypher query to execute"
                                },
                                "parameters": {
                                    "type": "object",
                                    "description": "Query parameters",
                                    "default": {}
                                },
                                "limit": {
                                    "type": "number",
                                    "description": "Maximum number of results",
                                    "default": 100
                                }
                            },
                            "required": ["query"]
                        }
                    }
                ]
            }
            logger.info("📋 Returning 1 tool: raw_cypher_query")

        elif method == "tools/call":
            tool_name = params.get("name")

            if tool_name != "raw_cypher_query":
                raise Exception(f"Unknown tool: {tool_name}")

            # Get parameters
            arguments = params.get("arguments", {})
            query = arguments.get("query")
            query_params = arguments.get("parameters", {})
            limit = arguments.get("limit", 100)

            logger.info(f"🔧 Executing Cypher: {query[:100]}...")

            # Execute query
            records = await execute_cypher(query, query_params, limit)

            # Format response
            result_text = f"Query returned {len(records)} records:\n\n"
            result_text += json.dumps(records, indent=2)

            result = {
                "content": [
                    {
                        "type": "text",
                        "text": result_text
                    }
                ]
            }

        else:
            raise Exception(f"Unknown method: {method}")

        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": result
        }

    except Exception as e:
        logger.error(f"❌ Request failed: {e}")
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": -32603,
                "message": str(e)
            }
        }

async def handle_http_mcp(request):
    """Handle MCP requests over HTTP/SSE"""
    if request.headers.get('Accept') == 'text/event-stream':
        # SSE mode
        response = web.StreamResponse()
        response.headers['Content-Type'] = 'text/event-stream'
        response.headers['Cache-Control'] = 'no-cache'
        response.headers['Access-Control-Allow-Origin'] = '*'
        await response.prepare(request)

        try:
            async for line in request.content:
                if line:
                    data = json.loads(line.decode())
                    result = await handle_mcp_request(data)
                    await response.write(f"data: {json.dumps(result)}\n\n".encode())
        except Exception as e:
            logger.error(f"SSE error: {e}")

        return response
    else:
        # Regular HTTP POST
        data = await request.json()
        result = await handle_mcp_request(data)
        return web.json_response(result)

async def health_check(request):
    """Health check endpoint"""
    return web.json_response({
        "status": "healthy",
        "timestamp": datetime.now(UTC).isoformat(),
        "neo4j_connected": neo4j_connected,
        "version": "1.0.0"
    })

async def root_info(request):
    """Root endpoint"""
    return web.json_response({
        "type": "mcp",
        "server": SERVER_INFO,
        "neo4j_connected": neo4j_connected,
        "neo4j_uri": NEO4J_URI[:30] + "..." if NEO4J_URI else None,
        "timestamp": datetime.now(UTC).isoformat()
    })

async def main():
    """Start HTTP server"""
    app = web.Application()

    # Add routes
    app.router.add_post('/mcp', handle_http_mcp)
    app.router.add_get('/mcp', handle_http_mcp)
    app.router.add_get('/health', health_check)
    app.router.add_get('/', root_info)

    # CORS
    app.router.add_route('OPTIONS', '/mcp', lambda r: web.Response(
        headers={
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization, Accept'
        }
    ))

    # Start server
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()

    logger.info(f"🚀 Minimal MCP Test Server listening on http://0.0.0.0:{PORT}")
    logger.info(f"📊 Neo4j: {NEO4J_URI}")

    # Initialize Neo4j
    await initialize_neo4j()

    # Keep running
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())

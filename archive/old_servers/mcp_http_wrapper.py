#!/usr/bin/env python3
"""
HTTP Wrapper for Daydreamer Semantic Memory MCP Server
Wraps stdio MCP server for Railway deployment with /health endpoint
"""

import os
import sys
import json
import asyncio
import logging
from datetime import datetime, UTC
from aiohttp import web
from dotenv import load_dotenv

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
    "name": "daydreamer-memory-auradb",
    "version": "3.2.0",
    "description": "Daydreamer Memory Sovereignty Architecture - AuraDB Backend"
}

# Import semantic memory server components
# We'll dynamically import to avoid initialization issues
semantic_server = None
server_initialized = False

async def initialize_semantic_server():
    """Initialize the semantic memory server"""
    global semantic_server, server_initialized

    if server_initialized:
        return True

    try:
        # Add parent directory to path to import semantic server
        sys.path.insert(0, os.path.dirname(__file__))

        # Import the module
        import mcp_neo4j_semantic_server_with_consolidation as sem_server
        semantic_server = sem_server

        # Initialize connections
        await sem_server.initialize_connections()

        server_initialized = True
        logger.info("Semantic memory server initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize semantic server: {e}")
        import traceback
        traceback.print_exc()
        return False

async def handle_initialize(params: dict) -> dict:
    """Handle MCP initialize request"""
    success = await initialize_semantic_server()

    return {
        "protocolVersion": MCP_VERSION,
        "capabilities": {
            "tools": {}
        },
        "serverInfo": SERVER_INFO,
        "_meta": {
            "semantic_server_loaded": success,
            "neo4j_uri": NEO4J_URI[:30] + "..." if NEO4J_URI else None
        }
    }

async def handle_tools_list(params: dict) -> dict:
    """Handle tools/list request"""
    if not server_initialized:
        await initialize_semantic_server()

    if semantic_server is None:
        return {"tools": []}

    try:
        # Call the semantic server's handle_list_tools
        tools = await semantic_server.handle_list_tools()

        # Convert Tool objects to dicts
        tools_list = []
        for tool in tools:
            tools_list.append({
                "name": tool.name,
                "description": tool.description,
                "inputSchema": tool.inputSchema
            })

        logger.info(f"Returning {len(tools_list)} tools")
        return {"tools": tools_list}
    except Exception as e:
        logger.error(f"Error listing tools: {e}")
        import traceback
        traceback.print_exc()
        return {"tools": []}

async def handle_tools_call(params: dict) -> dict:
    """Handle tools/call request"""
    if not server_initialized:
        await initialize_semantic_server()

    if semantic_server is None:
        return {
            "content": [{
                "type": "text",
                "text": "Error: Semantic server not initialized"
            }]
        }

    try:
        name = params.get("name")
        arguments = params.get("arguments", {})

        logger.info(f"Calling tool: {name}")

        # Call the semantic server's handle_call_tool
        result = await semantic_server.handle_call_tool(name, arguments)

        # Convert TextContent objects to dicts
        content = []
        for item in result:
            if hasattr(item, 'type') and hasattr(item, 'text'):
                content.append({
                    "type": item.type,
                    "text": item.text
                })
            else:
                content.append(item)

        return {"content": content}
    except Exception as e:
        logger.error(f"Error calling tool {params.get('name')}: {e}")
        import traceback
        traceback.print_exc()
        return {
            "content": [{
                "type": "text",
                "text": f"Error: {str(e)}"
            }]
        }

async def handle_mcp_request(data: dict) -> dict:
    """Route MCP requests to appropriate handlers"""
    method = data.get("method", "")
    params = data.get("params", {})
    request_id = data.get("id")

    # Route to appropriate handler
    if method == "initialize":
        result = await handle_initialize(params)
    elif method == "tools/list":
        result = await handle_tools_list(params)
    elif method == "tools/call":
        result = await handle_tools_call(params)
    else:
        result = {"error": f"Unknown method: {method}"}

    # Return MCP response
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": result
    }

async def handle_http_mcp(request):
    """Handle MCP requests over HTTP/SSE"""
    if request.headers.get('Accept') == 'text/event-stream':
        # SSE mode for Custom Connectors
        response = web.StreamResponse()
        response.headers['Content-Type'] = 'text/event-stream'
        response.headers['Cache-Control'] = 'no-cache'
        response.headers['Access-Control-Allow-Origin'] = '*'
        await response.prepare(request)

        async for line in request.content:
            if line:
                data = json.loads(line.decode())
                result = await handle_mcp_request(data)
                await response.write(f"data: {json.dumps(result)}\n\n".encode())

        return response
    else:
        # Regular HTTP POST
        data = await request.json()
        result = await handle_mcp_request(data)
        return web.json_response(result)

async def health_check(request):
    """Health check endpoint for Railway"""
    # Check if semantic server is initialized
    status = "healthy" if server_initialized else "initializing"

    return web.json_response({
        "status": status,
        "timestamp": datetime.now(UTC).isoformat(),
        "semantic_server": server_initialized,
        "neo4j_configured": bool(NEO4J_URI and NEO4J_PASSWORD)
    })

async def root_info(request):
    """Root endpoint with server info"""
    return web.json_response({
        "type": "mcp",
        "server": SERVER_INFO,
        "semantic_server": server_initialized,
        "neo4j_uri": NEO4J_URI[:30] + "..." if NEO4J_URI else None,
        "timestamp": datetime.now(UTC).isoformat(),
        "endpoints": {
            "/": "Server info",
            "/health": "Health check",
            "/mcp": "MCP protocol (POST JSON-RPC or GET SSE)"
        }
    })

async def main():
    """Start HTTP server"""
    app = web.Application()

    # Add routes
    app.router.add_post('/mcp', handle_http_mcp)
    app.router.add_get('/mcp', handle_http_mcp)  # SSE support
    app.router.add_get('/health', health_check)
    app.router.add_get('/', root_info)

    # CORS for Custom Connectors
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

    logger.info(f"Daydreamer Memory MCP Server listening on http://0.0.0.0:{PORT}")
    logger.info(f"Neo4j: {NEO4J_URI}")
    logger.info("Endpoints: /mcp (MCP protocol), /health, /")
    logger.info("Initializing semantic memory server...")

    # Pre-initialize to catch errors early
    await initialize_semantic_server()

    # Keep server running
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())

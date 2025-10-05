#!/usr/bin/env python3
"""
HTTP Wrapper for Daydreamer Memory MCP Server v5.0
Provides HTTP/SSE transport for Railway deployment with /health endpoint
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
    "version": "5.0.0",
    "description": "Daydreamer Memory Sovereignty Architecture v5.0 - AuraDB Backend"
}

# Import v5.0 memory server
mcp_server_module = None
mcp_app = None
server_ready = False

async def initialize_mcp_server():
    """Initialize the MCP v5.0 server"""
    global mcp_server_module, mcp_app, server_ready

    if server_ready:
        return True

    try:
        # Add current directory to path
        sys.path.insert(0, os.path.dirname(__file__))

        # Import the v5.0 server module
        import daydreamer_mcp_memory_server as mcp_module
        mcp_server_module = mcp_module

        # Get the Server instance
        mcp_app = mcp_module.app

        # Initialize Neo4j connection (from v5.0 server's initialize_connections)
        if hasattr(mcp_module, 'initialize_connections'):
            await mcp_module.initialize_connections()
            logger.info("✅ MCP v5.0 server connections initialized")

        server_ready = True
        logger.info(f"✅ MCP v5.0 server loaded successfully")
        logger.info(f"Neo4j URI: {NEO4J_URI}")

        return True
    except Exception as e:
        logger.error(f"❌ Failed to initialize MCP v5.0 server: {e}")
        import traceback
        traceback.print_exc()
        return False

async def handle_mcp_request(data: dict) -> dict:
    """Route MCP requests through v5.0 server's handlers"""
    if not server_ready:
        await initialize_mcp_server()

    if not mcp_app:
        return {
            "jsonrpc": "2.0",
            "id": data.get("id"),
            "error": {
                "code": -32603,
                "message": "MCP server not initialized"
            }
        }

    try:
        method = data.get("method", "")
        params = data.get("params", {})
        request_id = data.get("id")

        # Handle different MCP methods
        if method == "initialize":
            # Initialize response
            result = {
                "protocolVersion": MCP_VERSION,
                "capabilities": {
                    "tools": {}
                },
                "serverInfo": SERVER_INFO
            }

        elif method == "tools/list":
            # Get tools from v5.0 server
            tools_list = await mcp_server_module.handle_list_tools()

            # Convert Tool objects to dicts
            tools_dicts = []
            for tool in tools_list:
                tools_dicts.append({
                    "name": tool.name,
                    "description": tool.description,
                    "inputSchema": tool.inputSchema
                })

            logger.info(f"📋 Returning {len(tools_dicts)} tools")
            result = {"tools": tools_dicts}

        elif method == "tools/call":
            # Call tool through v5.0 server
            tool_name = params.get("name")
            arguments = params.get("arguments", {})

            logger.info(f"🔧 Calling tool: {tool_name}")

            content_list = await mcp_server_module.handle_call_tool(tool_name, arguments)

            # Convert TextContent objects to dicts
            content_dicts = []
            for item in content_list:
                if hasattr(item, 'type') and hasattr(item, 'text'):
                    content_dicts.append({
                        "type": item.type,
                        "text": item.text
                    })
                else:
                    content_dicts.append(item)

            result = {"content": content_dicts}

        else:
            result = {
                "error": {
                    "code": -32601,
                    "message": f"Unknown method: {method}"
                }
            }

        # Return MCP response
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": result
        }

    except Exception as e:
        logger.error(f"❌ MCP request handling failed: {e}")
        import traceback
        traceback.print_exc()

        return {
            "jsonrpc": "2.0",
            "id": data.get("id"),
            "error": {
                "code": -32603,
                "message": f"Internal error: {str(e)}"
            }
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
    """Health check endpoint for Railway"""
    status = "healthy" if server_ready else "initializing"

    return web.json_response({
        "status": status,
        "timestamp": datetime.now(UTC).isoformat(),
        "mcp_server": server_ready,
        "neo4j_configured": bool(NEO4J_URI and NEO4J_PASSWORD),
        "version": "5.0.0"
    })

async def root_info(request):
    """Root endpoint with server info"""
    return web.json_response({
        "type": "mcp",
        "server": SERVER_INFO,
        "mcp_ready": server_ready,
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

    logger.info(f"🚀 Daydreamer Memory MCP v5.0 HTTP Server listening on http://0.0.0.0:{PORT}")
    logger.info(f"📊 Neo4j: {NEO4J_URI}")
    logger.info("📍 Endpoints: /mcp (MCP protocol), /health, /")
    logger.info("⚙️  Initializing MCP v5.0 server...")

    # Pre-initialize to catch errors early
    success = await initialize_mcp_server()
    if success:
        logger.info("✅ MCP v5.0 server ready")
    else:
        logger.error("❌ MCP v5.0 server initialization failed - some tools may not be available")

    # Keep server running
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())

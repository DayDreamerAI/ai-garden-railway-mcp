#!/usr/bin/env python3
"""
Minimal SSE MCP Server - Dual Endpoint Pattern
/sse - GET endpoint for SSE connection
/messages - POST endpoint for JSON-RPC messages
"""

import os
import json
import asyncio
import logging
from datetime import datetime, UTC
from uuid import uuid4
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
    "description": "Minimal SSE MCP server for Custom Connector validation"
}

# Neo4j driver
driver = None
neo4j_connected = False

# SSE sessions: session_id -> response stream
sse_sessions = {}

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
        return False

async def execute_cypher(query: str, parameters: dict = None, limit: int = 100):
    """Execute Cypher query"""
    if not neo4j_connected:
        raise Exception("Neo4j not connected")

    try:
        with driver.session() as session:
            result = session.run(query, parameters or {})
            records = []

            for record in result[:limit]:
                record_dict = {}
                for key in record.keys():
                    value = record[key]
                    if hasattr(value, '__dict__'):
                        record_dict[key] = dict(value)
                    else:
                        record_dict[key] = value
                records.append(record_dict)

            return records

    except Exception as e:
        logger.error(f"❌ Cypher query failed: {e}")
        raise

async def handle_mcp_request(data: dict, session_id: str):
    """Handle MCP protocol requests"""
    method = data.get("method", "")
    params = data.get("params", {})
    request_id = data.get("id")

    logger.info(f"📨 [{session_id[:8]}] {method}")

    try:
        # Handle notifications (no response)
        if method.startswith("notifications/"):
            return None

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

        elif method == "tools/call":
            tool_name = params.get("name")

            if tool_name != "raw_cypher_query":
                raise Exception(f"Unknown tool: {tool_name}")

            arguments = params.get("arguments", {})
            query = arguments.get("query")
            query_params = arguments.get("parameters", {})
            limit = arguments.get("limit", 100)

            records = await execute_cypher(query, query_params, limit)

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

async def send_sse_message(session_id: str, message: dict):
    """Send message to SSE client"""
    if session_id not in sse_sessions:
        logger.warning(f"⚠️  Session {session_id[:8]} not found")
        return

    response = sse_sessions[session_id]
    try:
        data = json.dumps(message)
        await response.write(f"data: {data}\n\n".encode())
        logger.info(f"📤 [{session_id[:8]}] Sent: {message.get('result', message)[:100] if isinstance(message.get('result'), str) else 'response'}")
    except Exception as e:
        logger.error(f"❌ Failed to send SSE message: {e}")

async def handle_sse(request):
    """SSE endpoint - establish connection and send endpoint info"""
    session_id = str(uuid4())

    logger.info(f"🔗 SSE connection established: {session_id[:8]}")

    # Create SSE response
    response = web.StreamResponse()
    response.headers['Content-Type'] = 'text/event-stream'
    response.headers['Cache-Control'] = 'no-cache'
    response.headers['Access-Control-Allow-Origin'] = '*'
    await response.prepare(request)

    # Store session
    sse_sessions[session_id] = response

    try:
        # Send endpoint event (告诉客户端往哪里POST消息)
        endpoint_message = {
            "jsonrpc": "2.0",
            "method": "endpoint",
            "params": {
                "uri": f"/messages?session_id={session_id}"
            }
        }
        data = json.dumps(endpoint_message)
        await response.write(f"event: endpoint\ndata: {data}\n\n".encode())

        logger.info(f"📍 [{session_id[:8]}] Sent endpoint: /messages?session_id={session_id}")

        # Keep connection alive
        while True:
            await asyncio.sleep(30)  # Send keepalive every 30s
            try:
                await response.write(b": keepalive\n\n")
            except:
                break

    except Exception as e:
        logger.error(f"❌ SSE error: {e}")
    finally:
        # Clean up session
        if session_id in sse_sessions:
            del sse_sessions[session_id]
        logger.info(f"🔌 SSE connection closed: {session_id[:8]}")

    return response

async def handle_post_message(request):
    """POST endpoint - receive JSON-RPC messages"""
    # Get session ID from query params
    session_id = request.query.get('session_id')

    if not session_id or session_id not in sse_sessions:
        return web.json_response({
            "jsonrpc": "2.0",
            "error": {
                "code": -32000,
                "message": "Invalid or expired session"
            }
        }, status=400)

    # Parse JSON-RPC request
    data = await request.json()

    # Handle request
    response = await handle_mcp_request(data, session_id)

    # If notification (no response), return 204
    if response is None:
        return web.Response(status=204)

    # Send response via SSE
    await send_sse_message(session_id, response)

    # Also return via HTTP (some clients expect this)
    return web.json_response(response)

async def health_check(request):
    """Health check endpoint"""
    return web.json_response({
        "status": "healthy",
        "timestamp": datetime.now(UTC).isoformat(),
        "neo4j_connected": neo4j_connected,
        "active_sessions": len(sse_sessions),
        "version": "1.0.0"
    })

async def root_info(request):
    """Root endpoint"""
    return web.json_response({
        "type": "mcp-server",
        "transport": "sse",
        "server": SERVER_INFO,
        "neo4j_connected": neo4j_connected,
        "active_sessions": len(sse_sessions),
        "timestamp": datetime.now(UTC).isoformat(),
        "endpoints": {
            "/": "Server info",
            "/health": "Health check",
            "/sse": "SSE connection (GET)",
            "/messages": "JSON-RPC messages (POST)"
        }
    })

async def main():
    """Start HTTP server"""
    app = web.Application()

    # Add routes
    app.router.add_get('/sse', handle_sse)
    app.router.add_post('/messages', handle_post_message)
    app.router.add_get('/health', health_check)
    app.router.add_get('/', root_info)

    # CORS
    app.router.add_route('OPTIONS', '/sse', lambda r: web.Response(
        headers={
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Accept'
        }
    ))
    app.router.add_route('OPTIONS', '/messages', lambda r: web.Response(
        headers={
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type'
        }
    ))

    # Start server
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()

    logger.info(f"🚀 Minimal SSE MCP Server listening on http://0.0.0.0:{PORT}")
    logger.info(f"📊 Neo4j: {NEO4J_URI}")
    logger.info("📍 Endpoints: /sse (SSE), /messages (POST), /health")

    # Initialize Neo4j
    await initialize_neo4j()

    # Keep running
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())

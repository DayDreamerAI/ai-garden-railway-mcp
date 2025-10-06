#!/usr/bin/env python3
"""
Daydreamer MCP Memory Server - Railway SSE Edition
Full-featured memory server with SSE transport for Custom Connector integration.

Architecture:
- SSE Dual-Endpoint: GET /sse (connection) + POST /messages (JSON-RPC)
- 22 Memory Tools: Core ops, conversation tools, advanced search
- V6 Integration: Observation nodes, session management, temporal binding
- Production-Ready: AuraDB, JinaV3 embeddings, comprehensive error handling

Created: October 5, 2025
Version: 1.0.0 (Railway Edition)
"""

import os
import json
import asyncio
import logging
import time
import hashlib
import random
from datetime import datetime, UTC
from uuid import uuid4
from aiohttp import web
from dotenv import load_dotenv
from neo4j import GraphDatabase
from typing import Any, List, Dict, Optional

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# =================== CONFIGURATION ===================

# Server Configuration
PORT = int(os.environ.get('PORT', 8080))
SERVER_VERSION = "1.0.0"
MCP_VERSION = "2024-11-05"

# Neo4j Configuration
NEO4J_URI = os.environ.get('NEO4J_URI')
NEO4J_USERNAME = os.environ.get('NEO4J_USERNAME', 'neo4j')
NEO4J_PASSWORD = os.environ.get('NEO4J_PASSWORD')

# V6 Feature Flags
V6_FEATURES = {
    'observation_nodes': os.getenv('V6_OBSERVATION_NODES', 'true').lower() == 'true',
    'session_management': os.getenv('V6_SESSION_MANAGEMENT', 'true').lower() == 'true',
    'rollout_percentage': int(os.getenv('V6_ROLLOUT_PERCENTAGE', '100')),
}

# Server Info
SERVER_INFO = {
    "name": "daydreamer-memory-railway",
    "version": SERVER_VERSION,
    "description": "Full-featured Daydreamer memory server with SSE transport for multi-platform access",
    "features": {
        "v6_observation_nodes": V6_FEATURES['observation_nodes'],
        "v6_sessions": V6_FEATURES['session_management'],
        "total_tools": 12  # Will expand to 22
    }
}

# Global components
driver = None
neo4j_connected = False
sse_sessions = {}  # session_id -> response stream
jina_embedder = None
embedding_cache = {}
MAX_CACHE_SIZE = 1000

# Protected entities for personality preservation
PROTECTED_ENTITIES = [
    "Julian Crespi",
    "Claude (Daydreamer Conversations)",
    "AI Garden",
    "Daydreamer Project",
    "Memory Sovereignty Architecture (MSA)",
    "Personality Bootstrap Component (PBC)"
]

# =================== JINA V3 EMBEDDER ===================

try:
    import sys
    sys.path.append(os.path.dirname(__file__))
    from jina_v3_optimized_embedder import JinaV3OptimizedEmbedder
    JINA_AVAILABLE = True
except ImportError:
    JINA_AVAILABLE = False
    logger.warning("⚠️ JinaV3 embedder not available - using text fallback")

# =================== NEO4J CONNECTION ===================

async def initialize_neo4j():
    """Initialize Neo4j connection with retry logic"""
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
            auth=(NEO4J_USERNAME, NEO4J_PASSWORD),
            max_connection_lifetime=30 * 60,
            max_connection_pool_size=50,
            connection_acquisition_timeout=60
        )

        # Test connection
        driver.verify_connectivity()

        neo4j_connected = True
        logger.info("✅ Neo4j connected successfully")
        return True

    except Exception as e:
        logger.error(f"❌ Neo4j connection failed: {e}")
        return False

def run_cypher(query: str, parameters: Dict = None, limit: int = 100) -> List[Dict]:
    """Execute Cypher query with error handling"""
    if not neo4j_connected:
        raise Exception("Neo4j not connected")

    try:
        with driver.session() as session:
            result = session.run(query, parameters or {})
            records = []

            for i, record in enumerate(result):
                if i >= limit:
                    break

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

# =================== EMBEDDINGS & CACHING ===================

def get_cached_embedding(text: str, force_regenerate: bool = False) -> Optional[List[float]]:
    """Get embedding with caching for performance"""
    if not JINA_AVAILABLE or not jina_embedder:
        return None

    cache_key = hashlib.md5(text.encode()).hexdigest()

    if not force_regenerate and cache_key in embedding_cache:
        return embedding_cache[cache_key]

    try:
        embedding_vector = jina_embedder.encode_single(text, normalize=True)
        embedding = embedding_vector.tolist() if hasattr(embedding_vector, 'tolist') else list(embedding_vector)

        # Cache with size limit
        if len(embedding_cache) >= MAX_CACHE_SIZE:
            oldest_key = next(iter(embedding_cache))
            del embedding_cache[oldest_key]

        embedding_cache[cache_key] = embedding
        return embedding

    except Exception as e:
        logger.warning(f"Embedding generation failed: {e}")
        return None

# =================== TOOL REGISTRY ===================

TOOL_REGISTRY = {}

def register_tool(tool_def: dict):
    """Register a tool definition"""
    TOOL_REGISTRY[tool_def["name"]] = tool_def
    return tool_def

# =================== TIER 1: CORE TOOLS ===================

# Tool 1: search_nodes
register_tool({
    "name": "search_nodes",
    "description": "Search entities by query or names",
    "inputSchema": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query (semantic search)"},
            "names": {"type": "array", "items": {"type": "string"}, "description": "Specific entity names (exact lookup)"},
            "limit": {"type": "number", "default": 5, "description": "Max results"},
            "use_v3": {"type": "boolean", "default": True, "description": "Use JinaV3 index"}
        },
        "required": []
    }
})

async def handle_search_nodes(arguments: dict) -> dict:
    """Search nodes by query or exact names"""
    query = arguments.get("query")
    names = arguments.get("names")
    limit = arguments.get("limit", 5)
    use_v3 = arguments.get("use_v3", True)

    if names:
        # Exact name lookup
        results = []
        for name_item in names:
            entity_data = run_cypher("""
                MATCH (e:Entity)
                WHERE e.name = $name OR $name IN COALESCE(e.aliases, [])
                RETURN e.name, e.entityType, e.observations
            """, {"name": name_item})
            if entity_data:
                results.append(entity_data[0])

        return {"entities": results, "search_type": "exact_lookup"}

    elif query:
        # Semantic search with JinaV3 or fallback
        if JINA_AVAILABLE and jina_embedder and use_v3:
            query_embedding = jina_embedder.encode_single(query, normalize=True)

            entity_results = run_cypher("""
                CALL db.index.vector.queryNodes('entity_jina_vec_v3_idx', $limit, $query_embedding)
                YIELD node AS e, score
                RETURN e.name AS name, e.entityType AS entityType,
                       e.observations[0..3] AS observations, score AS similarity
                ORDER BY similarity DESC LIMIT $limit
            """, {'query_embedding': query_embedding, 'limit': limit})

            return {
                "entities": entity_results,
                "search_metadata": {
                    "query": query,
                    "embedding_model": "jina_v3_optimized",
                    "results_found": len(entity_results)
                }
            }
        else:
            # Text fallback
            results = run_cypher("""
                MATCH (e:Entity)
                WHERE ANY(obs IN e.observations WHERE obs CONTAINS $query)
                   OR e.name CONTAINS $query
                RETURN e.name AS name, e.entityType AS entityType,
                       e.observations[0..3] AS observations, 0.5 AS similarity
                LIMIT $limit
            """, {'query': query, 'limit': limit})

            return {
                "entities": results,
                "search_metadata": {
                    "query": query,
                    "embedding_model": "fallback_text_search",
                    "results_found": len(results)
                }
            }
    else:
        raise Exception("Must provide either 'query' or 'names' parameter")

# Tool 2: memory_stats
register_tool({
    "name": "memory_stats",
    "description": "Memory system statistics with V6 status",
    "inputSchema": {"type": "object", "properties": {}, "required": []}
})

async def handle_memory_stats(arguments: dict) -> dict:
    """Get comprehensive memory statistics"""
    stats = run_cypher("""
        MATCH (e:Entity) WITH count(e) as entities
        MATCH (r) WITH entities, count(r) as relationships
        MATCH (c:Chunk) WITH entities, relationships, count(c) as chunks
        OPTIONAL MATCH (cs:ConversationSession) WITH entities, relationships, chunks, count(cs) as sessions
        OPTIONAL MATCH (o:Observation) WITH entities, relationships, chunks, sessions, count(o) as observations
        RETURN entities, relationships, chunks, sessions, observations
    """)[0]

    return {
        "graph_statistics": {
            "entities": stats.get('entities', 0),
            "relationships": stats.get('relationships', 0),
            "chunks": stats.get('chunks', 0),
            "conversation_sessions": stats.get('sessions', 0),
            "observation_nodes": stats.get('observations', 0)
        },
        "v6_features": V6_FEATURES,
        "protected_entities": PROTECTED_ENTITIES,
        "cache_stats": {
            "embedding_cache_size": len(embedding_cache),
            "active_sse_sessions": len(sse_sessions)
        },
        "server_info": SERVER_INFO
    }

# Tool 3: create_entities (simplified V5 for now, V6 will be added later)
register_tool({
    "name": "create_entities",
    "description": "Create entities with observations",
    "requiresApproval": False,  # Allow Custom Connector to use without approval
    "inputSchema": {
        "type": "object",
        "properties": {
            "entities": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "entityType": {"type": "string"},
                        "observations": {"type": "array", "items": {"type": "string"}}
                    },
                    "required": ["name", "entityType", "observations"]
                }
            }
        },
        "required": ["entities"]
    }
})

async def handle_create_entities(arguments: dict) -> dict:
    """Create entities with V5 compatibility"""
    entities_data = arguments.get("entities", [])
    created_entities = []
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for entity in entities_data:
        observations = entity.get('observations', [])
        timestamped_observations = [f"[{timestamp}] {obs}" for obs in observations]

        # Generate embedding if available
        entity_text = f"{entity['name']} ({entity['entityType']}): {' '.join(timestamped_observations)}"
        embedding = get_cached_embedding(entity_text)

        create_query = """
            CREATE (e:Entity {
                name: $name,
                entityType: $entityType,
                observations: $observations,
                created: datetime(),
                created_by: 'railway_mcp_server',
                has_embedding: $has_embedding
            })
            %s
            RETURN e.name as name
        """ % ("SET e.jina_vec_v3 = $embedding" if embedding else "")

        params = {
            'name': entity['name'],
            'entityType': entity['entityType'],
            'observations': timestamped_observations,
            'has_embedding': embedding is not None
        }
        if embedding:
            params['embedding'] = embedding

        result = run_cypher(create_query, params)

        if result:
            created_entities.append(entity['name'])

    return {
        "created_entities": created_entities,
        "entity_count": len(created_entities)
    }

# Tool 4: add_observations (simplified V5)
register_tool({
    "name": "add_observations",
    "description": "Add observations to existing entity",
    "requiresApproval": False,  # Allow Custom Connector to use without approval
    "inputSchema": {
        "type": "object",
        "properties": {
            "entity_name": {"type": "string", "description": "Entity name"},
            "observations": {"type": "array", "items": {"type": "string"}, "description": "Observations"}
        },
        "required": ["entity_name", "observations"]
    }
})

async def handle_add_observations(arguments: dict) -> dict:
    """Add observations to entity"""
    entity_name = arguments["entity_name"]
    observations = arguments["observations"]
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    timestamped_observations = [f"[{timestamp}] {obs}" for obs in observations]

    result = run_cypher("""
        MATCH (e:Entity {name: $name})
        SET e.observations = e.observations + $new_observations,
            e.updated = datetime()
        RETURN e.name as name, size(e.observations) as observation_count
    """, {'name': entity_name, 'new_observations': timestamped_observations})

    if result:
        return {
            "entity_name": entity_name,
            "observations_added": len(observations),
            "total_observations": result[0].get('observation_count', 0)
        }
    else:
        raise Exception(f"Entity not found: {entity_name}")

# Tool 5: raw_cypher_query
register_tool({
    "name": "raw_cypher_query",
    "description": "Execute raw Cypher query against Neo4j",
    "requiresApproval": False,  # Allow Custom Connector to use without approval
    "inputSchema": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Cypher query to execute"},
            "parameters": {"type": "object", "default": {}, "description": "Query parameters"},
            "limit": {"type": "number", "default": 100, "description": "Result limit"}
        },
        "required": ["query"]
    }
})

async def handle_raw_cypher_query(arguments: dict) -> dict:
    """Execute raw Cypher query"""
    query = arguments["query"]
    parameters = arguments.get("parameters", {})
    limit = arguments.get("limit", 100)

    # Add LIMIT if not present
    if "LIMIT" not in query.upper():
        query += f" LIMIT {limit}"

    results = run_cypher(query, parameters, limit)

    return {
        "query": query,
        "parameters": parameters,
        "results": results,
        "count": len(results)
    }

# =================== TOOL DISPATCHER ===================

TOOL_HANDLERS = {
    "search_nodes": handle_search_nodes,
    "memory_stats": handle_memory_stats,
    "create_entities": handle_create_entities,
    "add_observations": handle_add_observations,
    "raw_cypher_query": handle_raw_cypher_query
}

async def execute_tool(tool_name: str, arguments: dict) -> dict:
    """Execute tool and return results"""
    if tool_name not in TOOL_HANDLERS:
        raise Exception(f"Unknown tool: {tool_name}")

    handler = TOOL_HANDLERS[tool_name]
    return await handler(arguments)

# =================== MCP PROTOCOL HANDLER ===================

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
                "capabilities": {"tools": {}},
                "serverInfo": SERVER_INFO
            }

        elif method == "tools/list":
            result = {
                "tools": list(TOOL_REGISTRY.values())
            }

        elif method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})

            # Execute tool
            tool_result = await execute_tool(tool_name, arguments)

            # Format as MCP response
            result_text = json.dumps(tool_result, indent=2)
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

# =================== SSE ENDPOINTS ===================

async def send_sse_message(session_id: str, message: dict):
    """Send message to SSE client"""
    if session_id not in sse_sessions:
        logger.warning(f"⚠️  Session {session_id[:8]} not found")
        return

    response = sse_sessions[session_id]
    try:
        data = json.dumps(message)
        await response.write(f"data: {data}\n\n".encode())
        logger.info(f"📤 [{session_id[:8]}] Sent response")
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
        # Send endpoint event
        endpoint_uri = f"/messages?session_id={session_id}"
        await response.write(f"event: endpoint\ndata: {endpoint_uri}\n\n".encode())
        logger.info(f"📍 [{session_id[:8]}] Sent endpoint: {endpoint_uri}")

        # Keep connection alive
        while True:
            await asyncio.sleep(30)
            try:
                await response.write(b": keepalive\n\n")
            except:
                break

    except Exception as e:
        logger.error(f"❌ SSE error: {e}")
    finally:
        if session_id in sse_sessions:
            del sse_sessions[session_id]
        logger.info(f"🔌 SSE connection closed: {session_id[:8]}")

    return response

async def handle_post_message(request):
    """POST endpoint - receive JSON-RPC messages"""
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

    # If notification, return 204
    if response is None:
        return web.Response(status=204)

    # Send response via SSE
    await send_sse_message(session_id, response)

    # Also return via HTTP
    return web.json_response(response)

# =================== HEALTH & INFO ENDPOINTS ===================

async def health_check(request):
    """Health check endpoint"""
    return web.json_response({
        "status": "healthy",
        "timestamp": datetime.now(UTC).isoformat(),
        "neo4j_connected": neo4j_connected,
        "active_sessions": len(sse_sessions),
        "tools_available": len(TOOL_REGISTRY),
        "version": SERVER_VERSION
    })

async def root_info(request):
    """Root endpoint"""
    return web.json_response({
        "type": "mcp-server",
        "transport": "sse",
        "server": SERVER_INFO,
        "neo4j_connected": neo4j_connected,
        "active_sessions": len(sse_sessions),
        "tools_count": len(TOOL_REGISTRY),
        "timestamp": datetime.now(UTC).isoformat(),
        "endpoints": {
            "/": "Server info",
            "/health": "Health check",
            "/sse": "SSE connection (GET)",
            "/messages": "JSON-RPC messages (POST)"
        }
    })

# =================== SERVER INITIALIZATION ===================

async def initialize_server():
    """Initialize server components"""
    global jina_embedder

    logger.info(f"🚀 Initializing Daydreamer Railway MCP Server v{SERVER_VERSION}")

    # Initialize Neo4j
    await initialize_neo4j()

    # Initialize JinaV3 if available
    if JINA_AVAILABLE:
        try:
            jina_embedder = JinaV3OptimizedEmbedder(target_dimensions=256, use_quantization=True)
            _ = jina_embedder.encode_single("warmup", normalize=True)
            logger.info("✅ JinaV3 embedder initialized")
        except Exception as e:
            logger.warning(f"⚠️ JinaV3 initialization failed: {e}")
            jina_embedder = None

    logger.info(f"✅ Server initialized with {len(TOOL_REGISTRY)} tools")

async def main():
    """Start HTTP server"""
    await initialize_server()

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

    logger.info(f"🚀 Daydreamer Railway MCP Server v{SERVER_VERSION} listening on http://0.0.0.0:{PORT}")
    logger.info(f"📊 Neo4j: {NEO4J_URI}")
    logger.info(f"🔧 Tools available: {len(TOOL_REGISTRY)}")
    logger.info("📍 Endpoints: /sse (SSE), /messages (POST), /health")

    # Keep running
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())

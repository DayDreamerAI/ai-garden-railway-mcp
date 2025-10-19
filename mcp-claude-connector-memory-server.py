#!/usr/bin/env python3
"""
Daydreamer MCP Memory Server - Railway SSE Edition v2.0
V6-compliant memory server with SSE transport for Custom Connector integration.

Architecture:
- SSE Dual-Endpoint: GET /sse (connection) + POST /messages (JSON-RPC)
- V6 MCP Bridge: Canonical observation creation (matches stdio server v5.0)
- V6-Only Operation: V5 deprecated (no observations arrays)
- Production-Ready: AuraDB, JinaV3 embeddings, schema enforcement

Created: October 5, 2025
Version: 2.0.0 (V6 Bridge Migration)
Last Updated: October 18, 2025

V6 Bridge Migration (Oct 18, 2025):
- Adopted V6 MCP Bridge architecture from stdio server v5.0
- V5 functionality completely removed (V6-only operation)
- Added schema enforcement (GraphRAG Phase 1 Foundation)
- Added conversation tools and observation search
- 100% V6 compliance: No timestamp property, canonical Month schema, semantic classification

Previous Fixes (Oct 15, 2025):
- CPU optimization: Platform-aware device selection
- DateTime/Date serialization fixes
- Canonical schema consistency
"""

import os
import sys
import platform
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

# Configure logging first
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import V6 canonical schema (single source of truth for property names)
# Consolidated from v6_schema.py → property_names.py (Oct 13, 2025)
try:
    from property_names import (
        ObservationProperties as OBS,
        EntityProperties as ENT,
        ConversationSessionProperties as SESS,
        NodeLabels as LABELS,
        RelationshipTypes as RELS,
    )
    logger.info("✅ V6 canonical schema imported successfully from property_names.py")
except ImportError as e:
    logger.error(f"❌ CRITICAL: V6 schema not available: {e}")
    # Define fallback constants (should never happen in production)
    class OBS:
        JINA_VEC_V3 = "jina_vec_v3"
        CONVERSATION_ID = "conversation_id"
        CONTENT = "content"
        HAS_EMBEDDING = "has_embedding"
        SEMANTIC_THEME = "semantic_theme"
        EMBEDDING_MODEL = "embedding_model"
        EMBEDDING_DIMENSIONS = "embedding_dimensions"
        EMBEDDING_GENERATED_AT = "embedding_generated_at"
    class RELS:
        ENTITY_HAS_OBSERVATION = "ENTITY_HAS_OBSERVATION"
        CONVERSATION_SESSION_ADDED_OBSERVATION = "CONVERSATION_SESSION_ADDED_OBSERVATION"
        OCCURRED_ON = "OCCURRED_ON"
        PART_OF_MONTH = "PART_OF_MONTH"
        PART_OF_YEAR = "PART_OF_YEAR"

# Load environment variables
load_dotenv()

# =================== CONFIGURATION ===================

# Server Configuration
PORT = int(os.environ.get('PORT', 8080))
SERVER_VERSION = "2.0.0"  # V6 Bridge Migration
MCP_VERSION = "2024-11-05"

# Neo4j Configuration
NEO4J_URI = os.environ.get('NEO4J_URI')
NEO4J_USERNAME = os.environ.get('NEO4J_USERNAME', 'neo4j')
NEO4J_PASSWORD = os.environ.get('NEO4J_PASSWORD')

# Platform Detection for Embedder Device (Oct 15, 2025)
# Railway runs Linux, local development uses MacBook (Darwin/MPS)
PLATFORM = platform.system()
IS_RAILWAY = PLATFORM == "Linux" or os.getenv("RAILWAY_ENVIRONMENT") is not None
EMBEDDER_DEVICE = "cpu" if IS_RAILWAY else "mps"
logger.info(f"🖥️  Platform: {PLATFORM}, Device: {EMBEDDER_DEVICE} (Railway: {IS_RAILWAY})")

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
        "graphrag_phase3": True,  # Leiden communities search
        "total_tools": 8  # Core tools + GraphRAG: search_nodes, memory_stats, create_entities, add_observations, raw_cypher_query, generate_embeddings_batch, graphrag_global_search, graphrag_local_search
    }
}

# Global components
driver = None
neo4j_connected = False
sse_sessions = {}  # session_id -> response stream
jina_embedder = None
embedding_cache = {}
MAX_CACHE_SIZE = 1000
v6_bridge = None  # V6 MCP Bridge (initialized after Neo4j connection)

# Railway Memory Protection (Oct 18, 2025)
MAX_SSE_CONNECTIONS = 5  # Limit concurrent connections to prevent memory accumulation
MEMORY_CIRCUIT_BREAKER_THRESHOLD_GB = 4.5  # Reject requests when memory exceeds this

# Protected entities for personality preservation
PROTECTED_ENTITIES = [
    "Julian Crespi",
    "Claude (Daydreamer Conversations)",
    "AI Garden",
    "Daydreamer Project",
    "Memory Sovereignty Architecture (MSA)",
    "Personality Bootstrap Component (PBC)"
]

# =================== V6 COMPONENTS ===================

# Import V6 MCP Bridge (canonical V6 observation creation from stdio v5.0)
try:
    from v6_mcp_bridge import V6MCPBridge
    V6_BRIDGE_AVAILABLE = True
    logger.info("✅ V6 MCP Bridge imported successfully")
except ImportError as e:
    V6_BRIDGE_AVAILABLE = False
    logger.error(f"❌ CRITICAL: V6 MCP Bridge not available: {e}")

# Import Schema Enforcement (GraphRAG Phase 1 Foundation)
try:
    from schema_enforcement import (
        validate_entities,
        validate_relationships,
        SchemaEnforcementError
    )
    SCHEMA_ENFORCEMENT_AVAILABLE = True
    SCHEMA_ENFORCEMENT_STRICT = os.getenv('SCHEMA_ENFORCEMENT_STRICT', 'false').lower() == 'true'
    logger.info(f"✅ Schema enforcement available (strict mode: {SCHEMA_ENFORCEMENT_STRICT})")
except ImportError:
    SCHEMA_ENFORCEMENT_AVAILABLE = False
    SCHEMA_ENFORCEMENT_STRICT = False
    logger.warning("⚠️ Schema enforcement not available")

# Import Conversation Tools (V6 conversation queries)
try:
    from tools.conversation_tools import ConversationTools
    CONVERSATION_TOOLS_AVAILABLE = True
    logger.info("✅ Conversation tools imported")
except ImportError:
    CONVERSATION_TOOLS_AVAILABLE = False
    logger.warning("⚠️ Conversation tools not available")

# Import Observation Search (MVCM)
try:
    from tools.observation_search import search_observations, format_search_results
    OBSERVATION_SEARCH_AVAILABLE = True
    logger.info("✅ Observation search tools imported")
except ImportError:
    OBSERVATION_SEARCH_AVAILABLE = False
    logger.warning("⚠️ Observation search not available")

# Import GraphRAG Phase 3 Tools (Leiden communities search)
try:
    from mcp_integration import graphrag_global_search_handler, graphrag_local_search_handler, load_feature_flags
    GRAPHRAG_PHASE3_AVAILABLE = True
    logger.info("✅ GraphRAG Phase 3 tools (Leiden communities) imported")
except ImportError as e:
    GRAPHRAG_PHASE3_AVAILABLE = False
    logger.warning(f"⚠️ GraphRAG Phase 3 not available: {e}")

# =================== JINA V3 EMBEDDER ===================

try:
    import sys
    sys.path.append(os.path.dirname(__file__))
    from jina_v3_optimized_embedder import JinaV3OptimizedEmbedder
    JINA_AVAILABLE = True
except ImportError:
    JINA_AVAILABLE = False
    logger.warning("⚠️ JinaV3 embedder not available - using text fallback")

# =================== MEMORY CIRCUIT BREAKER ===================

def check_memory_circuit_breaker() -> tuple[bool, Optional[str]]:
    """
    Memory circuit breaker to prevent Railway OOM crashes

    Created: Oct 18, 2025
    Purpose: Reject requests when memory exceeds 4.5GB threshold

    Returns:
        (is_safe, error_message)
    """
    try:
        import psutil
        process = psutil.Process()
        memory_gb = process.memory_info().rss / (1024**3)

        if memory_gb > MEMORY_CIRCUIT_BREAKER_THRESHOLD_GB:
            # Emergency cleanup
            import gc
            gc.collect()

            # Try to unload JinaV3 model if available
            global jina_embedder
            if jina_embedder and hasattr(jina_embedder, 'unload_model'):
                jina_embedder.unload_model()

            error_msg = f"⚠️ Memory circuit breaker triggered: {memory_gb:.2f}GB > {MEMORY_CIRCUIT_BREAKER_THRESHOLD_GB}GB"
            logger.warning(error_msg)
            return False, error_msg

        return True, None

    except Exception as e:
        logger.error(f"❌ Memory circuit breaker check failed: {e}")
        return True, None  # Fail open - allow request on check failure

# =================== NEO4J CONNECTION ===================

async def initialize_neo4j():
    """Initialize Neo4j connection with retry logic and V6 bridge"""
    global driver, neo4j_connected, v6_bridge

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

        # Initialize V6 MCP Bridge (canonical V6 observation creation)
        if V6_BRIDGE_AVAILABLE:
            try:
                v6_bridge = V6MCPBridge(driver)
                logger.info("✅ V6 MCP Bridge initialized")
            except Exception as e:
                logger.error(f"❌ V6 Bridge initialization failed: {e}")
                v6_bridge = None
        else:
            logger.error("❌ V6 Bridge unavailable - observation creation will fail")
            v6_bridge = None

        return True

    except Exception as e:
        logger.error(f"❌ Neo4j connection failed: {e}")
        return False

def run_cypher(query: str, parameters: Dict = None, limit: int = 100) -> List[Dict]:
    """Execute Cypher query with error handling and proper temporal serialization"""
    if not neo4j_connected:
        raise Exception("Neo4j not connected")

    def serialize_value(value):
        """Serialize Neo4j values to JSON-compatible types"""
        # Handle Neo4j temporal types (DateTime, Date, Time)
        if hasattr(value, 'isoformat'):
            return value.isoformat()
        # Handle Node/Relationship objects
        elif hasattr(value, '__dict__') and hasattr(value, 'items'):
            return {k: serialize_value(v) for k, v in dict(value).items()}
        # Handle lists
        elif isinstance(value, list):
            return [serialize_value(item) for item in value]
        # Handle dictionaries
        elif isinstance(value, dict):
            return {k: serialize_value(v) for k, v in value.items()}
        # Return primitive types as-is
        else:
            return value

    try:
        with driver.session() as session:
            result = session.run(query, parameters or {})
            records = []

            for i, record in enumerate(result):
                if i >= limit:
                    break

                record_dict = {}
                for key in record.keys():
                    record_dict[key] = serialize_value(record[key])
                records.append(record_dict)

            return records

    except Exception as e:
        logger.error(f"❌ Cypher query failed: {e}")
        raise

# =================== EMBEDDINGS & CACHING ===================

def get_cached_embedding(text: str, force_regenerate: bool = False) -> Optional[List[float]]:
    """Get embedding with caching for performance and lazy initialization"""
    global jina_embedder

    if not JINA_AVAILABLE:
        return None

    # Lazy initialization: retry if startup initialization failed (Oct 11, 2025 fix)
    if not jina_embedder:
        try:
            logger.info("🔄 Lazy-initializing JinaV3 embedder...")
            # Use platform-appropriate device (CPU for Railway, MPS for MacBook)
            jina_embedder = JinaV3OptimizedEmbedder(
                target_dimensions=256,
                use_quantization=True,
                device=EMBEDDER_DEVICE
            )
            _ = jina_embedder.encode_single("warmup", normalize=True)
            logger.info(f"✅ JinaV3 embedder lazy-initialized successfully (device={EMBEDDER_DEVICE})")
        except Exception as e:
            logger.warning(f"⚠️ JinaV3 lazy initialization failed: {e}")
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

            # Calculate scan limit in Python (Cypher params are VALUES not EXPRESSIONS)
            # Need VERY high multiplier: 19,263 system artifacts dominate index (93% of nodes)
            # Neo4j Wizard Fix: Use positive label check (e:SemanticEntity) instead of 5 negative checks
            # 1000x multiplier ensures semantic entities appear even if ranked lower than system artifacts
            scan_limit = limit * 1000

            entity_results = run_cypher("""
                CALL db.index.vector.queryNodes('entity_jina_vec_v3_idx', $scan_limit, $query_embedding)
                YIELD node AS e, score
                WHERE e:SemanticEntity
                RETURN e.name AS name, e.entityType AS entityType,
                       e.observations[0..3] AS observations, score AS similarity
                ORDER BY similarity DESC LIMIT $limit
            """, {'query_embedding': query_embedding, 'limit': limit, 'scan_limit': scan_limit})

            return {
                "entities": entity_results,
                "search_metadata": {
                    "query": query,
                    "embedding_model": "jina_v3_optimized",
                    "results_found": len(entity_results)
                }
            }
        else:
            # Text fallback (use SemanticEntity label for efficient filtering)
            results = run_cypher("""
                MATCH (e:SemanticEntity)
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
        MATCH ()-[r]->() WITH entities, count(r) as relationships
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

# Tool 3: create_entities (V6-ONLY - V5 Deprecated Oct 18, 2025)
register_tool({
    "name": "create_entities",
    "description": "Create entities with V6 observation nodes (V6-only, no V5 arrays)",
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
    """
    Create entities with V6 observation nodes (V6-only, Oct 18 2025)

    Uses V6MCPBridge for canonical observation creation.
    No V5 observations arrays created (V5 deprecated).
    Matches stdio server v5.0 architecture.
    """
    global v6_bridge

    entities_data = arguments.get("entities", [])

    results = {
        'v6_compliant': True,
        'v5_deprecated': True,
        'created_entities': [],
        'entity_count': len(entities_data),
        'schema_warnings': []
    }

    try:
        # Schema Enforcement: Validate and normalize entity types (GraphRAG Phase 1)
        if SCHEMA_ENFORCEMENT_AVAILABLE:
            try:
                validated_entities, warnings = validate_entities(entities_data, strict=SCHEMA_ENFORCEMENT_STRICT)
                entities_data = validated_entities  # Use normalized entities
                results['schema_warnings'] = warnings

                if warnings:
                    logger.info(f"Schema validation: {len(warnings)} entities normalized/warned")
                    for warning in warnings[:5]:  # Log first 5
                        logger.warning(f"  - {warning}")

            except SchemaEnforcementError as e:
                # In strict mode, validation errors prevent creation
                logger.error(f"Schema enforcement error (strict mode): {e}")
                results['error'] = f"Schema validation failed: {str(e)}"
                results['schema_enforcement_failed'] = True
                return results

        # V6 Bridge handles all entity creation (canonical V6 implementation)
        if v6_bridge:
            bridge_result = await v6_bridge.create_entities_v6_aware(entities_data)
            results.update(bridge_result)
            return results
        else:
            # If bridge unavailable, this is a configuration error
            raise ValueError("V6 bridge unavailable - cannot create entities. Check V6 initialization.")

    except Exception as e:
        logger.error(f"V6 create_entities error: {e}")
        results['error'] = str(e)
        results['v6_compliant'] = False

    return results

# Tool 4: add_observations (V6-ONLY - V5 Deprecated Oct 18, 2025)
register_tool({
    "name": "add_observations",
    "description": "Add observations to entity with V6 observation nodes (V6-only, no V5 arrays)",
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
    """
    Add observations to entity with V6 observation nodes (V6-only, Oct 18 2025)

    Uses V6MCPBridge for canonical observation creation.
    No V5 observations array append (V5 deprecated).
    Matches stdio server v5.0 architecture.
    """
    global v6_bridge

    entity_name = arguments["entity_name"]
    observations = arguments["observations"]

    results = {
        'v6_compliant': True,
        'v5_deprecated': True,
        'observations_added': len(observations)
    }

    try:
        # V6 bridge handles all observation creation (canonical V6 implementation)
        if v6_bridge:
            bridge_result = await v6_bridge.add_observations_v6_aware(entity_name, observations)
            results.update(bridge_result)
            return results
        else:
            # If bridge unavailable, this is a configuration error
            raise ValueError("V6 bridge unavailable - cannot add observations. Check V6 initialization.")

    except Exception as e:
        logger.error(f"V6 add_observations error: {e}")
        results['error'] = str(e)
        results['v6_compliant'] = False

    return results

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

# Tool 6: generate_embeddings_batch
register_tool({
    "name": "generate_embeddings_batch",
    "description": "Generate 256-dim JinaV3 embeddings for nodes missing them (solves local driver write failures)",
    "requiresApproval": False,
    "inputSchema": {
        "type": "object",
        "properties": {
            "node_type": {
                "type": "string",
                "description": "Node label to process (Observation, ConversationMessage, Entity)",
                "enum": ["Observation", "ConversationMessage", "ConversationSummary", "Entity"]
            },
            "batch_size": {
                "type": "number",
                "default": 50,
                "description": "Number of nodes to process per batch (max 100)"
            },
            "test_mode": {
                "type": "boolean",
                "default": False,
                "description": "If true, only process 10 nodes for validation"
            }
        },
        "required": ["node_type"]
    }
})

async def handle_generate_embeddings_batch(arguments: dict) -> dict:
    """
    Generate embeddings for nodes missing them.

    This solves the AuraDB write failure issue where local Python Neo4j driver
    sessions don't persist embeddings, but Railway MCP Cypher writes work perfectly.
    """
    node_type = arguments["node_type"]
    batch_size = min(arguments.get("batch_size", 50), 100)  # Cap at 100
    test_mode = arguments.get("test_mode", False)

    if not JINA_AVAILABLE or not jina_embedder:
        raise Exception("JinaV3 embedder not available on this server")

    # Determine content property based on node type
    content_property_map = {
        "Observation": "content",
        "ConversationMessage": "text",
        "ConversationSummary": "summary",
        "Entity": "observations"  # Will use first observation
    }

    content_property = content_property_map.get(node_type)
    if not content_property:
        raise Exception(f"Unknown node type: {node_type}")

    # Override batch size for test mode
    if test_mode:
        batch_size = 10
        logger.info("🧪 TEST MODE: Processing only 10 nodes")

    # Fetch nodes without embeddings (canonical schema)
    if node_type == "Entity":
        query = f"""
            MATCH (n:{node_type})
            WHERE n.{ENT.JINA_VEC_V3} IS NULL
              AND size(n.observations) > 0
            RETURN elementId(n) as node_id, n.name as name, n.observations[0] as text_content
            LIMIT {batch_size}
        """
    else:
        query = f"""
            MATCH (n:{node_type})
            WHERE n.{OBS.JINA_VEC_V3} IS NULL
              AND n.{content_property} IS NOT NULL
            RETURN elementId(n) as node_id, n.{content_property} as text_content
            LIMIT {batch_size}
        """

    nodes = run_cypher(query)

    if not nodes:
        return {
            "status": "complete",
            "message": f"No {node_type} nodes need embeddings",
            "processed": 0,
            "failed": 0
        }

    # Process each node
    processed = 0
    failed = 0
    timestamp = datetime.now(UTC).isoformat()

    for node in nodes:
        try:
            node_id = node['node_id']
            text_content = node.get('text_content', '')

            if not text_content or len(text_content.strip()) == 0:
                logger.warning(f"⚠️ Node {node_id} has empty content, skipping")
                failed += 1
                continue

            # Generate embedding
            embedding_vector = jina_embedder.encode_single(text_content, normalize=True)
            embedding = embedding_vector.tolist() if hasattr(embedding_vector, 'tolist') else list(embedding_vector)

            # Validate dimension
            if len(embedding) != 256:
                logger.error(f"❌ Wrong embedding dimension: {len(embedding)} (expected 256)")
                failed += 1
                continue

            # Write via Cypher (canonical schema)
            # Dynamically determine which properties to use based on node type
            jina_prop = ENT.JINA_VEC_V3 if node_type == "Entity" else OBS.JINA_VEC_V3
            has_embedding_prop = ENT.HAS_EMBEDDING if node_type == "Entity" else OBS.HAS_EMBEDDING
            embedding_model_prop = ENT.EMBEDDING_MODEL if node_type == "Entity" else OBS.EMBEDDING_MODEL
            embedding_dims_prop = ENT.EMBEDDING_DIMENSIONS if node_type == "Entity" else OBS.EMBEDDING_DIMENSIONS

            update_query = f"""
                MATCH (n) WHERE elementId(n) = $node_id
                SET n.{jina_prop} = $embedding,
                    n.{embedding_model_prop} = 'jinaai/jina-embeddings-v3',
                    n.{embedding_dims_prop} = 256,
                    n.embedding_version = 'v3.0',
                    n.{has_embedding_prop} = true,
                    n.embedding_updated = $timestamp
                RETURN elementId(n) as updated_id
            """

            result = run_cypher(update_query, {
                'node_id': node_id,
                'embedding': embedding,
                'timestamp': timestamp
            })

            if result:
                processed += 1
                if processed % 10 == 0:
                    logger.info(f"✅ Processed {processed}/{len(nodes)} {node_type} nodes")
            else:
                logger.warning(f"⚠️ No result for node {node_id}, may not exist")
                failed += 1

        except Exception as e:
            logger.error(f"❌ Failed to process node {node.get('node_id', '?')}: {e}")
            failed += 1

    # Count remaining nodes (canonical schema)
    jina_prop = ENT.JINA_VEC_V3 if node_type == "Entity" else OBS.JINA_VEC_V3
    remaining_query = f"""
        MATCH (n:{node_type})
        WHERE n.{jina_prop} IS NULL
        RETURN count(n) as remaining
    """
    remaining_result = run_cypher(remaining_query)
    remaining = remaining_result[0]['remaining'] if remaining_result else 0

    return {
        "status": "success" if failed == 0 else "partial",
        "node_type": node_type,
        "processed": processed,
        "failed": failed,
        "remaining_without_embeddings": remaining,
        "batch_size": batch_size,
        "test_mode": test_mode,
        "message": f"Processed {processed} {node_type} nodes, {failed} failures, {remaining} remaining"
    }

# Tool 7: graphrag_global_search (Leiden communities - Phase 3)
register_tool({
    "name": "graphrag_global_search",
    "description": "Global search for synthesis questions using Leiden community-level knowledge (GraphRAG Phase 3)",
    "requiresApproval": False,
    "inputSchema": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Natural language question for community-level synthesis"},
            "limit": {"type": "number", "default": 5, "description": "Maximum communities to retrieve (1-20)"},
            "min_similarity": {"type": "number", "default": 0.6, "description": "Minimum cosine similarity threshold (0.0-1.0)"}
        },
        "required": ["query"]
    }
})

async def handle_graphrag_global_search(arguments: dict) -> dict:
    """GraphRAG Global Search - Leiden community-level synthesis (Phase 3)"""
    if not GRAPHRAG_PHASE3_AVAILABLE:
        return {"error": "GraphRAG Phase 3 not available"}

    try:
        result = await graphrag_global_search_handler(
            neo4j_driver=driver,
            query=arguments["query"],
            limit=arguments.get("limit", 5),
            min_similarity=arguments.get("min_similarity", 0.6)
        )
        return result
    except Exception as e:
        logger.error(f"GraphRAG global search error: {e}")
        return {"error": str(e)}

# Tool 8: graphrag_local_search (Leiden communities - Phase 3)
register_tool({
    "name": "graphrag_local_search",
    "description": "Local search for entity neighborhood exploration using Leiden communities (GraphRAG Phase 3)",
    "requiresApproval": False,
    "inputSchema": {
        "type": "object",
        "properties": {
            "entity_name": {"type": "string", "description": "Name of entity to explore (supports aliases)"},
            "depth": {"type": "number", "default": 2, "description": "Neighborhood depth: 1 or 2 hops"},
            "hop1_limit": {"type": "number", "default": 20, "description": "Maximum 1-hop neighbors (1-50)"},
            "hop2_limit": {"type": "number", "default": 10, "description": "Maximum 2-hop neighbors (1-30)"},
            "observation_limit": {"type": "number", "default": 10, "description": "Maximum observations per entity (1-20)"}
        },
        "required": ["entity_name"]
    }
})

async def handle_graphrag_local_search(arguments: dict) -> dict:
    """GraphRAG Local Search - Entity neighborhood exploration (Phase 3)"""
    if not GRAPHRAG_PHASE3_AVAILABLE:
        return {"error": "GraphRAG Phase 3 not available"}

    try:
        result = await graphrag_local_search_handler(
            neo4j_driver=driver,
            entity_name=arguments["entity_name"],
            depth=arguments.get("depth", 2),
            hop1_limit=arguments.get("hop1_limit", 20),
            hop2_limit=arguments.get("hop2_limit", 10),
            observation_limit=arguments.get("observation_limit", 10)
        )
        return result
    except Exception as e:
        logger.error(f"GraphRAG local search error: {e}")
        return {"error": str(e)}

# =================== TOOL DISPATCHER ===================

TOOL_HANDLERS = {
    "search_nodes": handle_search_nodes,
    "memory_stats": handle_memory_stats,
    "create_entities": handle_create_entities,
    "add_observations": handle_add_observations,
    "raw_cypher_query": handle_raw_cypher_query,
    "generate_embeddings_batch": handle_generate_embeddings_batch,
    "graphrag_global_search": handle_graphrag_global_search,
    "graphrag_local_search": handle_graphrag_local_search
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
    """
    SSE endpoint - establish connection and send endpoint info

    Railway Optimization (Oct 18, 2025):
    - Connection limit: Max 5 concurrent connections
    - Memory circuit breaker: Reject if memory > 4.5GB
    """
    # Railway Memory Protection: Check connection limit
    if len(sse_sessions) >= MAX_SSE_CONNECTIONS:
        logger.warning(f"⚠️ SSE connection limit reached: {len(sse_sessions)}/{MAX_SSE_CONNECTIONS}")
        return web.Response(
            text="Service at capacity - too many active connections. Please try again later.",
            status=503,
            headers={'Retry-After': '60'}
        )

    # Railway Memory Protection: Check circuit breaker
    is_safe, error_msg = check_memory_circuit_breaker()
    if not is_safe:
        logger.warning(f"⚠️ SSE connection rejected: {error_msg}")
        return web.Response(
            text=f"Service temporarily unavailable - {error_msg}",
            status=503,
            headers={'Retry-After': '30'}
        )

    session_id = str(uuid4())
    logger.info(f"🔗 SSE connection established: {session_id[:8]} ({len(sse_sessions) + 1}/{MAX_SSE_CONNECTIONS})")

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
    """
    POST endpoint - receive JSON-RPC messages

    Railway Optimization (Oct 18, 2025):
    - Memory circuit breaker: Reject if memory > 4.5GB
    """
    # Railway Memory Protection: Check circuit breaker
    is_safe, error_msg = check_memory_circuit_breaker()
    if not is_safe:
        return web.json_response({
            "jsonrpc": "2.0",
            "error": {
                "code": -32000,
                "message": f"Service temporarily unavailable - {error_msg}"
            }
        }, status=503, headers={'Retry-After': '30'})

    session_id = request.query.get('session_id')
    test_mode = request.query.get('test_mode', '').lower() == 'true'

    # Bypass session validation in test mode (for development/testing)
    if not test_mode:
        if not session_id or session_id not in sse_sessions:
            return web.json_response({
                "jsonrpc": "2.0",
                "error": {
                    "code": -32000,
                    "message": "Invalid or expired session"
                }
            }, status=400)

    # Use test session ID if in test mode
    if test_mode and not session_id:
        session_id = "test-session"

    # Parse JSON-RPC request
    data = await request.json()

    # Handle request
    response = await handle_mcp_request(data, session_id)

    # If notification, return 204
    if response is None:
        return web.Response(status=204)

    # Send response via SSE (skip if test mode and no active session)
    if not test_mode or session_id in sse_sessions:
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
            # Use platform-appropriate device (CPU for Railway, MPS for MacBook)
            jina_embedder = JinaV3OptimizedEmbedder(
                target_dimensions=256,
                use_quantization=True,
                device=EMBEDDER_DEVICE
            )
            _ = jina_embedder.encode_single("warmup", normalize=True)
            logger.info(f"✅ JinaV3 embedder initialized (device={EMBEDDER_DEVICE})")
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

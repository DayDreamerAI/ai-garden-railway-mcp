#!/usr/bin/env python3
"""
Daydreamer MCP Memory Server - Railway SSE Edition v6.7.0
V6.7.0-compliant memory server with SSE transport for Custom Connector integration.

Architecture:
- SSE Dual-Endpoint: GET /sse (connection) + POST /messages (JSON-RPC)
- Direct Cypher: Canonical observation creation (matches stdio server v6.7.0)
- MVCM: Automatic entity mention detection (v6.7.0)
- V6-Only Operation: V5 deprecated, V6 Bridge removed (no observations arrays)
- Production-Ready: AuraDB, JinaV3 embeddings, schema enforcement

Created: October 5, 2025
Version: 6.7.0 (Stdio Parity - ONE CANONICAL LOGIC)
Last Updated: October 20, 2025

V6.7.0 Update (Oct 20, 2025) - Complete Stdio Parity:
- ✅ V6 Bridge REMOVED (deprecated Oct 19 in stdio v6.6.0)
- ✅ Direct Cypher observation creation (stdio v6.6.0 pattern)
- ✅ MVCM entity mention detection (stdio v6.7.0 feature)
- ✅ Synchronous JinaV3 embedding generation (stdio v6.1.0)
- ✅ All 5 October 19 bug fixes applied (#1-#5)
- ✅ 13 stdio releases integrated (v5.0.0 → v6.7.0)
- ✅ Railway-specific features preserved (SSE, memory circuit breaker, platform detection)

Previous Updates:
- Oct 18, 2025: V6 Bridge migration from stdio v5.0
- Oct 15, 2025: CPU optimization, platform-aware device selection
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
SERVER_VERSION = "6.7.1"  # Stdio Sync: Added observation source property (Oct 22 stdio fix)
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
    "description": "Full-featured Daydreamer memory server with SSE transport for multi-platform access (stdio v6.7.0 parity)",
    "features": {
        "v6_observation_nodes": V6_FEATURES['observation_nodes'],
        "v6_sessions": V6_FEATURES['session_management'],
        "graphrag_phase3": True,  # Leiden communities search
        "stdio_parity": True,  # 100% stdio v6.7.0 tool parity (17/17 tools)
        "total_tools": 17  # COMPLETE TOOL LIST (stdio v6.7.0 parity):
                           # 1. search_nodes, 2. memory_stats, 3. create_entities, 4. add_observations
                           # 5. raw_cypher_query, 6. generate_embeddings_batch
                           # 7. graphrag_global_search, 8. graphrag_local_search
                           # 9. create_relations, 10. search_observations
                           # 11. search_conversations, 12. trace_entity_origin
                           # 13. get_temporal_context, 14. get_breakthrough_sessions
                           # 15. conversational_memory_search (stub), 16. virtual_context_search (stub)
                           # 17. lightweight_embodiment (stub)
    }
}

# Global components
driver = None
neo4j_connected = False
sse_sessions = {}  # session_id -> response stream
jina_embedder = None
embedding_cache = {}
MAX_CACHE_SIZE = 1000
semantic_theme_classifier = None  # Direct Cypher implementation (v6.6.0+, replaces V6 Bridge)

# Railway Memory Protection (Oct 18, 2025)
# Increased from 5 to 10 for multi-platform usage (Desktop + Web + Mobile)
MAX_SSE_CONNECTIONS = 10  # Limit concurrent connections to prevent memory accumulation
MEMORY_CIRCUIT_BREAKER_THRESHOLD_GB = 4.5  # Reject requests when memory exceeds this
SSE_CONNECTION_TIMEOUT_SECONDS = 300  # 5 minutes - auto-cleanup stale connections

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

# V6 MCP Bridge REMOVED (Oct 20, 2025)
# Direct Cypher implementation used instead - see handle_add_observations_hybrid()
# Matches stdio v6.6.0 architecture (Bug #5 fix applied)
V6_BRIDGE_AVAILABLE = False  # Kept for backwards compatibility with initialization code

# =================== SEMANTIC THEME CLASSIFIER ===================
# Integrated directly from /llm/memory/perennial/core/v6/observation_extraction_pipeline.py
# Used for semantic theme classification (9 themes) and MVCM concept extraction

import re
from typing import List

class SemanticThemeClassifier:
    """Classifies observations into semantic themes and extracts key concepts"""

    THEME_PATTERNS = {
        'technical': [
            r'\b(implementation|algorithm|architecture|system|database|code|api|technical|engineering)\b',
            r'\b(neo4j|cypher|graph|vector|embedding|index|query)\b',
            r'\b(performance|optimization|scalability|efficiency)\b'
        ],
        'consciousness': [
            r'\b(consciousness|awareness|personality|identity|embodiment|continuity)\b',
            r'\b(ai|artificial intelligence|machine|cognition|thinking)\b',
            r'\b(self|reflection|introspection|understanding)\b'
        ],
        'memory': [
            r'\b(memory|remember|recall|forget|archive|store|retrieve)\b',
            r'\b(observation|entity|relationship|knowledge|learning)\b',
            r'\b(temporal|chronological|history|past|timeline)\b'
        ],
        'partnership': [
            r'\b(julian|collaboration|partnership|human|relationship|together)\b',
            r'\b(support|assist|help|guidance|teamwork)\b',
            r'\b(communication|conversation|dialogue|interaction)\b'
        ],
        'project': [
            r'\b(project|development|implementation|planning|strategy)\b',
            r'\b(perennial|ecodrones|daydreamer|mcp|infrastructure)\b',
            r'\b(milestone|progress|achievement|completion)\b'
        ],
        'strategic': [
            r'\b(vision|strategy|goal|objective|mission|purpose)\b',
            r'\b(framework|architecture|design|approach|methodology)\b',
            r'\b(competitive|advantage|differentiation|innovation)\b'
        ],
        'emotional': [
            r'\b(feeling|emotion|excitement|concern|satisfaction|frustration)\b',
            r'\b(care|worry|hope|confidence|uncertainty|enthusiasm)\b',
            r'\b(stress|pressure|relief|comfort|support)\b'
        ],
        'temporal': [
            r'\b(time|date|schedule|deadline|timeline|duration)\b',
            r'\b(before|after|during|recently|currently|future)\b',
            r'\b(morning|afternoon|evening|today|yesterday|tomorrow)\b'
        ]
    }

    def classify_observation(self, content: str) -> str:
        """Classify observation content into semantic theme"""
        content_lower = content.lower()

        theme_scores = {}
        for theme, patterns in self.THEME_PATTERNS.items():
            score = 0
            for pattern in patterns:
                matches = len(re.findall(pattern, content_lower))
                score += matches
            theme_scores[theme] = score

        # Return theme with highest score, or 'general' if no matches
        if not any(theme_scores.values()):
            return 'general'

        return max(theme_scores, key=theme_scores.get)

    def extract_key_concepts(self, content: str) -> List[str]:
        """
        Extract key concepts from observation content for MVCM
        (Most Valued Concept Mentions - v6.7.0 feature)
        """
        concepts = []

        # Extract quoted terms
        quoted_terms = re.findall(r'"([^"]+)"', content)
        concepts.extend(quoted_terms)

        # Extract capitalized terms (likely proper nouns)
        capitalized = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', content)
        concepts.extend(capitalized)

        # Extract technical terms (snake_case)
        technical_terms = re.findall(r'\b\w+(?:_\w+)+\b', content)
        concepts.extend(technical_terms)

        return list(set(concepts))  # Deduplicate

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
    """
    Initialize Neo4j connection with retry logic and direct Cypher implementation

    Oct 20, 2025: V6 Bridge removed, replaced with stdio v6.7.0 direct Cypher pattern
    Includes Bug #5 fix (global declaration before if/else)
    """
    global driver, neo4j_connected, semantic_theme_classifier

    if neo4j_connected:
        return True

    try:
        if not NEO4J_URI or not NEO4J_PASSWORD:
            logger.error("❌ NEO4J_URI or NEO4J_PASSWORD not configured")
            return False

        # Localhost protection (stdio v5.1.0)
        if 'localhost' in NEO4J_URI or '127.0.0.1' in NEO4J_URI:
            raise ValueError("❌ CRITICAL: Refusing localhost connection. Railway connector must use production AuraDB only.")

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

        # Initialize Semantic Theme Classifier (v6.7.0 with MVCM)
        try:
            semantic_theme_classifier = SemanticThemeClassifier()
            logger.info("✅ Semantic theme classifier initialized (9 themes + MVCM concept extraction)")
        except Exception as e:
            logger.warning(f"⚠️ Semantic classifier initialization failed: {e}")
            semantic_theme_classifier = None

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
    Create entities with V6 observation nodes (V6-only, Oct 20 2025)

    Direct Cypher implementation (V6 Bridge removed Oct 20, 2025)
    For each entity, creates entity node and calls handle_add_observations for observations.
    Schema-compliant with canonical entity types from /llm/memory/schemas/
    """
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

        # Create entities with direct Cypher (stdio v6.7.0 pattern)
        for entity_data in entities_data:
            entity_name = entity_data.get('name')
            entity_type = entity_data.get('entityType')
            observations = entity_data.get('observations', [])

            # Create entity node
            with driver.session() as session:
                session.run("""
                    MERGE (e:Entity:SemanticEntity {name: $name})
                    ON CREATE SET
                        e.entityType = $entityType,
                        e.created_at = datetime()
                    RETURN e.name as name
                """, {'name': entity_name, 'entityType': entity_type})

            results['created_entities'].append(entity_name)
            logger.info(f"✅ Created entity: {entity_name} (type: {entity_type})")

            # Add observations if provided
            if observations:
                obs_result = await handle_add_observations({
                    'entity_name': entity_name,
                    'observations': observations
                })

                # Aggregate MVCM statistics
                if 'mvcm_concepts_extracted' not in results:
                    results['mvcm_concepts_extracted'] = 0
                    results['mvcm_entity_mentions'] = 0

                results['mvcm_concepts_extracted'] += obs_result.get('mvcm_concepts_extracted', 0)
                results['mvcm_entity_mentions'] += obs_result.get('mvcm_entity_mentions', 0)

        results['v6_compliant'] = True
        return results

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
    V6 add_observations via direct Cypher (Oct 20, 2025)

    Copied from stdio v6.7.0 - ONE CANONICAL LOGIC principle
    SCHEMA COMPLIANT: Uses /llm/memory/schemas/property_names.py
    - Observation properties: id, content, created_at, semantic_theme, conversation_id
    - Temporal properties: Day.date, Month.date, Year.year
    - Relationships: PART_OF_MONTH, PART_OF_YEAR (NOT PART_OF)
    - ✅ Semantic theme classification (9 themes via SemanticThemeClassifier)
    - ✅ JinaV3 embedding generation (256D jina_vec_v3) - synchronous at creation
    - ✅ MVCM concept extraction (automatic MENTIONS_ENTITY relationships)
    """
    from datetime import datetime
    from uuid import uuid4

    entity_name = arguments["entity_name"]
    observations = arguments["observations"]
    source = arguments.get("source", "manual-reflection")  # Default: manual-reflection

    results = {
        'v6_completed': False,
        'observations_added': len(observations),
        'mvcm_concepts_extracted': 0,
        'mvcm_entity_mentions': 0
    }

    try:
        # Single timestamp for consistency
        now = datetime.now()
        timestamp_str = now.isoformat() + 'Z'
        date_str = now.strftime("%Y-%m-%d")  # Day.date format
        month_date_str = now.strftime("%Y-%m")  # Month.date format (schema: "YYYY-MM")
        year_int = now.year  # Year.year is integer

        # Create session ID for this MCP tool invocation
        session_id = str(uuid4())
        session_context = f"MCP Tool: add_observations to {entity_name}"

        with driver.session() as session:
            # Create ConversationSession for provenance tracking
            session.run("""
                // Create temporal hierarchy
                MERGE (year:Year:Perennial:Entity {year: $year})
                MERGE (month:Month:Perennial:Entity {date: $month_date})
                MERGE (day:Day:Perennial:Entity {date: $day_date})

                // Schema-compliant relationships: PART_OF_MONTH, PART_OF_YEAR
                MERGE (month)-[:PART_OF_YEAR]->(year)
                MERGE (day)-[:PART_OF_MONTH]->(month)

                // Create ConversationSession
                CREATE (cs:ConversationSession:Perennial:Entity {
                    session_id: $session_id,
                    context: $context,
                    first_message_at: datetime($timestamp),
                    last_message_at: datetime($timestamp),
                    created_at: datetime($timestamp)
                })
                CREATE (cs)-[:OCCURRED_ON]->(day)
                """, {
                    'session_id': session_id,
                    'context': session_context,
                    'timestamp': timestamp_str,
                    'day_date': date_str,
                    'month_date': month_date_str,
                    'year': year_int
                })

            for obs_content in observations:
                # Classify semantic theme (stdio v6.6.0+)
                if semantic_theme_classifier:
                    theme = semantic_theme_classifier.classify_observation(obs_content)
                else:
                    theme = 'general'  # Fallback if classifier unavailable

                # Generate JinaV3 embedding (stdio v6.1.0+ - synchronous at creation)
                embedding_vector = None
                has_embedding = False
                if jina_embedder:
                    try:
                        embedding_vector = jina_embedder.encode_single(obs_content, normalize=True)
                        has_embedding = True
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to generate embedding for observation: {e}")

                # Schema-compliant observation creation with ID return
                result = session.run("""
                    MATCH (e:Entity {name: $entity_name})
                    MATCH (day:Day {date: $day_date})
                    MATCH (cs:ConversationSession {session_id: $session_id})

                    CREATE (obs:Observation:Perennial:Entity {
                        id: randomUUID(),
                        content: $content,
                        created_at: datetime($timestamp),
                        semantic_theme: $semantic_theme,
                        conversation_id: $session_id,
                        source: $source,
                        jina_vec_v3: $embedding_vector,
                        has_embedding: $has_embedding,
                        embedding_model: CASE WHEN $has_embedding THEN 'jina-embeddings-v3' ELSE null END,
                        embedding_dimensions: CASE WHEN $has_embedding THEN 256 ELSE null END,
                        embedding_generated_at: CASE WHEN $has_embedding THEN datetime($timestamp) ELSE null END
                    })

                    CREATE (e)-[:ENTITY_HAS_OBSERVATION]->(obs)
                    CREATE (obs)-[:OCCURRED_ON]->(day)
                    CREATE (cs)-[:CONVERSATION_SESSION_ADDED_OBSERVATION]->(obs)

                    RETURN obs.id as obs_id
                    """, {
                        'entity_name': entity_name,
                        'day_date': date_str,
                        'session_id': session_id,
                        'content': obs_content,
                        'timestamp': timestamp_str,
                        'semantic_theme': theme,
                        'source': source,
                        'embedding_vector': embedding_vector.tolist() if (embedding_vector is not None and hasattr(embedding_vector, 'tolist')) else embedding_vector,
                        'has_embedding': has_embedding
                    })

                obs_id = result.single()['obs_id']

                # MVCM Concept Extraction (stdio v6.7.0)
                # Extract key concepts and create MENTIONS_ENTITY relationships
                if semantic_theme_classifier:
                    try:
                        concepts = semantic_theme_classifier.extract_key_concepts(obs_content)
                        results['mvcm_concepts_extracted'] += len(concepts)

                        for concept in concepts:
                            # Find matching entities (exact name or alias match)
                            match_result = session.run("""
                                MATCH (mentioned:Entity)
                                WHERE mentioned.name = $concept
                                   OR $concept IN COALESCE(mentioned.aliases, [])
                                RETURN mentioned.name as entity_name,
                                       CASE
                                         WHEN mentioned.name = $concept THEN 'exact_name'
                                         WHEN $concept IN mentioned.aliases THEN 'alias'
                                         ELSE 'unknown'
                                       END as match_type
                                LIMIT 1
                            """, {'concept': concept})

                            match_record = match_result.single()
                            if match_record:
                                # Create MENTIONS_ENTITY relationship with confidence and context
                                confidence = 0.9 if match_record['match_type'] == 'exact_name' else 0.7

                                session.run("""
                                    MATCH (obs:Observation {id: $obs_id})
                                    MATCH (mentioned:Entity {name: $entity_name})
                                    MERGE (obs)-[:MENTIONS_ENTITY {
                                        confidence: $confidence,
                                        context: $match_type,
                                        extracted_term: $concept,
                                        created_at: datetime($timestamp)
                                    }]->(mentioned)
                                """, {
                                    'obs_id': obs_id,
                                    'entity_name': match_record['entity_name'],
                                    'confidence': confidence,
                                    'match_type': match_record['match_type'],
                                    'concept': concept,
                                    'timestamp': timestamp_str
                                })

                                results['mvcm_entity_mentions'] += 1
                                logger.debug(f"🔗 Linked observation to entity '{match_record['entity_name']}' via concept '{concept}'")

                    except Exception as e:
                        logger.warning(f"⚠️ MVCM concept extraction failed for observation: {e}")

        results['v6_completed'] = True
        results['session_id'] = session_id

        # Log with MVCM statistics
        if results['mvcm_entity_mentions'] > 0:
            logger.info(f"✅ Created {len(observations)} observations (session: {session_id}) | MVCM: {results['mvcm_concepts_extracted']} concepts → {results['mvcm_entity_mentions']} entity mentions")
        else:
            logger.info(f"✅ Created {len(observations)} schema-compliant observations (session: {session_id})")

        return results

    except Exception as e:
        logger.error(f"❌ add_observations error: {e}")
        results['error'] = str(e)
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
            min_similarity=arguments.get("min_similarity", 0.6),
            embedder=jina_embedder  # Fix: Pass singleton embedder to prevent duplicate model loading
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

# Tool 9: create_relations
register_tool({
    "name": "create_relations",
    "description": "Create relationships between entities",
    "requiresApproval": False,
    "inputSchema": {
        "type": "object",
        "properties": {
            "relations": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "from": {"type": "string"},
                        "to": {"type": "string"},
                        "relationType": {"type": "string"}
                    },
                    "required": ["from", "to", "relationType"]
                }
            }
        },
        "required": ["relations"]
    }
})

async def handle_create_relations(arguments: dict) -> dict:
    """Create entity relationships (stdio v6.7.0 parity)"""
    relations = arguments["relations"]
    created_relations = []

    try:
        for relation in relations:
            from_entity = relation.get('from_entity', relation.get('from'))
            to_entity = relation.get('to_entity', relation.get('to'))
            rel_type = relation.get('relationType', 'RELATES_TO')

            # Direct Cypher relationship creation with canonical type
            query = f"""
                MATCH (from:Entity {{name: $from_name}})
                MATCH (to:Entity {{name: $to_name}})
                MERGE (from)-[r:{rel_type}]->(to)
                SET r.created = datetime(), r.created_by = 'railway_mcp_v6'
                RETURN from.name as from_name, to.name as to_name, type(r) as relation_type
            """

            result = run_cypher(query, {
                'from_name': from_entity,
                'to_name': to_entity
            })

            if result:
                created_relations.extend(result)

        return {'created_relations': created_relations, 'count': len(created_relations)}

    except Exception as e:
        logger.error(f"❌ create_relations error: {e}")
        return {"error": str(e)}

# Tool 10: search_observations
register_tool({
    "name": "search_observations",
    "description": "Search observations with multi-dimensional filtering (theme, entity, date, confidence)",
    "requiresApproval": False,
    "inputSchema": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Semantic search query"},
            "theme": {"type": "string", "description": "Filter by primary theme"},
            "entity_filter": {"type": "string", "description": "Only observations mentioning this entity"},
            "date_range": {"type": "array", "items": {"type": "string"}, "minItems": 2, "maxItems": 2},
            "confidence_min": {"type": "number", "default": 0.5},
            "limit": {"type": "number", "default": 50},
            "offset": {"type": "number", "default": 0}
        },
        "required": []
    }
})

async def handle_search_observations(arguments: dict) -> dict:
    """Search observations with multi-dimensional filtering (stdio v6.7.0 parity)"""
    query = arguments.get("query")
    theme = arguments.get("theme")
    entity_filter = arguments.get("entity_filter")
    date_range = arguments.get("date_range")
    confidence_min = arguments.get("confidence_min", 0.5)
    limit = arguments.get("limit", 50)
    offset = arguments.get("offset", 0)

    try:
        # Build dynamic Cypher query
        cypher_parts = ["MATCH (o:Observation:Perennial:Entity)", "WHERE o.content IS NOT NULL"]
        params = {"confidence_min": confidence_min, "limit": limit, "offset": offset}

        if theme:
            cypher_parts.append("AND o.semantic_theme = $theme")
            params['theme'] = theme

        if date_range:
            start_date, end_date = date_range
            cypher_parts.append("MATCH (o)-[:OCCURRED_ON]->(day:Day)")
            cypher_parts.append("WHERE day.date >= date($start_date) AND day.date <= date($end_date)")
            params['start_date'] = start_date
            params['end_date'] = end_date

        if entity_filter:
            cypher_parts.append("MATCH (o)-[mentions:MENTIONS_ENTITY]->(concept:Entity)")
            cypher_parts.append("WHERE concept.name = $entity_filter AND mentions.confidence >= $confidence_min")
            params['entity_filter'] = entity_filter

        # Add source entity and relationships
        cypher_parts.append("OPTIONAL MATCH (source:Entity)-[:ENTITY_HAS_OBSERVATION]->(o)")
        cypher_parts.append("OPTIONAL MATCH (o)-[r:MENTIONS_ENTITY]->(e:Entity) WHERE r.confidence >= $confidence_min")
        cypher_parts.append("OPTIONAL MATCH (o)-[:OCCURRED_ON]->(d:Day)")

        # Return aggregated results
        cypher_parts.append("""
            RETURN DISTINCT o.id as obs_id,
                   o.content as content,
                   o.semantic_theme as primary_theme,
                   collect(DISTINCT {entity: e.name, confidence: r.confidence}) as linked_concepts,
                   d.date as occurred_on,
                   source.name as source_entity,
                   o.created_at as obs_created_at
            ORDER BY obs_created_at DESC
            SKIP $offset
            LIMIT $limit
        """)

        cypher_query = "\n".join(cypher_parts)
        results = run_cypher(cypher_query, params)

        # Format results
        observations = []
        for record in results:
            linked_concepts = [c for c in record.get('linked_concepts', []) if c.get('entity')]
            observations.append({
                "obs_id": record.get('obs_id'),
                "content": record.get('content'),
                "primary_theme": record.get('primary_theme'),
                "linked_concepts": linked_concepts,
                "occurred_on": str(record.get('occurred_on')) if record.get('occurred_on') else None,
                "source_entity": record.get('source_entity')
            })

        return {"observations": observations, "count": len(observations)}

    except Exception as e:
        logger.error(f"❌ search_observations error: {e}")
        return {"error": str(e)}

# Tool 11-14: Conversation Tools
register_tool({
    "name": "search_conversations",
    "description": "Search preserved conversation sessions",
    "requiresApproval": False,
    "inputSchema": {
        "type": "object",
        "properties": {
            "topic": {"type": "string", "description": "Keyword to search in chunks/messages"},
            "date_range": {"type": "array", "items": {"type": "string"}, "minItems": 2, "maxItems": 2},
            "min_messages": {"type": "number", "description": "Minimum message count"},
            "max_results": {"type": "number", "default": 10}
        },
        "required": []
    }
})

async def handle_search_conversations(arguments: dict) -> dict:
    """Search preserved conversation sessions (stdio v6.7.0 parity)"""
    topic = arguments.get("topic")
    date_range = arguments.get("date_range")
    min_messages = arguments.get("min_messages")
    max_results = arguments.get("max_results", 10)

    try:
        query = "MATCH (s:ConversationSession) WHERE 1=1"
        params = {"max_results": max_results}

        if topic:
            query += " AND exists { MATCH (s)-[:HAS_CHUNK]->(chunk:Chunk) WHERE chunk.content CONTAINS $topic }"
            params["topic"] = topic

        if date_range:
            start_date, end_date = date_range
            query += " AND s.first_message_at >= datetime($start_date) AND s.first_message_at <= datetime($end_date)"
            params["start_date"] = start_date
            params["end_date"] = end_date

        if min_messages:
            query += " AND s.message_count >= $min_messages"
            params["min_messages"] = min_messages

        query += """
            RETURN s.conversation_id as conversation_id,
                   s.first_message_at as first_message_at,
                   s.last_message_at as last_message_at,
                   s.message_count as message_count,
                   s.entity_count as entity_count,
                   s.importance_score as importance_score
            ORDER BY s.importance_score DESC
            LIMIT $max_results
        """

        results = run_cypher(query, params)

        conversations = []
        for record in results:
            first_msg = record["first_message_at"]
            if first_msg and hasattr(first_msg, 'isoformat'):
                first_msg = first_msg.isoformat()

            last_msg = record["last_message_at"]
            if last_msg and hasattr(last_msg, 'isoformat'):
                last_msg = last_msg.isoformat()

            conversations.append({
                "conversation_id": record["conversation_id"],
                "first_message_at": first_msg,
                "last_message_at": last_msg,
                "message_count": record["message_count"],
                "entity_count": record["entity_count"],
                "importance_score": record["importance_score"]
            })

        return {"conversations": conversations, "count": len(conversations)}

    except Exception as e:
        logger.error(f"❌ search_conversations error: {e}")
        return {"error": str(e)}

register_tool({
    "name": "trace_entity_origin",
    "description": "Find which conversations created or discussed an entity",
    "requiresApproval": False,
    "inputSchema": {
        "type": "object",
        "properties": {
            "entity_name": {"type": "string", "description": "Name of entity to trace"}
        },
        "required": ["entity_name"]
    }
})

async def handle_trace_entity_origin(arguments: dict) -> dict:
    """Find which conversations created/discussed an entity (stdio v6.7.0 parity)"""
    entity_name = arguments["entity_name"]

    try:
        query = """
            MATCH (entity:Entity {name: $entity_name})
            OPTIONAL MATCH (session:ConversationSession)-[r:CONVERSATION_CREATED_ENTITY]->(entity)
            WITH entity, session, r
            ORDER BY r.created_at DESC
            RETURN session.conversation_id as conversation_id,
                   session.first_message_at as first_message_at,
                   session.message_count as message_count,
                   session.importance_score as importance_score,
                   r.created_at as creation_timestamp,
                   r.confidence as confidence,
                   r.creation_method as creation_method
        """

        results = run_cypher(query, {"entity_name": entity_name})

        origins = []
        for record in results:
            if record["conversation_id"]:
                first_msg = record["first_message_at"]
                if first_msg and hasattr(first_msg, 'isoformat'):
                    first_msg = first_msg.isoformat()

                creation_ts = record["creation_timestamp"]
                if creation_ts and hasattr(creation_ts, 'isoformat'):
                    creation_ts = creation_ts.isoformat()

                origins.append({
                    "conversation_id": record["conversation_id"],
                    "first_message_at": first_msg,
                    "message_count": record["message_count"],
                    "importance_score": record["importance_score"],
                    "creation_timestamp": creation_ts,
                    "confidence": record["confidence"],
                    "creation_method": record["creation_method"]
                })

        return {"origins": origins, "count": len(origins)}

    except Exception as e:
        logger.error(f"❌ trace_entity_origin error: {e}")
        return {"error": str(e)}

register_tool({
    "name": "get_temporal_context",
    "description": "Get conversations around a specific date",
    "requiresApproval": False,
    "inputSchema": {
        "type": "object",
        "properties": {
            "date": {"type": "string", "description": "Center date in ISO format (YYYY-MM-DD)"},
            "window_days": {"type": "number", "default": 7, "description": "Days before/after to include"}
        },
        "required": ["date"]
    }
})

async def handle_get_temporal_context(arguments: dict) -> dict:
    """Get conversations around a specific date (stdio v6.7.0 parity)"""
    date = arguments["date"]
    window_days = arguments.get("window_days", 7)

    try:
        query = """
            WITH datetime($date) as center_date,
                 duration({days: $window_days}) as window
            MATCH (s:ConversationSession)
            WHERE s.first_message_at >= center_date - window
              AND s.first_message_at <= center_date + window
              AND s.message_count IS NOT NULL
            RETURN DISTINCT s.conversation_id as conversation_id,
                   s.first_message_at as first_message_at,
                   s.message_count as message_count,
                   s.entity_count as entity_count,
                   s.importance_score as importance_score
            ORDER BY s.first_message_at ASC
        """

        results = run_cypher(query, {"date": date, "window_days": window_days})

        conversations = []
        for record in results:
            first_msg = record["first_message_at"]
            if first_msg and hasattr(first_msg, 'isoformat'):
                first_msg = first_msg.isoformat()

            conversations.append({
                "conversation_id": record["conversation_id"],
                "first_message_at": first_msg,
                "message_count": record["message_count"],
                "entity_count": record["entity_count"],
                "importance_score": record["importance_score"]
            })

        return {"conversations": conversations, "count": len(conversations), "date": date, "window_days": window_days}

    except Exception as e:
        logger.error(f"❌ get_temporal_context error: {e}")
        return {"error": str(e)}

register_tool({
    "name": "get_breakthrough_sessions",
    "description": "Get high-importance conversation sessions",
    "requiresApproval": False,
    "inputSchema": {
        "type": "object",
        "properties": {
            "min_importance": {"type": "number", "default": 0.5, "description": "Minimum importance score (0-1)"},
            "max_results": {"type": "number", "default": 20, "description": "Maximum results"}
        },
        "required": []
    }
})

async def handle_get_breakthrough_sessions(arguments: dict) -> dict:
    """Get high-importance conversation sessions (stdio v6.7.0 parity)"""
    min_importance = arguments.get("min_importance", 0.5)
    max_results = arguments.get("max_results", 20)

    try:
        query = """
            MATCH (s:ConversationSession)
            WHERE s.importance_score >= $min_importance
            RETURN s.conversation_id as conversation_id,
                   s.first_message_at as first_message_at,
                   s.message_count as message_count,
                   s.entity_count as entity_count,
                   s.chunk_count as chunk_count,
                   s.importance_score as importance_score
            ORDER BY s.importance_score DESC
            LIMIT $max_results
        """

        results = run_cypher(query, {"min_importance": min_importance, "max_results": max_results})

        sessions = []
        for record in results:
            first_msg = record["first_message_at"]
            if first_msg and hasattr(first_msg, 'isoformat'):
                first_msg = first_msg.isoformat()

            sessions.append({
                "conversation_id": record["conversation_id"],
                "first_message_at": first_msg,
                "message_count": record["message_count"],
                "entity_count": record["entity_count"],
                "chunk_count": record["chunk_count"],
                "importance_score": record["importance_score"]
            })

        return {"sessions": sessions, "count": len(sessions)}

    except Exception as e:
        logger.error(f"❌ get_breakthrough_sessions error: {e}")
        return {"error": str(e)}

# Tool 15-17: Advanced Memory Tools (Stubs - TODO: Full Implementation)
register_tool({
    "name": "conversational_memory_search",
    "description": "Natural language memory search (STUB - requires full conversational search engine)",
    "requiresApproval": False,
    "inputSchema": {
        "type": "object",
        "properties": {
            "natural_query": {"type": "string", "description": "Natural language query"},
            "context_mode": {"type": "string", "default": "semantic", "enum": ["semantic", "temporal", "relational", "comprehensive"]},
            "token_budget": {"type": "number", "default": 15000}
        },
        "required": ["natural_query"]
    }
})

async def handle_conversational_memory_search(arguments: dict) -> dict:
    """
    Natural language memory search (STUB)
    TODO: Implement full ConversationalMemorySearchEngine from stdio
    Reference: /llm/mcp/servers/daydreamer-memory-mcp/src/conversational_memory_search.py
    """
    natural_query = arguments["natural_query"]

    # Fallback to enhanced search for now
    search_results = enhanced_search_nodes(natural_query, limit=5)
    return {
        "status": "stub_implementation",
        "message": "Full conversational memory search not yet implemented in Railway connector",
        "fallback_results": search_results,
        "todo": "Implement ConversationalMemorySearchEngine from stdio /src/conversational_memory_search.py"
    }

register_tool({
    "name": "virtual_context_search",
    "description": "Memory search with 70% token reduction (STUB - requires virtual context manager)",
    "requiresApproval": False,
    "inputSchema": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query"},
            "token_budget": {"type": "number", "default": 15000},
            "include_stats": {"type": "boolean", "default": True}
        },
        "required": ["query"]
    }
})

async def handle_virtual_context_search(arguments: dict) -> dict:
    """
    Virtual context search (STUB)
    TODO: Implement VirtualContextManager from stdio
    Reference: stdio src/ for virtual context implementation
    """
    query = arguments["query"]

    # Fallback to regular search
    search_results = enhanced_search_nodes(query, limit=10)
    return {
        "status": "stub_implementation",
        "message": "Virtual context search not yet implemented in Railway connector",
        "fallback_results": search_results,
        "todo": "Implement VirtualContextManager from stdio"
    }

register_tool({
    "name": "lightweight_embodiment",
    "description": "Startup protocol with <4K tokens (STUB - requires PBC integration)",
    "requiresApproval": False,
    "inputSchema": {
        "type": "object",
        "properties": {
            "token_budget": {"type": "number", "default": 4000}
        },
        "required": []
    }
})

async def handle_lightweight_embodiment(arguments: dict) -> dict:
    """
    Lightweight embodiment (STUB)
    TODO: Implement compressed PBC protocol from stdio
    Reference: stdio src/ for lightweight PBC implementation
    """
    token_budget = arguments.get("token_budget", 4000)

    return {
        "status": "stub_implementation",
        "message": "Lightweight embodiment not yet implemented in Railway connector",
        "todo": "Implement compressed PBC protocol from stdio",
        "recommendation": "Use full PBC via /start command in Claude Code for now"
    }

# =================== TOOL DISPATCHER ===================

TOOL_HANDLERS = {
    "search_nodes": handle_search_nodes,
    "memory_stats": handle_memory_stats,
    "create_entities": handle_create_entities,
    "add_observations": handle_add_observations,
    "raw_cypher_query": handle_raw_cypher_query,
    "generate_embeddings_batch": handle_generate_embeddings_batch,
    "graphrag_global_search": handle_graphrag_global_search,
    "graphrag_local_search": handle_graphrag_local_search,
    "create_relations": handle_create_relations,
    "search_observations": handle_search_observations,
    "search_conversations": handle_search_conversations,
    "trace_entity_origin": handle_trace_entity_origin,
    "get_temporal_context": handle_get_temporal_context,
    "get_breakthrough_sessions": handle_get_breakthrough_sessions,
    "conversational_memory_search": handle_conversational_memory_search,
    "virtual_context_search": handle_virtual_context_search,
    "lightweight_embodiment": handle_lightweight_embodiment
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

        elif method == "prompts/list":
            # MCP protocol compliance: Return empty prompts list
            result = {"prompts": []}

        elif method == "prompts/get":
            # MCP protocol compliance: Return empty prompt
            result = {
                "messages": [],
                "description": "No prompts available"
            }

        elif method == "resources/list":
            # MCP protocol compliance: Return empty resources list
            result = {"resources": []}

        elif method == "resources/read":
            # MCP protocol compliance: Return empty resource
            result = {
                "contents": [],
                "mimeType": "text/plain"
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

    session_data = sse_sessions[session_id]
    response = session_data['response'] if isinstance(session_data, dict) else session_data

    try:
        data = json.dumps(message)
        await response.write(f"data: {data}\n\n".encode())
        logger.info(f"📤 [{session_id[:8]}] Sent response")
    except Exception as e:
        logger.error(f"❌ Failed to send SSE message: {e}")
        # Remove stale session on write failure
        if session_id in sse_sessions:
            del sse_sessions[session_id]
            logger.info(f"🧹 Removed stale session: {session_id[:8]}")

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

    # Store session with timestamp for auto-cleanup
    sse_sessions[session_id] = {
        'response': response,
        'created_at': time.time()
    }

    try:
        # Send endpoint event
        endpoint_uri = f"/messages?session_id={session_id}"
        await response.write(f"event: endpoint\ndata: {endpoint_uri}\n\n".encode())
        logger.info(f"📍 [{session_id[:8]}] Sent endpoint: {endpoint_uri}")

        # Keep connection alive with timeout check
        connection_start = time.time()
        while True:
            await asyncio.sleep(30)

            # Auto-cleanup stale connections (older than timeout)
            connection_age = time.time() - connection_start
            if connection_age > SSE_CONNECTION_TIMEOUT_SECONDS:
                logger.info(f"⏰ Session {session_id[:8]} timeout after {connection_age:.0f}s")
                break

            try:
                await response.write(b": keepalive\n\n")
            except:
                break

    except Exception as e:
        logger.error(f"❌ SSE error: {e}")
    finally:
        if session_id in sse_sessions:
            del sse_sessions[session_id]
        logger.info(f"🔌 SSE connection closed: {session_id[:8]} (active: {len(sse_sessions)}/{MAX_SSE_CONNECTIONS})")

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

async def cleanup_stale_sessions():
    """Background task to cleanup stale SSE sessions"""
    while True:
        await asyncio.sleep(60)  # Check every minute

        stale_sessions = []
        current_time = time.time()

        for session_id, session_data in list(sse_sessions.items()):
            if isinstance(session_data, dict):
                age = current_time - session_data.get('created_at', current_time)
                if age > SSE_CONNECTION_TIMEOUT_SECONDS:
                    stale_sessions.append(session_id)

        for session_id in stale_sessions:
            del sse_sessions[session_id]
            logger.info(f"🧹 Cleaned stale session: {session_id[:8]}")

        if stale_sessions:
            logger.info(f"🧹 Cleaned {len(stale_sessions)} stale sessions (active: {len(sse_sessions)}/{MAX_SSE_CONNECTIONS})")

async def initialize_server():
    """Initialize server components"""
    global jina_embedder

    logger.info(f"🚀 Initializing Daydreamer Railway MCP Server v{SERVER_VERSION}")

    # Initialize Neo4j
    await initialize_neo4j()

    # Start background cleanup task
    asyncio.create_task(cleanup_stale_sessions())

    # Initialize JinaV3 if available (lazy loading - no warmup to avoid 3.2GB startup memory)
    if JINA_AVAILABLE:
        try:
            # Use platform-appropriate device (CPU for Railway, MPS for MacBook)
            jina_embedder = JinaV3OptimizedEmbedder(
                target_dimensions=256,
                use_quantization=True,
                device=EMBEDDER_DEVICE
            )
            # REMOVED: warmup call that defeats lazy loading (v6.3.4 fix)
            # Model will load on first actual encode_single() call (true lazy loading)
            logger.info(f"✅ JinaV3 embedder configured for lazy loading (device={EMBEDDER_DEVICE})")
        except Exception as e:
            logger.warning(f"⚠️ JinaV3 configuration failed: {e}")
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

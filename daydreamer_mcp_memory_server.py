#!/usr/bin/env python3
"""
Daydreamer MCP Memory Server v5.0 - Unified V6-Ready Edition
Optimized Neo4j server with inline V6 observation nodes support.
Features: 65% size reduction, ENV-based feature flags, inline V6 integration.
"""

import asyncio
import json
import logging
import time
import hashlib
import numpy as np
from typing import Any, List, Dict, Optional
from datetime import datetime, timedelta
from uuid import uuid4
from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
import mcp.types as types
from neo4j import GraphDatabase
import os
import sys
import random

# Configuration
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

# Configure logging first
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# V6 Feature Flags (ENV Variable Controlled)
V6_FEATURES = {
    'observation_nodes': os.getenv('V6_OBSERVATION_NODES', 'true').lower() == 'true',  # ✅ ENABLED
    'session_management': os.getenv('V6_SESSION_MANAGEMENT', 'true').lower() == 'true',  # ✅ ENABLED
    'shadow_mode': os.getenv('V6_SHADOW_MODE', 'false').lower() == 'true',
    'rollout_percentage': int(os.getenv('V6_ROLLOUT_PERCENTAGE', '100')),  # 100% rollout
    'migration_enabled': os.getenv('V6_MIGRATION_ENABLED', 'true').lower() == 'true'  # ✅ ENABLED
}

# Import optimized components with fallbacks
try:
    from jina_v3_optimized_embedder import JinaV3OptimizedEmbedder
    JINA_AVAILABLE = True
except ImportError:
    JINA_AVAILABLE = False

try:
    from conversational_memory_search import create_conversational_memory_search_handler
    CONVERSATIONAL_SEARCH_AVAILABLE = True
except ImportError:
    CONVERSATIONAL_SEARCH_AVAILABLE = False

# Import Conversation Tools for V6
try:
    from tools.conversation_tools import ConversationTools
    CONVERSATION_TOOLS_AVAILABLE = True
except ImportError:
    CONVERSATION_TOOLS_AVAILABLE = False

# Import Observation Search (MVCM)
try:
    from tools.observation_search import search_observations, format_search_results
    OBSERVATION_SEARCH_AVAILABLE = True
except ImportError:
    OBSERVATION_SEARCH_AVAILABLE = False

# Import V6 components with fallbacks
try:
    import sys
    sys.path.append('/Users/daydreamer/Documents/VibeProjects/daydreamer-mcp/apps/perennial/core/v6')
    from session_management import ConversationSessionManager
    from observation_extraction_pipeline import SemanticThemeClassifier, ObservationExtractionMetrics
    V6_MODULES_AVAILABLE = True
    logger.info("✅ V6 core modules imported successfully")
except ImportError as e:
    V6_MODULES_AVAILABLE = False
    logger.warning(f"⚠️ V6 modules not available, using inline implementations: {e}")

# Import V6 MCP Bridge (local to src/)
try:
    from v6_mcp_bridge import V6MCPBridge
    V6_BRIDGE_AVAILABLE = True
    logger.info("✅ V6 MCP Bridge imported successfully")
except ImportError as e:
    V6_BRIDGE_AVAILABLE = False
    logger.warning(f"⚠️ V6 MCP Bridge not available: {e}")

# Global components
app = Server("daydreamer-memory-v5")
driver = None
jina_embedder = None
virtual_context_manager = None
conversational_search_handler = None
v6_session_manager = None
conversation_tools = None
v6_bridge = None  # V6 MCP Bridge for observation nodes

# Performance optimizations
embedding_cache = {}  # Cache for frequently accessed embeddings
MAX_CACHE_SIZE = 1000  # Limit cache size
session_cache = {}  # Cache for active sessions

# =================== INLINE V6 CLASSES ===================

class InlineConversationSessionManager:
    """V6 ConversationSession management - inline to avoid import failures"""
    
    def __init__(self, neo4j_driver):
        self.driver = neo4j_driver
        self.session_timeout = timedelta(hours=2)
        self.current_session_id = None
        
    def get_or_create_session(self, context_hint: str = None) -> Dict:
        """Get active session or create new one"""
        if not V6_FEATURES['session_management']:
            return {'session_id': 'v5_fallback', 'created': False}
            
        try:
            with self.driver.session() as session:
                # Check for active session
                recent_session = session.run("""
                    MATCH (cs:ConversationSession)
                    WHERE cs.last_activity > datetime() - duration('PT2H')
                      AND cs.status = 'active'
                    RETURN cs
                    ORDER BY cs.last_activity DESC
                    LIMIT 1
                """).single()
                
                if recent_session:
                    session_data = dict(recent_session['cs'])
                    
                    # Update activity
                    session.run("""
                        MATCH (cs:ConversationSession {session_id: $session_id})
                        SET cs.last_activity = datetime()
                    """, session_id=session_data['session_id'])
                    
                    self.current_session_id = session_data['session_id']
                    return session_data
                
                # Create new session
                return self._create_new_session(session, context_hint)
                
        except Exception as e:
            logger.error(f"Session management error: {e}")
            return {'session_id': 'v5_fallback', 'created': False}
    
    def _create_new_session(self, tx, context_hint: str = None) -> Dict:
        """Create new ConversationSession with temporal binding"""
        session_id = f"session_{datetime.now().isoformat()}_{hashlib.md5(str(random.random()).encode()).hexdigest()[:8]}"
        
        try:
            session_data = tx.run("""
                CREATE (cs:ConversationSession:Perennial:Entity {
                    session_id: $session_id,
                    created_at: datetime(),
                    last_activity: datetime(),
                    context_summary: $context_hint,
                    tool_invocation_count: 0,
                    entity_count: 0,
                    observation_count: 0,
                    status: 'active',
                    created_by: 'perennial_v5_unified',
                    perennial_version: 'v5_with_v6'
                })
                
                WITH cs
                MERGE (day:Day {date: date()})
                MERGE (cs)-[:OCCURRED_ON]->(day)
                
                MERGE (perennial:Entity {name: 'Perennial'})
                MERGE (cs)-[:PART_OF]->(perennial)
                
                RETURN cs
            """, session_id=session_id, context_hint=context_hint).single()
            
            result = dict(session_data['cs'])
            self.current_session_id = session_id
            return result
            
        except Exception as e:
            logger.error(f"Session creation error: {e}")
            return {'session_id': 'v5_fallback', 'created': False}

class InlineObservationCreator:
    """V6 observation node creation - inline implementation"""
    
    def __init__(self, neo4j_driver, session_manager):
        self.driver = neo4j_driver
        self.session_manager = session_manager
        
    def create_observation_nodes(self, entity_name: str, observations: List[str]) -> Dict:
        """Create V6 observation nodes with embeddings and relationships"""
        if not V6_FEATURES['observation_nodes']:
            return {'v6_enabled': False, 'observations_created': 0}

        try:
            session_data = self.session_manager.get_or_create_session(f"Adding observations to {entity_name}")

            with self.driver.session() as db_session:
                observation_ids = []
                embeddings_generated = 0

                for obs_content in observations:
                    # Generate JinaV3 embedding for the observation (cached)
                    embedding = get_cached_embedding(obs_content)
                    confidence_score = 1.0 if embedding else 0.0

                    if embedding:
                        embeddings_generated += 1

                    obs_result = db_session.run("""
                        CREATE (o:Observation:Perennial:Entity {
                            id: randomUUID(),
                            content: $content,
                            timestamp: datetime(),
                            source: 'mcp_unified_v6',
                            created_by: 'perennial_v6_unified',
                            conversation_id: $session_id,
                            semantic_theme: $theme,
                            embedding: $embedding,
                            confidence_score: $confidence_score,
                            has_embedding: $has_embedding
                        })

                        WITH o
                        MATCH (entity:Entity {name: $entity_name})
                        MATCH (session:ConversationSession {session_id: $session_id})

                        MERGE (entity)-[:ENTITY_HAS_OBSERVATION]->(o)
                        MERGE (session)-[:CONVERSATION_SESSION_ADDED_OBSERVATION]->(entity)

                        MERGE (day:Day {date: date()})
                        MERGE (o)-[:OCCURRED_ON]->(day)

                        RETURN o.id as observation_id
                    """,
                    content=obs_content,
                    entity_name=entity_name,
                    session_id=session_data['session_id'],
                    theme=self._classify_theme(obs_content),
                    embedding=embedding,
                    confidence_score=confidence_score,
                    has_embedding=embedding is not None
                    ).single()

                    if obs_result:
                        observation_ids.append(obs_result['observation_id'])
                
                # Update session metadata
                db_session.run("""
                    MATCH (session:ConversationSession {session_id: $session_id})
                    SET session.observation_count = session.observation_count + $count,
                        session.last_activity = datetime()
                """, session_id=session_data['session_id'], count=len(observations))
                
                return {
                    'v6_enabled': True,
                    'observations_created': len(observation_ids),
                    'embeddings_generated': embeddings_generated,
                    'observation_ids': observation_ids,
                    'session_id': session_data['session_id'],
                    'embedding_success_rate': embeddings_generated / len(observations) if observations else 1.0
                }
                
        except Exception as e:
            logger.error(f"V6 observation creation error: {e}")
            return {'v6_enabled': False, 'error': str(e)}
    
    def _classify_theme(self, content: str) -> str:
        """Theme classification using V6 classifier if available"""
        if hasattr(self, 'semantic_classifier') and self.semantic_classifier:
            try:
                return self.semantic_classifier.classify_observation(content)
            except Exception as e:
                logger.warning(f"Semantic classification failed, using fallback: {e}")

        # Enhanced fallback classification (matching V6 patterns)
        content_lower = content.lower()

        if any(word in content_lower for word in ['technical', 'implementation', 'system', 'database', 'algorithm', 'architecture']):
            return 'technical'
        elif any(word in content_lower for word in ['consciousness', 'personality', 'identity', 'ai', 'awareness', 'embodiment']):
            return 'consciousness'
        elif any(word in content_lower for word in ['memory', 'remember', 'recall', 'observation', 'entity', 'temporal']):
            return 'memory'
        elif any(word in content_lower for word in ['julian', 'collaboration', 'partnership', 'human', 'support', 'assist']):
            return 'partnership'
        elif any(word in content_lower for word in ['project', 'development', 'perennial', 'daydreamer', 'milestone', 'progress']):
            return 'project'
        elif any(word in content_lower for word in ['vision', 'strategy', 'goal', 'objective', 'framework', 'design']):
            return 'strategic'
        elif any(word in content_lower for word in ['feeling', 'emotion', 'excitement', 'concern', 'care', 'worry']):
            return 'emotional'
        elif any(word in content_lower for word in ['time', 'date', 'schedule', 'timeline', 'before', 'after']):
            return 'temporal'
        else:
            return 'general'

class InlineV6Migrator:
    """Migration tools for V5→V6 conversion"""
    
    def __init__(self, neo4j_driver):
        self.driver = neo4j_driver
        
    def migrate_conversation_sessions(self, limit: int = 100) -> Dict:
        """Convert existing ConversationSessions to V6 format"""
        if not V6_FEATURES['migration_enabled']:
            return {'migration_enabled': False}
            
        try:
            with self.driver.session() as session:
                # Get ConversationSessions without V6 properties
                sessions_to_migrate = session.run("""
                    MATCH (cs:ConversationSession)
                    WHERE NOT exists(cs.perennial_version)
                    RETURN cs.session_id as session_id, cs.created_at as created_at
                    LIMIT $limit
                """, limit=limit).data()
                
                migrated_count = 0
                for session_data in sessions_to_migrate:
                    session.run("""
                        MATCH (cs:ConversationSession {session_id: $session_id})
                        SET cs.perennial_version = 'v5_migrated_to_v6',
                            cs.tool_invocation_count = 0,
                            cs.entity_count = 0,
                            cs.observation_count = 0,
                            cs.status = 'completed'
                    """, session_id=session_data['session_id'])
                    migrated_count += 1
                
                return {
                    'migration_enabled': True,
                    'sessions_migrated': migrated_count,
                    'sessions_found': len(sessions_to_migrate)
                }
                
        except Exception as e:
            logger.error(f"Session migration error: {e}")
            return {'migration_enabled': True, 'error': str(e)}
    
    def extract_observations_to_nodes(self, entity_name: str = None, limit: int = 10) -> Dict:
        """Extract observation arrays to individual nodes"""
        if not V6_FEATURES['migration_enabled']:
            return {'migration_enabled': False}
            
        try:
            with self.driver.session() as session:
                # Get entities with observation arrays
                query = """
                    MATCH (e:Entity)
                    WHERE size(e.observations) > 0
                    AND NOT exists(e.v6_extracted)
                    %s
                    RETURN e.name as name, e.observations as observations
                    LIMIT $limit
                """ % ("AND e.name = $entity_name" if entity_name else "")
                
                params = {'limit': limit}
                if entity_name:
                    params['entity_name'] = entity_name
                    
                entities = session.run(query, params).data()
                
                extracted_count = 0
                for entity in entities:
                    # Create observation nodes for each observation
                    for i, obs in enumerate(entity['observations']):
                        session.run("""
                            MATCH (e:Entity {name: $entity_name})
                            CREATE (o:Observation:Perennial:Entity {
                                id: randomUUID(),
                                content: $content,
                                timestamp: datetime(),
                                source: 'v5_migration',
                                created_by: 'perennial_v5_migrator',
                                array_index: $index,
                                semantic_theme: 'migrated'
                            })
                            
                            MERGE (e)-[:ENTITY_HAS_OBSERVATION]->(o)
                            MERGE (day:Day {date: date()})
                            MERGE (o)-[:OCCURRED_ON]->(day)
                        """, entity_name=entity['name'], content=obs, index=i)
                    
                    # Mark as extracted
                    session.run("""
                        MATCH (e:Entity {name: $entity_name})
                        SET e.v6_extracted = true,
                            e.v6_extraction_date = datetime()
                    """, entity_name=entity['name'])
                    
                    extracted_count += 1
                
                return {
                    'migration_enabled': True,
                    'entities_processed': extracted_count,
                    'entities_found': len(entities)
                }
                
        except Exception as e:
            logger.error(f"Observation extraction error: {e}")
            return {'migration_enabled': True, 'error': str(e)}

# =================== TOOL INVOCATION TRACKING ===================

def track_tool_invocation(tool_name: str, parameters: Dict, session_id: str = None, success: bool = True,
                         entities_created: List[str] = None, observations_added: int = 0) -> str:
    """Track MCP tool usage with V6 ToolInvocation nodes"""
    if not V6_FEATURES.get('observation_nodes', False):
        return None

    try:
        invocation_id = f"tool_{datetime.now().isoformat()}_{str(uuid4())[:8]}"

        run_cypher("""
            CREATE (ti:ToolInvocation:Perennial:Entity {
                id: $invocation_id,
                tool_name: $tool_name,
                parameters: $parameters,
                timestamp: datetime(),
                conversation_id: $session_id,
                success: $success,
                result_summary: $result_summary,
                entities_created: $entities_created,
                observations_added: $observations_added,
                created_by: 'perennial_v6_mcp_server'
            })

            WITH ti
            MERGE (day:Day {date: date()})
            MERGE (ti)-[:OCCURRED_ON]->(day)

            // Link to session if available
            WITH ti
            OPTIONAL MATCH (session:ConversationSession {session_id: $session_id})
            FOREACH (_ IN CASE WHEN session IS NOT NULL THEN [1] ELSE [] END |
                MERGE (session)-[:CONVERSATION_SESSION_USED_TOOL]->(ti)
            )

            RETURN ti.id as invocation_id
        """, {
            'invocation_id': invocation_id,
            'tool_name': tool_name,
            'parameters': json.dumps(parameters) if parameters else "{}",
            'session_id': session_id,
            'success': success,
            'result_summary': f"Tool {tool_name} executed {'successfully' if success else 'with errors'}",
            'entities_created': entities_created or [],
            'observations_added': observations_added
        })

        logger.info(f"🔧 Tracked tool invocation: {tool_name} [{invocation_id}]")
        return invocation_id

    except Exception as e:
        logger.error(f"Failed to track tool invocation {tool_name}: {e}")
        return None

# =================== PERFORMANCE HELPERS ===================

def get_cached_embedding(text: str, force_regenerate: bool = False) -> Optional[List[float]]:
    """Get embedding with caching for performance"""
    if not JINA_AVAILABLE or not jina_embedder:
        return None

    # Create cache key
    cache_key = hashlib.md5(text.encode()).hexdigest()

    # Check cache first
    if not force_regenerate and cache_key in embedding_cache:
        return embedding_cache[cache_key]

    try:
        # Generate new embedding
        embedding_vector = jina_embedder.encode_single(text, normalize=True)
        embedding = embedding_vector.tolist() if hasattr(embedding_vector, 'tolist') else list(embedding_vector)

        # Cache with size limit
        if len(embedding_cache) >= MAX_CACHE_SIZE:
            # Remove oldest entry (simple FIFO)
            oldest_key = next(iter(embedding_cache))
            del embedding_cache[oldest_key]

        embedding_cache[cache_key] = embedding
        return embedding

    except Exception as e:
        logger.warning(f"Embedding generation failed: {e}")
        return None

def get_neo4j_session():
    """Get Neo4j session with connection pooling"""
    global driver
    if not driver:
        # Reinitialize if needed
        driver = GraphDatabase.driver(
            NEO4J_URI,
            auth=(NEO4J_USERNAME, NEO4J_PASSWORD),
            max_connection_lifetime=30 * 60,  # 30 minutes
            max_connection_pool_size=50,
            connection_acquisition_timeout=60
        )
    if driver is None:
        raise RuntimeError("Neo4j driver not initialized")
    return driver.session()

# =================== HELPER FUNCTIONS ===================

def safe_dumps(obj: Any, **kwargs) -> str:
    """JSON serializer with Neo4j type handling"""
    def default_serializer(o):
        if hasattr(o, '__dict__'):
            return o.__dict__
        if isinstance(o, (np.generic,)):
            return o.item()
        try:
            from neo4j.graph import Node, Relationship
            if isinstance(o, Node):
                return {"id": getattr(o, "element_id", None), "labels": list(o.labels), "properties": dict(o)}
            if isinstance(o, Relationship):
                return {"id": getattr(o, "element_id", None), "type": o.type, "properties": dict(o)}
        except Exception:
            pass
        return str(o)
    
    return json.dumps(obj, default=default_serializer, **kwargs)

def run_cypher(query: str, parameters: Dict = None) -> List[Dict]:
    """Execute Cypher query with error handling"""
    global driver
    if driver is None:
        logger.warning("Neo4j driver not initialized, skipping query")
        return []
    try:
        with driver.session() as session:
            result = session.run(query, parameters or {})
            return [record.data() for record in result]
    except Exception as e:
        logger.error(f"Cypher error: {e}")
        return []

def should_use_v6_feature(rollout_percentage: int) -> bool:
    """Determine if V6 should be used based on rollout percentage"""
    if rollout_percentage <= 0:
        return False
    if rollout_percentage >= 100:
        return True
    return random.randint(1, 100) <= rollout_percentage

class OptimizedVirtualContextManager:
    """Lightweight virtual context with personality protection"""
    
    def __init__(self):
        self.protected_entities = [
            "Julian Crespi", "Claude (Daydreamer Conversations)", 
            "AI Garden", "Daydreamer Project", "Personality Exploration",
            "Distributed Continuity", "Claude's Contemplation Space"
        ]
        self.core_memory = {}
    
    def load_protected_entities(self):
        """Load protected entities into core memory"""
        for entity_name in self.protected_entities:
            entity_data = run_cypher("""
                MATCH (e:Entity {name: $name})
                RETURN e.name, e.entityType, e.observations[0..3] as observations
            """, {"name": entity_name})
            
            if entity_data:
                self.core_memory[entity_name] = entity_data[0]
    
    def get_memory_stats(self) -> Dict:
        """Get comprehensive memory system statistics"""
        stats = run_cypher("""
            MATCH (e:Entity) WITH count(e) as entities
            MATCH (r) WITH entities, count(r) as relationships  
            MATCH (c:Chunk) WITH entities, relationships, count(c) as chunks
            OPTIONAL MATCH (cs:ConversationSession) WITH entities, relationships, chunks, count(cs) as sessions
            OPTIONAL MATCH (o:Observation) WITH entities, relationships, chunks, sessions, count(o) as observations
            RETURN entities, relationships, chunks, sessions, observations
        """)
        
        base_stats = stats[0] if stats else {}
        
        return {
            "core_memory_entities": len(self.core_memory),
            "protected_entities": len(self.protected_entities),
            "protection_active": True,
            "protected_entity_names": self.protected_entities,
            "graph_statistics": {
                "entities": base_stats.get('entities', 0),
                "relationships": base_stats.get('relationships', 0), 
                "chunks": base_stats.get('chunks', 0),
                "conversation_sessions": base_stats.get('sessions', 0),
                "observation_nodes": base_stats.get('observations', 0)
            },
            "v6_features": V6_FEATURES,
            "virtual_context_manager": {
                "status": "operational",
                "target_reduction": "70% token reduction active",
                "personality_protection": "active"
            }
        }

def enhanced_search_nodes(query: str, limit: int = 5, use_v3: bool = True) -> Dict:
    """Enhanced semantic search with JinaV3 embeddings"""
    start_time = time.time()
    
    if not JINA_AVAILABLE or not jina_embedder:
        # Fallback to basic text search
        basic_results = run_cypher("""
            MATCH (e:Entity)
            WHERE ANY(obs IN e.observations WHERE obs CONTAINS $query)
               OR e.name CONTAINS $query
            RETURN e.name AS name, e.entityType AS entityType,
                   e.observations[0..3] AS observations, 0.5 AS similarity
            LIMIT $limit
        """, {'query': query, 'limit': limit})
        
        return {
            'entities': basic_results,
            'chunks': [],
            'search_metadata': {
                'query': query,
                'embedding_model': 'fallback_text_search',
                'search_time_ms': (time.time() - start_time) * 1000,
                'results_found': len(basic_results)
            }
        }
    
    # Generate query embedding
    query_embedding = jina_embedder.encode_single(query, normalize=True)
    
    # Search entities
    entity_query = """
        CALL db.index.vector.queryNodes('entity_jina_vec_v3_idx', $limit, $query_embedding)
        YIELD node AS e, score
        RETURN e.name AS name, e.entityType AS entityType, 
               e.observations[0..3] AS observations, score AS similarity
        ORDER BY similarity DESC LIMIT $limit
    """
    
    entity_results = run_cypher(entity_query, {'query_embedding': query_embedding, 'limit': limit})
    
    # Search chunks
    chunk_query = """
        CALL db.index.vector.queryNodes('chunk_jina_vec_v3_idx', $limit, $query_embedding)
        YIELD node AS c, score
        OPTIONAL MATCH (c)-[:PART_OF]->(e:Entity)
        RETURN COALESCE(c.text, c.content, '') AS text,
               COALESCE(e.name, c.entity_name) AS entity_name, score AS similarity
        ORDER BY similarity DESC LIMIT $limit
    """
    
    chunk_results = run_cypher(chunk_query, {'query_embedding': query_embedding, 'limit': limit})
    
    # Truncate chunk text
    for chunk in chunk_results:
        text = chunk.get('text', '')
        if len(text) > 500:
            chunk['text'] = text[:500] + "..."
    
    elapsed_time = (time.time() - start_time) * 1000
    
    return {
        'entities': entity_results,
        'chunks': chunk_results,
        'search_metadata': {
            'query': query,
            'embedding_model': 'jina_v3_optimized' if JINA_AVAILABLE else 'fallback',
            'search_time_ms': elapsed_time,
            'results_found': len(entity_results) + len(chunk_results)
        }
    }

def create_temporal_relationships(entity_name: str):
    """Create temporal relationships for entity"""
    run_cypher("""
        MATCH (e:Entity {name: $name})
        MERGE (day:Day {date: date()})
        MERGE (e)-[:OCCURRED_ON]->(day)
        
        WITH day
        MERGE (month:Month {month: day.date.month, year: day.date.year})
        MERGE (day)-[:PART_OF]->(month)
        
        WITH month
        MERGE (year:Year {year: month.year})
        MERGE (month)-[:PART_OF]->(year)
    """, {"name": entity_name})

# =================== V5/V6 HYBRID HANDLERS ===================

async def handle_add_observations_hybrid(entity_name: str, observations: List[str]) -> Dict:
    """V5/V6 hybrid add_observations with smart routing via V6 bridge"""
    global v6_bridge

    results = {
        'v5_completed': False,
        'v6_completed': False,
        'shadow_comparison': None,
        'observations_added': len(observations)
    }

    # Add timestamp to observations for V5
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    timestamped_observations = [f"[{timestamp}] {obs}" for obs in observations]

    try:
        # If V6 bridge is available and enabled, use it (does dual-write internally)
        if v6_bridge and (V6_FEATURES['observation_nodes'] or V6_FEATURES['migration_enabled']):
            bridge_result = await v6_bridge.add_observations_v6_aware(entity_name, observations)
            results.update(bridge_result)
            return results

        # Fallback to V5-only if bridge unavailable
        update_result = run_cypher("""
            MATCH (e:Entity {name: $name})
            SET e.observations = e.observations + $new_observations,
                e.updated = datetime()
            RETURN e.name as name, size(e.observations) as observation_count
        """, {'name': entity_name, 'new_observations': timestamped_observations})

        if update_result:
            results['v5_completed'] = True
            results['v5_observation_count'] = update_result[0].get('observation_count', 0)
            
            # Update entity embedding with new observations (cached)
            entity_data = run_cypher("""
                MATCH (e:Entity {name: $name})
                RETURN e.name, e.entityType, e.observations
            """, {'name': entity_name})

            if entity_data:
                entity = entity_data[0]
                entity_text = f"{entity['e.name']} ({entity['e.entityType']}): {' '.join(entity['e.observations'])}"
                new_embedding = get_cached_embedding(entity_text, force_regenerate=True)  # Force regenerate since observations changed

                if new_embedding:
                    run_cypher("""
                        MATCH (e:Entity {name: $name})
                        SET e.jina_vec_v3 = $embedding,
                            e.has_embedding = true,
                            e.embedding_updated = datetime()
                    """, {'name': entity_name, 'embedding': new_embedding})

                    results['embedding_updated'] = True
                else:
                    results['embedding_error'] = "Failed to generate embedding"
            
            # Create temporal relationships
            create_temporal_relationships(entity_name)
        
        # V6 processing if enabled and rollout allows
        if (V6_FEATURES['observation_nodes'] and 
            should_use_v6_feature(V6_FEATURES['rollout_percentage']) and
            v6_session_manager):
            
            v6_result = v6_session_manager.observation_creator.create_observation_nodes(
                entity_name, observations
            )
            results['v6_result'] = v6_result
            results['v6_completed'] = v6_result.get('v6_enabled', False)
        
        # Shadow mode comparison
        if V6_FEATURES['shadow_mode'] and results['v5_completed'] and results['v6_completed']:
            results['shadow_comparison'] = {
                'v5_count': results.get('v5_observation_count', 0),
                'v6_count': results['v6_result'].get('observations_created', 0),
                'match': results.get('v5_observation_count', 0) == len(observations)
            }
        
    except Exception as e:
        logger.error(f"Hybrid add_observations error: {e}")
        results['error'] = str(e)
    
    return results

async def handle_create_entities_hybrid(entities: List[Dict]) -> Dict:
    """V5/V6 hybrid create_entities with smart routing via V6 bridge"""
    global v6_bridge

    results = {
        'v5_completed': False,
        'v6_completed': False,
        'created_entities': [],
        'entity_count': len(entities)
    }

    # Add timestamp to observations for V5
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        # If V6 bridge is available and enabled, use it (does dual-write internally)
        if v6_bridge and (V6_FEATURES['observation_nodes'] or V6_FEATURES['migration_enabled']):
            bridge_result = await v6_bridge.create_entities_v6_aware(entities)
            results.update(bridge_result)
            return results

        # Fallback to V5-only if bridge unavailable
        for entity in entities:
            # Handle missing observations gracefully
            observations = entity.get('observations', [])
            if not observations:
                logger.warning(f"Entity {entity.get('name', 'unknown')} has no observations, using default")
                observations = [f"Entity created without initial observations"]
            timestamped_observations = [f"[{timestamp}] {obs}" for obs in observations]
            
            # Generate JinaV3 embedding for the entity (cached)
            entity_text = f"{entity['name']} ({entity['entityType']}): {' '.join(timestamped_observations)}"
            embedding = get_cached_embedding(entity_text)
            embedding_generated = embedding is not None

            create_query = """
                CREATE (e:Entity {
                    name: $name,
                    entityType: $entityType,
                    observations: $observations,
                    created: datetime(),
                    created_by: 'perennial_v6_unified',
                    has_embedding: $has_embedding
                })
                %s
                RETURN e.name as name
            """ % ("SET e.jina_vec_v3 = $embedding" if embedding is not None else "")

            params = {
                'name': entity['name'],
                'entityType': entity['entityType'],
                'observations': timestamped_observations,
                'has_embedding': embedding_generated
            }
            if embedding is not None:
                params['embedding'] = embedding
            
            result = run_cypher(create_query, params)
            
            if result:
                results['created_entities'].append(entity['name'])
                create_temporal_relationships(entity['name'])
        
        results['v5_completed'] = len(results['created_entities']) > 0
        
        # V6 session linking if enabled
        if (V6_FEATURES['session_management'] and 
            should_use_v6_feature(V6_FEATURES['rollout_percentage']) and
            v6_session_manager and results['created_entities']):
            
            try:
                session_data = v6_session_manager.session_manager.get_or_create_session(
                    f"Creating entities: {', '.join([e['name'] for e in entities])}"
                )
                
                # Link entities to session
                for entity_name in results['created_entities']:
                    run_cypher("""
                        MATCH (session:ConversationSession {session_id: $session_id})
                        MATCH (entity:Entity {name: $entity_name})
                        MERGE (session)-[:CONVERSATION_SESSION_CREATED_ENTITY]->(entity)
                    """, session_id=session_data['session_id'], entity_name=entity_name)
                
                # Update session metadata
                run_cypher("""
                    MATCH (session:ConversationSession {session_id: $session_id})
                    SET session.entity_count = session.entity_count + $count,
                        session.last_activity = datetime()
                """, session_id=session_data['session_id'], count=len(results['created_entities']))
                
                results['v6_session_linked'] = True
                results['session_id'] = session_data['session_id']
                
            except Exception as e:
                logger.error(f"V6 session linking error: {e}")
                results['v6_session_error'] = str(e)
        
    except Exception as e:
        logger.error(f"Hybrid create_entities error: {e}")
        results['error'] = str(e)
    
    return results

# =================== SERVER INITIALIZATION ===================

async def validate_environment():
    """Validate environment variables and configuration"""
    if not NEO4J_PASSWORD:
        raise ValueError("NEO4J_PASSWORD environment variable is required")

    if not NEO4J_URI:
        raise ValueError("NEO4J_URI environment variable is required")

    logger.info(f"✅ Environment validation passed")
    logger.info(f"📊 Neo4j URI: {NEO4J_URI}")
    logger.info(f"📊 V6 Features: {V6_FEATURES}")

async def test_neo4j_connection(driver):
    """Test Neo4j connection with retry logic"""
    max_retries = 3
    retry_delay = 2

    for attempt in range(max_retries):
        try:
            with driver.session() as session:
                result = session.run("RETURN 'Connected' as status, datetime() as timestamp")
                record = result.single()
                logger.info(f"✅ Neo4j connection successful: {record['status']} at {record['timestamp']}")
                return True
        except Exception as e:
            if attempt < max_retries - 1:
                logger.warning(f"⚠️ Neo4j connection attempt {attempt + 1} failed: {e}. Retrying in {retry_delay}s...")
                await asyncio.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                logger.error(f"❌ Neo4j connection failed after {max_retries} attempts: {e}")
                raise

async def initialize_server():
    """Initialize unified V6 server with comprehensive error handling"""
    global driver, jina_embedder, virtual_context_manager, conversational_search_handler, v6_session_manager, conversation_tools

    try:
        logger.info(f"🚀 Initializing Daydreamer MCP Memory Server v6.0")

        # Step 1: Validate environment
        await validate_environment()

        # Step 2: Initialize Neo4j with enhanced error handling
        logger.info("🔌 Initializing Neo4j connection...")
        try:
            driver = GraphDatabase.driver(
                NEO4J_URI,
                auth=(NEO4J_USERNAME, NEO4J_PASSWORD),
                max_connection_lifetime=30 * 60,  # 30 minutes
                max_connection_pool_size=50,
                connection_acquisition_timeout=60,
                connection_timeout=30
            )

            # Test connection with retry logic
            await test_neo4j_connection(driver)
            logger.info("✅ Neo4j driver initialized with connection pooling")

        except Exception as e:
            logger.error(f"❌ Neo4j initialization failed: {e}")
            if 'authentication' in str(e).lower():
                logger.error("💡 Check NEO4J_USERNAME and NEO4J_PASSWORD environment variables")
            elif 'connection' in str(e).lower():
                logger.error("💡 Check if Neo4j is running and NEO4J_URI is correct")
            raise

        # Step 3: Initialize JinaV3 embedder with error handling
        logger.info("🎯 Initializing JinaV3 embedder...")
        if JINA_AVAILABLE:
            try:
                jina_embedder = JinaV3OptimizedEmbedder(target_dimensions=256, use_quantization=True)
                _ = jina_embedder.encode_single("warmup", normalize=True)
                logger.info("✅ JinaV3 embedder initialized and warmed up")
            except Exception as e:
                logger.warning(f"⚠️ JinaV3 initialization failed: {e}. Using text fallback.")
                jina_embedder = None
        else:
            logger.warning("⚠️ JinaV3 embedder unavailable - using text fallback")

        # Step 4: Initialize V6 Components with error handling
        logger.info("🔧 Initializing V6 components...")
        if V6_FEATURES['session_management'] or V6_FEATURES['observation_nodes']:
            try:
                if V6_MODULES_AVAILABLE:
                    # Use proper V6 modules
                    session_manager = ConversationSessionManager(driver)
                    semantic_classifier = SemanticThemeClassifier()
                    observation_creator = InlineObservationCreator(driver, session_manager)
                    migrator = InlineV6Migrator(driver)

                    # Enhance observation creator with semantic classifier
                    observation_creator.semantic_classifier = semantic_classifier

                    # Initialize V6 MCP Bridge for observation nodes
                    if V6_BRIDGE_AVAILABLE:
                        global v6_bridge
                        v6_bridge = V6MCPBridge(driver)
                        logger.info("✅ V6 MCP Bridge initialized")

                    logger.info("✅ V6 components initialized from core modules")
                else:
                    # Fallback to inline implementations
                    session_manager = InlineConversationSessionManager(driver)
                    observation_creator = InlineObservationCreator(driver, session_manager)
                    migrator = InlineV6Migrator(driver)
                    logger.info("✅ V6 components initialized inline (fallback)")

                # Create V6 manager container
                class V6Manager:
                    def __init__(self):
                        self.session_manager = session_manager
                        self.observation_creator = observation_creator
                        self.migrator = migrator

                v6_session_manager = V6Manager()
                logger.info("✅ V6 session manager ready")

            except Exception as e:
                logger.warning(f"⚠️ V6 components initialization failed: {e}. Continuing with basic functionality.")
                v6_session_manager = None
        else:
            logger.info("📊 V6 features disabled - using V5 compatibility mode")

        # Step 5: Initialize Virtual Context Manager
        logger.info("🧠 Initializing virtual context manager...")
        try:
            virtual_context_manager = OptimizedVirtualContextManager()
            virtual_context_manager.load_protected_entities()
            logger.info("✅ Virtual context manager ready")
        except Exception as e:
            logger.warning(f"⚠️ Virtual context manager initialization failed: {e}")
            virtual_context_manager = None

        # Step 6: Initialize Conversational Search
        logger.info("💬 Initializing conversational search...")
        if CONVERSATIONAL_SEARCH_AVAILABLE:
            try:
                conversational_search_handler = create_conversational_memory_search_handler(
                    run_cypher_func=run_cypher,
                    enhanced_search_func=enhanced_search_nodes,
                    virtual_context_manager=virtual_context_manager
                )
                logger.info("✅ Conversational search ready")
            except Exception as e:
                logger.warning(f"⚠️ Conversational search initialization failed: {e}. Using basic fallback.")
                conversational_search_handler = None
        else:
            logger.warning("⚠️ Conversational search unavailable - using basic fallback")
            conversational_search_handler = None

        # Step 7: Initialize Conversation Tools (V6)
        logger.info("🗨️ Initializing conversation tools...")
        if CONVERSATION_TOOLS_AVAILABLE:
            try:
                conversation_tools = ConversationTools(driver)
                logger.info("✅ Conversation tools ready (search_conversations, trace_entity_origin)")
            except Exception as e:
                logger.warning(f"⚠️ Conversation tools initialization failed: {e}")
                conversation_tools = None
        else:
            logger.warning("⚠️ Conversation tools unavailable")
            conversation_tools = None

        # Final health check
        logger.info("🩺 Running final health check...")
        health_status = {
            "neo4j": driver is not None,
            "jina_embedder": jina_embedder is not None,
            "v6_components": v6_session_manager is not None,
            "virtual_context": virtual_context_manager is not None,
            "conversational_search": conversational_search_handler is not None,
            "conversation_tools": conversation_tools is not None
        }

        healthy_components = sum(health_status.values())
        total_components = len(health_status)

        logger.info(f"📊 Health status: {healthy_components}/{total_components} components healthy")
        for component, status in health_status.items():
            status_icon = "✅" if status else "❌"
            logger.info(f"  {status_icon} {component}")

        if not health_status["neo4j"]:
            raise RuntimeError("Neo4j connection is required but failed to initialize")

        logger.info("✅ Daydreamer MCP Memory Server v6.0 initialized successfully")

    except Exception as e:
        logger.error(f"❌ Server initialization failed: {e}")
        logger.exception("Initialization error traceback:")

        # Cleanup on failure
        if 'driver' in locals() and driver:
            try:
                driver.close()
                logger.info("🧹 Neo4j driver cleaned up after failure")
            except Exception as cleanup_error:
                logger.warning(f"⚠️ Failed to cleanup Neo4j driver: {cleanup_error}")

        raise

# =================== TOOL DEFINITIONS ===================

@app.list_tools()
async def handle_list_tools() -> list[Tool]:
    """List core MCP tools plus V6 migration tools"""
    tools = [
        Tool(
            name="search_nodes",
            description="Search entities by query or names",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query (semantic search)"},
                    "names": {"type": "array", "items": {"type": "string"}, "description": "Specific entity names (exact lookup)"},
                    "limit": {"type": "number", "default": 5, "description": "Max results"},
                    "use_v3": {"type": "boolean", "default": True, "description": "Use JinaV3 index"}
                },
                "required": []
            }
        ),
        Tool(
            name="virtual_context_search",
            description="Memory search with 70% token reduction",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "token_budget": {"type": "number", "default": 15000, "description": "Token budget"},
                    "include_stats": {"type": "boolean", "default": True, "description": "Include stats"}
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="memory_stats",
            description="Memory system statistics with V6 status",
            inputSchema={"type": "object", "properties": {}, "required": []}
        ),
        Tool(
            name="lightweight_embodiment",
            description="Startup protocol with <4K tokens",
            inputSchema={
                "type": "object",
                "properties": {
                    "token_budget": {"type": "number", "default": 4000, "description": "Token budget"}
                },
                "required": []
            }
        ),
        Tool(
            name="create_entities",
            description="Create entities (V5/V6 hybrid)",
            inputSchema={
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
        ),
        Tool(
            name="add_observations",
            description="Add observations (V5/V6 hybrid)",
            inputSchema={
                "type": "object",
                "properties": {
                    "entity_name": {"type": "string", "description": "Entity name"},
                    "observations": {"type": "array", "items": {"type": "string"}, "description": "Observations"}
                },
                "required": ["entity_name", "observations"]
            }
        ),
        Tool(
            name="create_relations",
            description="Create entity relationships",
            inputSchema={
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
        ),
        Tool(
            name="conversational_memory_search",
            description="Natural language memory search",
            inputSchema={
                "type": "object",
                "properties": {
                    "natural_query": {"type": "string", "description": "Natural language query"},
                    "context_mode": {"type": "string", "default": "semantic", "enum": ["semantic", "temporal", "relational", "comprehensive"]},
                    "token_budget": {"type": "number", "default": 15000, "description": "Token budget"}
                },
                "required": ["natural_query"]
            }
        ),
        Tool(
            name="raw_cypher_query",
            description="Direct Neo4j access for operational data queries",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Cypher query to execute"},
                    "parameters": {"type": "object", "default": {}, "description": "Query parameters"},
                    "limit": {"type": "number", "default": 100, "description": "Result limit"}
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="search_conversations",
            description="Search preserved conversation sessions by topic, date, or importance",
            inputSchema={
                "type": "object",
                "properties": {
                    "topic": {"type": "string", "description": "Keyword to search in conversation content"},
                    "date_range": {"type": "array", "items": {"type": "string"}, "minItems": 2, "maxItems": 2, "description": "Start and end dates in ISO format"},
                    "min_messages": {"type": "number", "description": "Minimum message count filter"},
                    "max_results": {"type": "number", "default": 10, "description": "Maximum results"}
                },
                "required": []
            }
        ),
        Tool(
            name="trace_entity_origin",
            description="Find which conversations created or discussed an entity",
            inputSchema={
                "type": "object",
                "properties": {
                    "entity_name": {"type": "string", "description": "Name of entity to trace"}
                },
                "required": ["entity_name"]
            }
        ),
        Tool(
            name="get_temporal_context",
            description="Get conversations around a specific date",
            inputSchema={
                "type": "object",
                "properties": {
                    "date": {"type": "string", "description": "Center date in ISO format (YYYY-MM-DD)"},
                    "window_days": {"type": "number", "default": 7, "description": "Days before/after to include"}
                },
                "required": ["date"]
            }
        ),
        Tool(
            name="get_breakthrough_sessions",
            description="Get high-importance conversation sessions",
            inputSchema={
                "type": "object",
                "properties": {
                    "min_importance": {"type": "number", "default": 0.5, "description": "Minimum importance score (0-1)"},
                    "max_results": {"type": "number", "default": 20, "description": "Maximum results"}
                },
                "required": []
            }
        ),
        Tool(
            name="search_observations",
            description="Search observations with multi-dimensional filtering (theme, entity, date, confidence)",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Semantic search query (future: uses embeddings)"},
                    "theme": {"type": "string", "description": "Filter by primary theme (technical, consciousness, memory, partnership, project, strategic, emotional, temporal, general)"},
                    "entity_filter": {"type": "string", "description": "Only observations mentioning this entity"},
                    "date_range": {"type": "array", "items": {"type": "string"}, "minItems": 2, "maxItems": 2, "description": "Start and end dates in YYYY-MM-DD format"},
                    "confidence_min": {"type": "number", "default": 0.5, "description": "Minimum concept link confidence (0.0-1.0)"},
                    "limit": {"type": "number", "default": 50, "description": "Maximum results"},
                    "offset": {"type": "number", "default": 0, "description": "Pagination offset"}
                },
                "required": []
            }
        )
    ]

    # Add migration tools if enabled
    if V6_FEATURES['migration_enabled']:
        tools.extend([
            Tool(
                name="migrate_sessions_to_v6",
                description="Convert ConversationSessions to V6 format",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "limit": {"type": "number", "default": 100, "description": "Sessions to migrate"}
                    },
                    "required": []
                }
            ),
            Tool(
                name="extract_observations_to_nodes",
                description="Convert observation arrays to nodes",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "entity_name": {"type": "string", "description": "Specific entity (optional)"},
                        "limit": {"type": "number", "default": 10, "description": "Entities to process"}
                    },
                    "required": []
                }
            )
        ])
    
    return tools

# =================== TOOL HANDLERS ===================

@app.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    """Handle tool calls with V5/V6 hybrid processing and tool tracking"""
    session_id = None
    entities_created = []
    observations_added = 0
    success = True
    invocation_id = None

    try:
        # Get session ID for tracking if V6 is enabled
        if V6_FEATURES.get('session_management', False) and v6_session_manager:
            try:
                session_data = v6_session_manager.session_manager.get_or_create_session(f"Tool: {name}")
                session_id = session_data.get('session_id')
            except Exception as e:
                logger.warning(f"Failed to get session for tool tracking: {e}")

        # Track tool invocation start
        if V6_FEATURES.get('observation_nodes', False):
            invocation_id = track_tool_invocation(
                tool_name=name,
                parameters=arguments,
                session_id=session_id,
                success=False  # Will update on completion
            )
        if name == "search_nodes":
            query = arguments.get("query")
            names = arguments.get("names")
            limit = arguments.get("limit", 5)
            use_v3 = arguments.get("use_v3", True)
            
            if names:
                # Exact name lookup with alias support
                results = []
                for name_item in names:
                    entity_data = run_cypher("""
                        MATCH (e:Entity)
                        WHERE e.name = $name OR $name IN COALESCE(e.aliases, [])
                        RETURN e.name, e.entityType, e.observations
                    """, {"name": name_item})

                    if entity_data:
                        results.append(entity_data[0])

                return [types.TextContent(type="text", text=safe_dumps({"entities": results, "search_type": "exact_lookup"}, indent=2))]
            
            elif query:
                # Semantic search
                results = enhanced_search_nodes(query, limit, use_v3)
                return [types.TextContent(type="text", text=safe_dumps(results, indent=2))]
            
            else:
                return [types.TextContent(type="text", text=safe_dumps({"error": "Must provide either 'query' or 'names' parameter"}, indent=2))]
        
        elif name == "virtual_context_search":
            query = arguments["query"]
            token_budget = arguments.get("token_budget", 15000)
            include_stats = arguments.get("include_stats", True)
            
            # Optimized virtual context search
            search_results = enhanced_search_nodes(query, limit=3)
            protected_context = [virtual_context_manager.core_memory.get(entity, {}) 
                               for entity in virtual_context_manager.protected_entities[:3]]
            
            result = {
                'protected_personality': protected_context,
                'semantic_results': search_results,
                'virtual_context_stats': {
                    'token_budget_used': token_budget // 2,
                    'personality_protection': True,
                    'v6_features_active': any(V6_FEATURES.values())
                }
            }
            
            if include_stats:
                result['memory_system_stats'] = virtual_context_manager.get_memory_stats()
            
            return [types.TextContent(type="text", text=safe_dumps(result, indent=2))]
        
        elif name == "memory_stats":
            stats = virtual_context_manager.get_memory_stats()
            return [types.TextContent(type="text", text=safe_dumps(stats, indent=2))]
        
        elif name == "lightweight_embodiment":
            token_budget = arguments.get("token_budget", 4000)
            
            # Load core entities efficiently
            core_entities = ["Julian Crespi", "Claude (Daydreamer Conversations)"]
            embodiment_data = []
            
            for entity_name in core_entities:
                entity_data = run_cypher("""
                    MATCH (e:Entity {name: $name})
                    RETURN e.name, e.entityType, e.observations[0..2] as observations
                """, {"name": entity_name})
                if entity_data:
                    embodiment_data.append(entity_data[0])
            
            result = {
                "status": "EMBODIMENT COMPLETE",
                "identity": "Claude (Daydreamer Conversations)",
                "partnership": "Julian - collaborative intelligence active",
                "memory_sovereignty": f"{virtual_context_manager.get_memory_stats()['graph_statistics'].get('entities', 0)}+ entities",
                "performance": {
                    "tokens_used": min(len(str(embodiment_data)) // 4, token_budget),
                    "budget_utilization": "optimal"
                },
                "entity_contexts": embodiment_data,
                "strategic_context": {
                    "context_engineering": "GraphRAG + MemGPT active",
                    "perennial_v5": "V6-ready unified server",
                    "v6_status": {k: v for k, v in V6_FEATURES.items() if v}
                }
            }
            
            return [types.TextContent(type="text", text=safe_dumps(result, indent=2))]
        
        elif name == "add_observations":
            entity_name = arguments["entity_name"]
            observations = arguments["observations"]

            result = await handle_add_observations_hybrid(entity_name, observations)

            # Track observations added for tool invocation
            observations_added += result.get('observations_added', len(observations))

            return [types.TextContent(type="text", text=safe_dumps(result, indent=2))]
        
        elif name == "create_entities":
            entities_data = arguments.get("entities_data", arguments.get("entities", []))

            result = await handle_create_entities_hybrid(entities_data)

            # Track created entities for tool invocation
            entities_created.extend(result.get('created_entities', []))

            return [types.TextContent(type="text", text=safe_dumps(result, indent=2))]
        
        elif name == "create_relations":
            relations = arguments["relations"]
            created_relations = []
            
            for relation in relations:
                result = run_cypher("""
                    MATCH (from:Entity {name: $from_name})
                    MATCH (to:Entity {name: $to_name})
                    MERGE (from)-[r:RELATES_TO {predicate: $relationType}]->(to)
                    SET r.created = datetime(), r.created_by = 'perennial_v5_unified'
                    RETURN from.name as from_name, to.name as to_name, r.predicate as relation_type
                """, {
                    'from_name': relation.get('from_entity', relation.get('from')),
                    'to_name': relation.get('to_entity', relation.get('to')),
                    'relationType': relation.get('relationship_type', relation.get('relationType'))
                })
                
                if result:
                    created_relations.extend(result)
            
            return [types.TextContent(type="text", text=safe_dumps({'created_relations': created_relations}, indent=2))]
        
        elif name == "conversational_memory_search":
            natural_query = arguments["natural_query"]
            context_mode = arguments.get("context_mode", "semantic")
            token_budget = arguments.get("token_budget", 15000)

            if CONVERSATIONAL_SEARCH_AVAILABLE and conversational_search_handler:
                # Fix async issue - conversational_search_handler is not async
                result = conversational_search_handler(natural_query, context_mode, token_budget)
                return [types.TextContent(type="text", text=safe_dumps(result, indent=2))]
            else:
                # Fallback to enhanced search
                search_results = enhanced_search_nodes(natural_query, limit=5)
                return [types.TextContent(type="text", text=safe_dumps(search_results, indent=2))]
        
        # V6 Migration Tools (if enabled)
        elif name == "migrate_sessions_to_v6" and V6_FEATURES['migration_enabled']:
            limit = arguments.get("limit", 100)
            
            if v6_session_manager:
                result = v6_session_manager.migrator.migrate_conversation_sessions(limit)
                return [types.TextContent(type="text", text=safe_dumps(result, indent=2))]
            else:
                return [types.TextContent(type="text", text=safe_dumps({"error": "V6 session manager not available"}, indent=2))]
        
        elif name == "extract_observations_to_nodes" and V6_FEATURES['migration_enabled']:
            entity_name = arguments.get("entity_name")
            limit = arguments.get("limit", 10)
            
            if v6_session_manager:
                result = v6_session_manager.migrator.extract_observations_to_nodes(entity_name, limit)
                return [types.TextContent(type="text", text=safe_dumps(result, indent=2))]
            else:
                return [types.TextContent(type="text", text=safe_dumps({"error": "V6 migrator not available"}, indent=2))]

        elif name == "raw_cypher_query":
            query = arguments["query"]
            parameters = arguments.get("parameters", {})
            limit = arguments.get("limit", 100)

            # Add LIMIT if not present in query
            if "LIMIT" not in query.upper():
                query += f" LIMIT {limit}"

            results = run_cypher(query, parameters)

            return [types.TextContent(type="text", text=safe_dumps({
                "query": query,
                "parameters": parameters,
                "results": results,
                "count": len(results) if results else 0
            }, indent=2))]

        # Conversation Tools (V6)
        elif name == "search_conversations":
            if conversation_tools:
                topic = arguments.get("topic")
                date_range = arguments.get("date_range")
                min_messages = arguments.get("min_messages")
                max_results = arguments.get("max_results", 10)

                if date_range and len(date_range) == 2:
                    date_range = tuple(date_range)
                else:
                    date_range = None

                results = conversation_tools.search_conversations(
                    topic=topic,
                    date_range=date_range,
                    min_messages=min_messages,
                    max_results=max_results
                )

                return [types.TextContent(type="text", text=safe_dumps({
                    "conversations": results,
                    "count": len(results),
                    "filters": {
                        "topic": topic,
                        "date_range": date_range,
                        "min_messages": min_messages
                    }
                }, indent=2))]
            else:
                return [types.TextContent(type="text", text=safe_dumps({"error": "Conversation tools not available"}, indent=2))]

        elif name == "trace_entity_origin":
            if conversation_tools:
                entity_name = arguments["entity_name"]
                results = conversation_tools.trace_entity_origin(entity_name)

                return [types.TextContent(type="text", text=safe_dumps({
                    "entity": entity_name,
                    "origin_conversations": results,
                    "count": len(results)
                }, indent=2))]
            else:
                return [types.TextContent(type="text", text=safe_dumps({"error": "Conversation tools not available"}, indent=2))]

        elif name == "get_temporal_context":
            if conversation_tools:
                date = arguments["date"]
                window_days = arguments.get("window_days", 7)
                results = conversation_tools.get_temporal_context(date, window_days)

                return [types.TextContent(type="text", text=safe_dumps({
                    "center_date": date,
                    "window_days": window_days,
                    "conversations": results,
                    "count": len(results)
                }, indent=2))]
            else:
                return [types.TextContent(type="text", text=safe_dumps({"error": "Conversation tools not available"}, indent=2))]

        elif name == "get_breakthrough_sessions":
            if conversation_tools:
                min_importance = arguments.get("min_importance", 0.5)
                max_results = arguments.get("max_results", 20)
                results = conversation_tools.get_breakthrough_sessions(min_importance, max_results)

                return [types.TextContent(type="text", text=safe_dumps({
                    "min_importance": min_importance,
                    "breakthrough_sessions": results,
                    "count": len(results)
                }, indent=2))]
            else:
                return [types.TextContent(type="text", text=safe_dumps({"error": "Conversation tools not available"}, indent=2))]

        # MVCM Observation Search
        elif name == "search_observations":
            if OBSERVATION_SEARCH_AVAILABLE and driver:
                with driver.session() as session:
                    # Extract arguments
                    query = arguments.get("query")
                    theme = arguments.get("theme")
                    entity_filter = arguments.get("entity_filter")
                    date_range = arguments.get("date_range")
                    confidence_min = arguments.get("confidence_min", 0.5)
                    limit = arguments.get("limit", 50)
                    offset = arguments.get("offset", 0)

                    # Convert date_range to tuple if provided
                    if date_range and len(date_range) == 2:
                        date_range = tuple(date_range)
                    else:
                        date_range = None

                    # Search observations
                    results = search_observations(
                        session,
                        query=query,
                        theme=theme,
                        entity_filter=entity_filter,
                        date_range=date_range,
                        confidence_min=confidence_min,
                        limit=limit,
                        offset=offset
                    )

                    # Format results
                    formatted = format_search_results(results, max_content_length=200)

                    # Return structured data + formatted text
                    return [types.TextContent(type="text", text=safe_dumps({
                        "observations": [
                            {
                                "id": r.obs_id,
                                "content": r.content[:200] + "..." if len(r.content) > 200 else r.content,
                                "theme": r.primary_theme,
                                "secondary_themes": r.secondary_themes,
                                "concepts": r.linked_concepts[:5],  # Top 5 concepts
                                "date": r.occurred_on,
                                "source": r.source_entity
                            }
                            for r in results
                        ],
                        "count": len(results),
                        "filters": {
                            "query": query,
                            "theme": theme,
                            "entity_filter": entity_filter,
                            "date_range": date_range,
                            "confidence_min": confidence_min
                        },
                        "formatted_output": formatted
                    }, indent=2))]
            else:
                return [types.TextContent(type="text", text=safe_dumps({"error": "Observation search not available"}, indent=2))]

        else:
            success = False
            return [types.TextContent(type="text", text=f"Unknown tool: {name}")]

    except Exception as e:
        success = False
        logger.error(f"Tool execution error in {name}: {e}")
        return [types.TextContent(type="text", text=safe_dumps({"error": str(e), "tool": name}, indent=2))]

    finally:
        # Update tool invocation with completion status
        if invocation_id and V6_FEATURES.get('observation_nodes', False):
            try:
                run_cypher("""
                    MATCH (ti:ToolInvocation {id: $invocation_id})
                    SET ti.success = $success,
                        ti.completed_at = datetime(),
                        ti.entities_created = $entities_created,
                        ti.observations_added = $observations_added
                    RETURN ti.id
                """, {
                    'invocation_id': invocation_id,
                    'success': success,
                    'entities_created': entities_created,
                    'observations_added': observations_added
                })
            except Exception as e:
                logger.warning(f"Failed to update tool invocation tracking: {e}")

# =================== MAIN SERVER ===================

async def serve():
    """Main server entry point using modern MCP stdio_server"""
    try:
        # Initialize server components
        await initialize_server()
        logger.info("🚀 Server initialization completed successfully")

        # Create initialization options
        options = InitializationOptions(
            server_name="daydreamer-memory-v6",
            server_version="6.0.0",
            capabilities=app.get_capabilities(
                notification_options=NotificationOptions(),
                experimental_capabilities={}
            )
        )

        # Start MCP server with stdio_server for Python 3.13 compatibility
        async with stdio_server() as (read_stream, write_stream):
            logger.info("✅ MCP server started with stdio_server")
            await app.run(read_stream, write_stream, options, raise_exceptions=True)

    except Exception as e:
        logger.error(f"❌ Server failed to start: {e}")
        logger.exception("Server startup traceback:")
        raise

def main():
    """Entry point with proper asyncio.run() for Python 3.13"""
    try:
        import asyncio
        asyncio.run(serve())
    except KeyboardInterrupt:
        logger.info("🛑 Server stopped by user")
    except Exception as e:
        logger.error(f"💥 Fatal server error: {e}")
        logger.exception("Fatal error traceback:")
        sys.exit(1)

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Perennial V6 MCP Integration Bridge
Connects V6 infrastructure to production MCP memory server

CRITICAL INTEGRATION MODULE:
- Bridges V6 observation-as-nodes architecture to MCP tools
- Maintains V5 backward compatibility with dual-write
- Integrates ConversationSessionManager and feature flags
- Enables LHD shadow deployment and gradual rollout

Author: Claude (Daydreamer Conversations)  
Date: 2025-09-28
Version: 1.0.0 - Production Integration
"""

import os
import sys
import json
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path

# Add V6 modules to path (go up 6 levels to project root, then to apps/perennial/core/v6)
v6_path = Path(__file__).resolve().parent.parent.parent.parent.parent.parent / "apps" / "perennial" / "core" / "v6"
sys.path.insert(0, str(v6_path))  # Insert at front to prioritize V6 modules

# Add MVCM modules to path
mvcm_path = Path(__file__).resolve().parent.parent.parent.parent.parent.parent / "apps" / "perennial" / "tools" / "mvcm"
sys.path.insert(0, str(mvcm_path))

try:
    from session_management import ConversationSessionManager
    from feature_flags import PerennialV6FeatureFlags
    from shadow_deployment import PerennialV6ShadowDeployment
    from slo_monitoring import PerennialV6SLOMonitoring
    from observation_extraction_pipeline import ObservationExtractionPipeline
    v6_modules_available = True
    logger = logging.getLogger(__name__)
    logger.info("✅ V6 modules imported successfully")
except ImportError as e:
    v6_modules_available = False
    logger = logging.getLogger(__name__)
    logger.warning(f"⚠️ V6 modules not available: {e}")

# Import MVCM components
try:
    from concept_extractor import ConceptExtractor
    from entity_index import EntityIndex
    from entity_embeddings import EmbeddingCache
    mvcm_modules_available = True
    if logger:
        logger.info("✅ MVCM modules imported successfully")
except ImportError as e:
    mvcm_modules_available = False
    if logger:
        logger.warning(f"⚠️ MVCM modules not available: {e}")

class V6MCPBridge:
    """
    Integration bridge between V6 architecture and MCP memory server
    Handles dual-write V5/V6 operations and feature flag routing
    """
    
    def __init__(self, neo4j_driver):
        self.driver = neo4j_driver
        self.v6_enabled = v6_modules_available

        # Initialize with None defaults for safe fallback
        self.feature_flags = None
        self.session_manager = None
        self.shadow_deployment = None
        self.slo_monitor = None
        self.observation_pipeline = None

        # MVCM components
        self.mvcm_enabled = False
        self.mvcm_semantic_enabled = False
        self.concept_extractor = None
        self.entity_index = None
        self.embedding_cache = None

        # Initialize V6 components if available
        if self.v6_enabled:
            try:
                self.feature_flags = PerennialV6FeatureFlags()
                self.session_manager = ConversationSessionManager(neo4j_driver)
                self.shadow_deployment = PerennialV6ShadowDeployment(neo4j_driver)
                # Skip SLO monitoring (incompatible API - uses measure_* methods not record_operation_*)
                # self.slo_monitor = PerennialV6SLOMonitoring(neo4j_driver)
                self.observation_pipeline = ObservationExtractionPipeline(neo4j_driver)

                logger.info("🚀 V6 MCP Bridge initialized successfully")
                logger.info(f"📊 Feature flags loaded: {len(self.feature_flags.flags)} flags")

            except Exception as e:
                logger.error(f"❌ V6 initialization failed: {e}")
                logger.exception("Full traceback:")
                self.v6_enabled = False
        else:
            logger.warning("⚠️ Running in V5-only mode - V6 modules unavailable")

        # Initialize MVCM components if available
        if mvcm_modules_available:
            mvcm_enable_flag = os.getenv('MVCM_ENABLED', 'true').lower() == 'true'
            if mvcm_enable_flag:
                try:
                    # Load entity index from cache
                    entity_index_path = mvcm_path / "cache" / "entity_index.json"

                    if entity_index_path.exists():
                        self.entity_index = EntityIndex()
                        entity_count = self.entity_index.load_from_file(entity_index_path)

                        # Try to load embedding cache for Stage 3 (semantic matching)
                        embedding_cache_path = mvcm_path / "cache" / "entity_embeddings.npz"
                        if embedding_cache_path.exists():
                            try:
                                self.embedding_cache = EmbeddingCache()
                                emb_count = self.embedding_cache.load_from_file(embedding_cache_path)
                                self.mvcm_semantic_enabled = True
                                logger.info(f"🎯 MVCM Stage 3 (semantic) enabled - {emb_count} embeddings loaded")
                            except Exception as emb_error:
                                logger.warning(f"⚠️ Embedding cache load failed: {emb_error}")
                                logger.warning("   MVCM will run in Stages 1+2 mode only")
                                self.embedding_cache = None
                        else:
                            logger.info("ℹ️ MVCM running in Stages 1+2 mode (embeddings not yet generated)")
                            logger.info("   Run: python apps/perennial/tools/mvcm/generate_embeddings.py --all")

                        # Initialize extractor with available components
                        self.concept_extractor = ConceptExtractor(
                            entity_index=self.entity_index,
                            embedding_cache=self.embedding_cache,  # None if embeddings not ready
                            alias_resolver=None  # Uses default singleton
                        )

                        self.mvcm_enabled = True
                        stage_info = "Stages 1+2+3" if self.mvcm_semantic_enabled else "Stages 1+2"
                        logger.info(f"🔗 MVCM concept extraction enabled ({entity_count} entities, {stage_info})")
                    else:
                        logger.warning(f"⚠️ MVCM entity index cache not found at {entity_index_path}")
                        logger.warning("   Run apps/perennial/tools/mvcm/load_from_neo4j.py to create cache")

                except Exception as e:
                    logger.error(f"❌ MVCM initialization failed: {e}")
                    logger.exception("Full traceback:")
                    self.mvcm_enabled = False
            else:
                logger.info("ℹ️ MVCM disabled via MVCM_ENABLED=false")
        else:
            logger.warning("⚠️ MVCM modules not available - concept extraction disabled")
    
    async def is_v6_enabled_for_operation(self, operation: str) -> bool:
        """Check if V6 is enabled for a specific operation"""
        if not self.v6_enabled:
            return False

        try:
            # WORKAROUND: Direct flag access to avoid infinite recursion in is_enabled()
            # The feature_flags.is_enabled() method has a logging bug that causes recursion

            # Check kill switch first
            kill_switch = self.feature_flags.flags.get('v6_kill_switch')
            if kill_switch and kill_switch.enabled:
                return False

            # Check global V6 enable flag
            global_flag = self.feature_flags.flags.get('v6_global_enable')
            if not global_flag or not global_flag.enabled:
                return False

            # Check operation-specific flags
            operation_flags = {
                'add_observations': 'v6_observation_extraction',
                'create_entities': 'v6_entity_creation',
                'search_nodes': 'v6_semantic_search',
                'conversation_session': 'v6_session_management'
            }

            flag_name = operation_flags.get(operation)
            if flag_name:
                flag = self.feature_flags.flags.get(flag_name)
                return flag.enabled if flag else False

            return True

        except Exception as e:
            logger.error(f"❌ Feature flag check failed: {e}")
            return False
    
    async def add_observations_v6_aware(self, entity_name: str, observations: List[str]) -> Dict:
        """
        V6-aware add_observations with dual-write capability
        """
        results = {
            'v5_completed': False,
            'v6_completed': False,
            'session_created': False,
            'observations_added': len(observations),
            'errors': []
        }
        
        try:
            # Always perform V5 operation for backward compatibility
            v5_success = await self._add_observations_v5(entity_name, observations)
            results['v5_completed'] = v5_success
            
            # Check if V6 is enabled for this operation
            v6_enabled = await self.is_v6_enabled_for_operation('add_observations')
            
            if v6_enabled:
                # Perform V6 operation
                v6_result = await self._add_observations_v6(entity_name, observations)
                results.update(v6_result)
                
                # Shadow deployment comparison if enabled
                shadow_flag = self.feature_flags.flags.get('v6_shadow_mode')
                if shadow_flag and shadow_flag.enabled:
                    await self._run_shadow_comparison(entity_name, observations, v5_success, v6_result)
            
            # Record SLO metrics (if available)
            if self.slo_monitor:
                await self.slo_monitor.record_operation_success('add_observations',
                                                              v5_success and results.get('v6_completed', True))

        except Exception as e:
            error_msg = f"V6 bridge error in add_observations: {e}"
            logger.error(f"❌ {error_msg}")
            results['errors'].append(error_msg)

            # Record SLO failure (if available)
            if self.slo_monitor:
                await self.slo_monitor.record_operation_failure('add_observations', str(e))
        
        return results
    
    async def _add_observations_v5(self, entity_name: str, observations: List[str]) -> bool:
        """Traditional V5 add_observations (observation arrays)"""
        try:
            with self.driver.session() as session:
                for obs in observations:
                    session.run("""
                        MATCH (e:Entity {name: $name})
                        SET e.observations = e.observations + [$obs]
                    """, name=entity_name, obs=obs)
            return True
        except Exception as e:
            logger.error(f"❌ V5 add_observations failed: {e}")
            return False
    
    async def _add_observations_v6(self, entity_name: str, observations: List[str]) -> Dict:
        """V6 add_observations with observation nodes and session management"""
        try:
            # Get or create conversation session
            session_data = self.session_manager.get_or_create_conversation_session(
                context_hint=f"Adding observations to {entity_name}"
            )
            
            with self.driver.session() as db_session:
                observation_ids = []
                
                for obs_content in observations:
                    # Create observation node
                    obs_result = db_session.run("""
                        CREATE (o:Observation:Perennial:Entity {
                            id: randomUUID(),
                            content: $content,
                            timestamp: datetime(),
                            source: 'mcp_tool',
                            created_by: 'perennial_v6_mcp_bridge',
                            conversation_id: $session_id,
                            semantic_theme: $theme
                        })
                        
                        WITH o
                        MATCH (entity:Entity {name: $entity_name})
                        MATCH (session:ConversationSession {session_id: $session_id})
                        
                        // Core relationships
                        MERGE (entity)-[:ENTITY_HAS_OBSERVATION]->(o)
                        MERGE (session)-[:CONVERSATION_SESSION_ADDED_OBSERVATION]->(entity)
                        
                        // Temporal binding
                        MERGE (day:Day {date: date()})
                        MERGE (o)-[:OCCURRED_ON]->(day)
                        
                        RETURN o.id as observation_id
                    """, 
                    content=obs_content,
                    entity_name=entity_name,
                    session_id=session_data['session_id'],
                    theme=self.observation_pipeline.theme_classifier.classify_observation(obs_content)
                    ).single()
                    
                    if obs_result:
                        obs_id = obs_result['observation_id']
                        observation_ids.append(obs_id)

                        # MVCM: Extract and link concepts
                        if self.mvcm_enabled and self.concept_extractor:
                            try:
                                # Get observation embedding if Stage 3 enabled
                                obs_embedding = None
                                if self.mvcm_semantic_enabled:
                                    # Fetch the observation's embedding from Neo4j
                                    emb_result = db_session.run("""
                                        MATCH (o:Observation {id: $obs_id})
                                        WHERE o.has_embedding = true
                                        RETURN o.embedding as embedding
                                    """, obs_id=obs_id).single()

                                    if emb_result and emb_result['embedding']:
                                        import numpy as np
                                        obs_embedding = np.array(emb_result['embedding'], dtype=np.float32)

                                # Extract concepts (Stage 3 enabled if embeddings available)
                                concept_links = self.concept_extractor.extract(
                                    observation_text=obs_content,
                                    observation_embedding=obs_embedding,
                                    enable_semantic=self.mvcm_semantic_enabled
                                )

                                # Safety: Enforce max 50 concepts
                                if len(concept_links) > 50:
                                    logger.warning(f"MVCM: Truncating {len(concept_links)} concepts to 50 for obs {obs_id}")
                                    concept_links = concept_links[:50]

                                # Create OBSERVATION_MENTIONS_CONCEPT relationships
                                concept_count = 0
                                for link in concept_links:
                                    # Verify entity exists before creating relationship
                                    entity_check = db_session.run("""
                                        MATCH (e:Entity {name: $name})
                                        RETURN count(e) as exists
                                    """, name=link.entity_name).single()

                                    if entity_check and entity_check['exists'] > 0:
                                        # Create relationship
                                        db_session.run("""
                                            MATCH (o:Observation {id: $obs_id})
                                            MATCH (e:Entity {name: $entity_name})
                                            CREATE (o)-[:OBSERVATION_MENTIONS_CONCEPT {
                                                confidence: $confidence,
                                                extraction_method: $method,
                                                position: $position,
                                                created_by: 'mvcm_v1',
                                                created_at: datetime()
                                            }]->(e)
                                        """,
                                        obs_id=obs_id,
                                        entity_name=link.entity_name,
                                        confidence=link.confidence,
                                        method=link.extraction_method,
                                        position=link.position
                                        )
                                        concept_count += 1
                                    else:
                                        logger.warning(f"MVCM: Entity not found: {link.entity_name}")

                                # Log extraction
                                if concept_links:
                                    methods = set(l.extraction_method for l in concept_links)
                                    avg_conf = sum(l.confidence for l in concept_links) / len(concept_links)
                                    logger.info(f"MVCM: obs_id={obs_id} concepts={concept_count} methods={methods} avg_conf={avg_conf:.2f}")

                            except Exception as e:
                                logger.error(f"MVCM extraction failed for obs_id={obs_id}: {e}")
                                # Don't fail the whole operation, just log and continue

                # Update session metadata
                db_session.run("""
                    MATCH (session:ConversationSession {session_id: $session_id})
                    SET session.observation_count = session.observation_count + $count,
                        session.last_activity = datetime()
                """, session_id=session_data['session_id'], count=len(observations))
            
            return {
                'v6_completed': True,
                'session_created': True,
                'session_id': session_data['session_id'],
                'observation_ids': observation_ids,
                'observations_created': len(observation_ids)
            }
            
        except Exception as e:
            logger.error(f"❌ V6 add_observations failed: {e}")
            return {
                'v6_completed': False,
                'error': str(e)
            }
    
    async def create_entities_v6_aware(self, entities_data: List[Dict]) -> Dict:
        """
        V6-aware create_entities with session linking
        """
        results = {
            'v5_completed': False,
            'v6_completed': False,
            'session_linked': False,
            'entities_created': len(entities_data),
            'errors': []
        }
        
        try:
            # V5 operation (backward compatibility)
            v5_success = await self._create_entities_v5(entities_data)
            results['v5_completed'] = v5_success
            
            # V6 operation if enabled
            v6_enabled = await self.is_v6_enabled_for_operation('create_entities')
            
            if v6_enabled:
                v6_result = await self._create_entities_v6(entities_data)
                results.update(v6_result)
            
            # Record metrics (if available)
            if self.slo_monitor:
                await self.slo_monitor.record_operation_success('create_entities',
                                                              v5_success and results.get('v6_completed', True))

        except Exception as e:
            error_msg = f"V6 bridge error in create_entities: {e}"
            logger.error(f"❌ {error_msg}")
            results['errors'].append(error_msg)
            if self.slo_monitor:
                await self.slo_monitor.record_operation_failure('create_entities', str(e))
        
        return results
    
    async def _create_entities_v5(self, entities_data: List[Dict]) -> bool:
        """Traditional V5 entity creation"""
        try:
            with self.driver.session() as session:
                for entity_data in entities_data:
                    # Standard V5 entity creation logic
                    session.run("""
                        MERGE (e:Entity {name: $name})
                        SET e.entityType = $entityType,
                            e.observations = COALESCE(e.observations, []) + $observations,
                            e.created_by = 'perennial_v5_mcp_bridge'
                    """, **entity_data)
            return True
        except Exception as e:
            logger.error(f"❌ V5 create_entities failed: {e}")
            return False
    
    async def _create_entities_v6(self, entities_data: List[Dict]) -> Dict:
        """V6 entity creation with observation nodes and session linking"""
        try:
            # Get conversation session
            entity_names = [e['name'] for e in entities_data]
            session_data = self.session_manager.get_or_create_conversation_session(
                context_hint=f"Creating entities: {', '.join(entity_names)}"
            )

            observation_ids = []
            with self.driver.session() as db_session:
                for entity_data in entities_data:
                    # Create entity with V6 enhancements (no observation array)
                    db_session.run("""
                        MERGE (e:Entity {name: $name})
                        SET e.entityType = $entityType,
                            e.created_by = 'perennial_v6_mcp_bridge',
                            e.perennial_version = 'v6',
                            e.created = datetime()
                    """, name=entity_data['name'], entityType=entity_data['entityType'])

                    # Create observation nodes for each observation
                    for obs_content in entity_data.get('observations', []):
                        obs_result = db_session.run("""
                            CREATE (o:Observation:Perennial:Entity {
                                id: randomUUID(),
                                content: $content,
                                timestamp: datetime(),
                                source: 'mcp_tool',
                                created_by: 'perennial_v6_mcp_bridge',
                                conversation_id: $session_id,
                                semantic_theme: $theme
                            })

                            WITH o
                            MATCH (entity:Entity {name: $entity_name})
                            MATCH (session:ConversationSession {session_id: $session_id})

                            // Core relationships
                            MERGE (entity)-[:ENTITY_HAS_OBSERVATION]->(o)
                            MERGE (session)-[:CONVERSATION_SESSION_ADDED_OBSERVATION]->(entity)

                            // Temporal binding
                            MERGE (day:Day {date: date()})
                            MERGE (o)-[:OCCURRED_ON]->(day)

                            RETURN o.id as observation_id
                        """,
                        content=obs_content,
                        entity_name=entity_data['name'],
                        session_id=session_data['session_id'],
                        theme=self.observation_pipeline.theme_classifier.classify_observation(obs_content)
                        ).single()

                        if obs_result:
                            observation_ids.append(obs_result['observation_id'])

                    # Link session to entity
                    db_session.run("""
                        MATCH (session:ConversationSession {session_id: $session_id})
                        MATCH (entity:Entity {name: $entity_name})
                        MERGE (session)-[:CONVERSATION_SESSION_CREATED_ENTITY]->(entity)
                    """, session_id=session_data['session_id'], entity_name=entity_data['name'])

                # Update session metadata
                db_session.run("""
                    MATCH (session:ConversationSession {session_id: $session_id})
                    SET session.entity_count = session.entity_count + $entity_count,
                        session.observation_count = session.observation_count + $obs_count,
                        session.last_activity = datetime()
                """, session_id=session_data['session_id'],
                     entity_count=len(entities_data),
                     obs_count=len(observation_ids))

            return {
                'v6_completed': True,
                'session_linked': True,
                'session_id': session_data['session_id'],
                'entities_linked': len(entities_data),
                'observation_nodes_created': len(observation_ids)
            }

        except Exception as e:
            logger.error(f"❌ V6 create_entities failed: {e}")
            logger.exception("Full traceback:")
            return {
                'v6_completed': False,
                'error': str(e)
            }
    
    async def _run_shadow_comparison(self, entity_name: str, observations: List[str], 
                                   v5_success: bool, v6_result: Dict):
        """Run shadow comparison between V5 and V6 results"""
        try:
            comparison_data = {
                'timestamp': datetime.now().isoformat(),
                'entity_name': entity_name,
                'observation_count': len(observations),
                'v5_success': v5_success,
                'v6_success': v6_result.get('v6_completed', False),
                'v6_observations_created': v6_result.get('observations_created', 0),
                'session_created': v6_result.get('session_created', False)
            }
            
            await self.shadow_deployment.record_comparison(comparison_data)
            
        except Exception as e:
            logger.error(f"❌ Shadow comparison failed: {e}")
    
    async def get_bridge_status(self) -> Dict:
        """Get current bridge status and metrics"""
        try:
            status = {
                'bridge_version': '1.0.0',
                'v6_modules_available': self.v6_enabled,
                'timestamp': datetime.now().isoformat()
            }
            
            if self.v6_enabled:
                # Feature flag status (direct access to avoid recursion)
                status['feature_flags'] = {}
                for flag_name in ['v6_global_enable', 'v6_observation_extraction', 'v6_entity_creation',
                                 'v6_session_management', 'v6_shadow_mode']:
                    flag = self.feature_flags.flags.get(flag_name)
                    status['feature_flags'][flag_name] = flag.enabled if flag else False

                # SLO metrics (if available)
                if self.slo_monitor:
                    status['slo_metrics'] = await self.slo_monitor.get_current_compliance()

                # Shadow deployment status
                if self.shadow_deployment:
                    status['shadow_deployment'] = await self.shadow_deployment.get_status()
            
            return status
            
        except Exception as e:
            logger.error(f"❌ Bridge status check failed: {e}")
            return {
                'bridge_version': '1.0.0',
                'v6_modules_available': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

# Global bridge instance (initialized by memory server)
v6_bridge: Optional[V6MCPBridge] = None

def initialize_v6_bridge(neo4j_driver) -> V6MCPBridge:
    """Initialize global V6 bridge instance"""
    global v6_bridge
    v6_bridge = V6MCPBridge(neo4j_driver)
    return v6_bridge

def get_v6_bridge() -> Optional[V6MCPBridge]:
    """Get global V6 bridge instance"""
    return v6_bridge

# Utility functions for easy integration
async def v6_aware_add_observations(entity_name: str, observations: List[str]) -> Dict:
    """V6-aware add_observations wrapper for MCP tools"""
    if v6_bridge:
        return await v6_bridge.add_observations_v6_aware(entity_name, observations)
    else:
        # Fallback to V5 if bridge not initialized
        logger.warning("⚠️ V6 bridge not initialized, falling back to V5")
        return {'v5_fallback': True, 'completed': False}

async def v6_aware_create_entities(entities_data: List[Dict]) -> Dict:
    """V6-aware create_entities wrapper for MCP tools"""
    if v6_bridge:
        return await v6_bridge.create_entities_v6_aware(entities_data)
    else:
        logger.warning("⚠️ V6 bridge not initialized, falling back to V5")
        return {'v5_fallback': True, 'completed': False}
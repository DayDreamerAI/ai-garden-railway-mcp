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

# Add schemas directory to path (consolidated Oct 13, 2025)
# Path from: llm/mcp/servers/daydreamer-memory-mcp/src/v6_mcp_bridge.py
# Target:    llm/memory/schemas/
schemas_path = Path(__file__).resolve().parent.parent.parent.parent.parent / "memory" / "schemas"
sys.path.insert(0, str(schemas_path))

# Import canonical property names schema (single source of truth for property names)
try:
    from property_names import (
        ObservationProperties as OBS,
        EntityProperties as ENT,
        ConversationSessionProperties as SESS,
        NodeLabels as LABELS,
        RelationshipTypes as RELS,
    )
    schema_available = True
except ImportError as e:
    schema_available = False
    logging.getLogger(__name__).error(f"❌ CRITICAL: property_names schema not available: {e}")
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

# Import JinaV3 embedder for synchronous embedding generation
try:
    from jina_v3_optimized_embedder import JinaV3OptimizedEmbedder
    jina_embedder_available = True
except ImportError as e:
    jina_embedder_available = False
    if logger:
        logger.warning(f"⚠️ JinaV3OptimizedEmbedder not available: {e}")

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

        # Embedding generation (for synchronous embedding in V6 observations)
        self.embedder = None

        # Initialize JinaV3 embedder for synchronous embedding generation
        if jina_embedder_available:
            try:
                self.embedder = JinaV3OptimizedEmbedder()
                self.embedder.initialize()
                logger.info("✅ JinaV3 embedder initialized for synchronous observation embedding generation")
            except Exception as e:
                logger.warning(f"⚠️ JinaV3 embedder initialization failed: {e}")
                logger.warning("   Observations will be created without embeddings (requires manual batch generation)")
                self.embedder = None

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
        V6-only add_observations (V5 arrays removed - 100% V6 compliance achieved Oct 18, 2025)
        """
        results = {
            'v6_completed': False,
            'session_created': False,
            'observations_added': len(observations),
            'errors': []
        }

        try:
            # V6 operation (V5 dual-write removed after 100% migration)
            v6_result = await self._add_observations_v6(entity_name, observations)
            results.update(v6_result)

            # Record SLO metrics (if available)
            if self.slo_monitor:
                await self.slo_monitor.record_operation_success('add_observations',
                                                              results.get('v6_completed', False))

        except Exception as e:
            error_msg = f"V6 bridge error in add_observations: {e}"
            logger.error(f"❌ {error_msg}")
            results['errors'].append(error_msg)

            # Record SLO failure (if available)
            if self.slo_monitor:
                await self.slo_monitor.record_operation_failure('add_observations', str(e))

        return results

    async def _add_observations_v6(self, entity_name: str, observations: List[str]) -> Dict:
        """V6 add_observations with observation nodes and session management"""
        try:
            # Get or create conversation session (ALWAYS create session for tool invocations)
            session_data = self.session_manager.get_or_create_conversation_session(
                context_hint=f"MCP Tool: add_observations to {entity_name}"
            )

            with self.driver.session() as db_session:
                observation_ids = []
                embeddings_generated = 0

                for obs_content in observations:
                    # V6 COMPLIANCE: Generate ISO 8601 timestamp for created_at
                    created_at_iso = datetime.now().isoformat(timespec='milliseconds') + 'Z'

                    # Use general theme for now (avoid potential recursion in classifier)
                    theme = 'general'

                    # Generate embedding synchronously (with lazy initialization)
                    embedding_vector = None
                    has_embedding = False

                    # Check feature flag for embedding generation (direct access to avoid recursion bug)
                    embedding_flag = self.feature_flags.flags.get('v6_embedding_generation') if self.feature_flags else None
                    embedding_enabled = embedding_flag.enabled if embedding_flag else False

                    if embedding_enabled:
                        # Lazy initialization: try to initialize embedder if not already done
                        if not self.embedder and jina_embedder_available:
                            try:
                                logger.info("🔄 Lazy-initializing JinaV3 embedder...")
                                self.embedder = JinaV3OptimizedEmbedder()
                                self.embedder.initialize()
                                logger.info("✅ JinaV3 embedder lazy-initialized successfully")
                            except Exception as e:
                                logger.error(f"❌ JinaV3 lazy initialization failed: {e}")
                                self.embedder = None

                        # Generate embedding if embedder is available
                        if self.embedder:
                            try:
                                embedding_vector = self.embedder.encode_single(obs_content, normalize=True)
                                has_embedding = True
                                logger.debug(f"✅ Generated 256D embedding for observation")
                            except Exception as e:
                                logger.warning(f"⚠️ Embedding generation failed: {e}")
                                # Continue without embedding - graceful degradation
                        else:
                            logger.warning(f"⚠️ Embedder not available - observation created without embedding")
                    else:
                        logger.debug(f"⏭️ Embedding generation disabled by feature flag")

                    # CRITICAL FIX (Oct 10, 2025): MATCH entity and session FIRST to validate they exist
                    # Then CREATE observation node - prevents silent failures
                    # Uses V6 canonical schema constants for all property names
                    obs_result = db_session.run(f"""
                        // Validate entity and session exist FIRST
                        MATCH (entity:Entity {{name: $entity_name}})
                        MATCH (session:ConversationSession {{session_id: $session_id}})

                        // Create observation node with embedding properties and full temporal binding
                        // V6 COMPLIANCE: created_at must be ISO 8601 string (not DateTime object)
                        CREATE (o:Observation:Perennial:Entity {{
                            id: randomUUID(),
                            {OBS.CONTENT}: $content,
                            created_at: $created_at_iso,
                            source: 'mcp_tool',
                            created_by: 'perennial_v6_mcp_bridge',
                            {OBS.CONVERSATION_ID}: $session_id,
                            {OBS.SEMANTIC_THEME}: $theme,

                            // Embedding properties (canonical schema)
                            {OBS.JINA_VEC_V3}: $embedding_vector,
                            {OBS.HAS_EMBEDDING}: $has_embedding,
                            {OBS.EMBEDDING_MODEL}: CASE WHEN $has_embedding THEN 'jina-embeddings-v3' ELSE null END,
                            {OBS.EMBEDDING_DIMENSIONS}: CASE WHEN $has_embedding THEN 256 ELSE null END,
                            {OBS.EMBEDDING_GENERATED_AT}: CASE WHEN $has_embedding THEN $created_at_iso ELSE null END
                        }})

                        // Core relationships (canonical schema)
                        MERGE (entity)-[:{RELS.ENTITY_HAS_OBSERVATION}]->(o)
                        MERGE (session)-[:{RELS.CONVERSATION_SESSION_ADDED_OBSERVATION}]->(entity)

                        // Full temporal binding: Day → Month → Year hierarchy (CANONICAL V6 SCHEMA)
                        // Month uses 'date' property in YYYY-MM format (fixed Oct 18, 2025)
                        WITH o
                        MERGE (day:Day {{date: toString(date())}})
                        ON CREATE SET day.year = date().year, day.month = date().month, day.day = date().day

                        WITH o, day, date() as current_date
                        MERGE (month:Month {{date: toString(current_date.year) + '-' + substring('0' + toString(current_date.month), -2)}})
                        ON CREATE SET month.month = current_date.month, month.year = current_date.year

                        WITH o, day, month, current_date
                        MERGE (year:Year {{year: current_date.year}})

                        MERGE (o)-[:{RELS.OCCURRED_ON}]->(day)
                        MERGE (day)-[:{RELS.PART_OF_MONTH}]->(month)
                        MERGE (month)-[:{RELS.PART_OF_YEAR}]->(year)

                        RETURN o.id as observation_id, o.created_at as created_at, o.{OBS.HAS_EMBEDDING} as has_embedding
                    """,
                    content=obs_content,
                    entity_name=entity_name,
                    session_id=session_data['session_id'],
                    theme=theme,
                    embedding_vector=embedding_vector,
                    has_embedding=has_embedding,
                    created_at_iso=created_at_iso
                    ).single()

                    # V6 COMPLIANCE: Ensure temporal hierarchy exists
                    self.ensure_temporal_hierarchy(created_at_iso)
                    
                    if obs_result:
                        obs_id = obs_result['observation_id']
                        observation_ids.append(obs_id)

                        # Log embedding status and track count
                        if obs_result['has_embedding']:
                            embeddings_generated += 1
                            logger.info(f"✅ Observation {obs_id[:8]}... created WITH embedding")
                        else:
                            logger.warning(f"⚠️ Observation {obs_id[:8]}... created WITHOUT embedding")

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

            # V6 COMPLIANCE: Validate all observations against audit standards
            compliance_result = self.validate_v6_compliance(observation_ids)

            # Log compliance status
            if compliance_result['compliant']:
                logger.info(f"✅ V6 Compliance: {len(observation_ids)} observations 100% compliant")
            else:
                logger.warning(f"⚠️ V6 Compliance: {compliance_result['compliant_count']}/{compliance_result['total_validated']} compliant ({compliance_result['compliance_percentage']:.1f}%)")
                if compliance_result.get('violations'):
                    for violation in compliance_result['violations'][:5]:  # Log first 5 violations
                        logger.warning(f"  - {violation}")

            return {
                'v6_completed': True,
                'session_created': True,
                'session_id': session_data['session_id'],
                'observation_ids': observation_ids,
                'observations_created': len(observation_ids),
                'embeddings_generated': embeddings_generated,
                'v6_compliance': compliance_result  # Include compliance validation results
            }
            
        except Exception as e:
            logger.error(f"❌ V6 add_observations failed: {e}")
            return {
                'v6_completed': False,
                'error': str(e)
            }
    
    async def create_entities_v6_aware(self, entities_data: List[Dict]) -> Dict:
        """
        V6-only create_entities (V5 arrays removed - 100% V6 compliance achieved Oct 18, 2025)
        """
        results = {
            'v6_completed': False,
            'session_linked': False,
            'entities_created': len(entities_data),
            'errors': []
        }

        try:
            # V6 operation (V5 dual-write removed after 100% migration)
            v6_result = await self._create_entities_v6(entities_data)
            results.update(v6_result)

            # Record metrics (if available)
            if self.slo_monitor:
                await self.slo_monitor.record_operation_success('create_entities',
                                                              results.get('v6_completed', False))

        except Exception as e:
            error_msg = f"V6 bridge error in create_entities: {e}"
            logger.error(f"❌ {error_msg}")
            results['errors'].append(error_msg)
            if self.slo_monitor:
                await self.slo_monitor.record_operation_failure('create_entities', str(e))

        return results

    async def _create_entities_v6(self, entities_data: List[Dict]) -> Dict:
        """V6 entity creation with observation nodes, session linking, and embedding generation"""
        try:
            # Get conversation session
            entity_names = [e['name'] for e in entities_data]
            session_data = self.session_manager.get_or_create_conversation_session(
                context_hint=f"Creating entities: {', '.join(entity_names)}"
            )

            observation_ids = []
            with self.driver.session() as db_session:
                for entity_data in entities_data:
                    # Generate entity embedding (matching observation pattern)
                    entity_embedding = None
                    entity_has_embedding = False

                    # Check feature flag for embedding generation
                    embedding_flag = self.feature_flags.flags.get('v6_embedding_generation') if self.feature_flags else None
                    embedding_enabled = embedding_flag.enabled if embedding_flag else False

                    if embedding_enabled:
                        # Lazy-initialize JinaV3 embedder if needed
                        if not self.embedder and jina_embedder_available:
                            try:
                                logger.info("🔄 Lazy-initializing JinaV3 embedder for entity...")
                                self.embedder = JinaV3OptimizedEmbedder()
                                self.embedder.initialize()
                                logger.info("✅ JinaV3 embedder lazy-initialized successfully")
                            except Exception as e:
                                logger.error(f"❌ JinaV3 lazy initialization failed: {e}")
                                self.embedder = None

                        # Generate embedding from entity text (name + type + observations)
                        if self.embedder:
                            try:
                                observations_text = ' '.join(entity_data.get('observations', []))
                                entity_text = f"{entity_data['name']} ({entity_data['entityType']}): {observations_text}"
                                entity_embedding = self.embedder.encode_single(entity_text, normalize=True)
                                entity_has_embedding = True
                                logger.debug(f"✅ Generated 256D embedding for entity: {entity_data['name']}")
                            except Exception as e:
                                logger.warning(f"⚠️ Entity embedding generation failed: {e}")

                    # Create entity with V6 enhancements including embeddings (canonical schema)
                    db_session.run(f"""
                        MERGE (e:Entity {{name: $name}})
                        SET e.entityType = $entityType,
                            e.created_by = 'perennial_v6_mcp_bridge',
                            e.perennial_version = 'v6',
                            e.created = datetime(),
                            e.{ENT.JINA_VEC_V3} = $embedding,
                            e.{ENT.HAS_EMBEDDING} = $has_embedding,
                            e.{ENT.EMBEDDING_MODEL} = CASE WHEN $has_embedding THEN 'jina-embeddings-v3' ELSE null END,
                            e.{ENT.EMBEDDING_DIMENSIONS} = CASE WHEN $has_embedding THEN 256 ELSE null END
                    """,
                    name=entity_data['name'],
                    entityType=entity_data['entityType'],
                    embedding=entity_embedding,
                    has_embedding=entity_has_embedding)

                    # Create observation nodes for each observation
                    for obs_content in entity_data.get('observations', []):
                        # Use general theme for now (avoid potential recursion in classifier)
                        theme = 'general'

                        # Generate embedding (with lazy initialization and feature flag check)
                        embedding_vector = None
                        has_embedding = False
                        # Direct flag access to avoid recursion bug in is_enabled()
                        embedding_flag = self.feature_flags.flags.get('v6_embedding_generation') if self.feature_flags else None
                        embedding_enabled = embedding_flag.enabled if embedding_flag else False

                        if embedding_enabled:
                            if not self.embedder and jina_embedder_available:
                                try:
                                    logger.info("🔄 Lazy-initializing JinaV3 embedder...")
                                    self.embedder = JinaV3OptimizedEmbedder()
                                    self.embedder.initialize()
                                    logger.info("✅ JinaV3 embedder lazy-initialized successfully")
                                except Exception as e:
                                    logger.error(f"❌ JinaV3 lazy initialization failed: {e}")
                                    self.embedder = None

                            if self.embedder:
                                try:
                                    embedding_vector = self.embedder.encode_single(obs_content, normalize=True)
                                    has_embedding = True
                                except Exception as e:
                                    logger.warning(f"⚠️ Embedding generation failed: {e}")

                        # Create observation node with canonical schema properties
                        obs_result = db_session.run(f"""
                            CREATE (o:Observation:Perennial:Entity {{
                                id: randomUUID(),
                                {OBS.CONTENT}: $content,
                                timestamp: datetime(),
                                source: 'mcp_tool',
                                created_by: 'perennial_v6_mcp_bridge',
                                {OBS.CONVERSATION_ID}: $session_id,
                                {OBS.SEMANTIC_THEME}: $theme,
                                {OBS.JINA_VEC_V3}: $embedding_vector,
                                {OBS.HAS_EMBEDDING}: $has_embedding,
                                {OBS.EMBEDDING_MODEL}: CASE WHEN $has_embedding THEN 'jina-embeddings-v3' ELSE null END,
                                {OBS.EMBEDDING_DIMENSIONS}: CASE WHEN $has_embedding THEN 256 ELSE null END
                            }})

                            WITH o
                            MATCH (entity:Entity {{name: $entity_name}})
                            MATCH (session:ConversationSession {{session_id: $session_id}})

                            // Core relationships (canonical schema)
                            MERGE (entity)-[:{RELS.ENTITY_HAS_OBSERVATION}]->(o)
                            MERGE (session)-[:{RELS.CONVERSATION_SESSION_ADDED_OBSERVATION}]->(entity)

                            // Temporal binding (canonical schema)
                            MERGE (day:Day {{date: date()}})
                            MERGE (o)-[:{RELS.OCCURRED_ON}]->(day)

                            RETURN o.id as observation_id
                        """,
                        content=obs_content,
                        entity_name=entity_data['name'],
                        session_id=session_data['session_id'],
                        theme=theme,
                        embedding_vector=embedding_vector,
                        has_embedding=has_embedding
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

    def ensure_temporal_hierarchy(self, date_str: str) -> bool:
        """
        Ensure Day→Month→Year temporal hierarchy exists for a given date.

        Implements V6 Compliance Audit Standard Requirement 9:
        - Day nodes must connect to Month nodes via PART_OF_MONTH
        - Month nodes must connect to Year nodes via PART_OF_YEAR

        Args:
            date_str: ISO 8601 date string (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS.sssZ)

        Returns:
            bool: True if hierarchy exists or was created successfully

        Reference: /llm/memory/perennial/docs/standards/V6_COMPLIANCE_AUDIT_STANDARDS.md
        """
        try:
            # Parse date from ISO 8601 format
            if 'T' in date_str:
                date_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            else:
                date_obj = datetime.strptime(date_str, '%Y-%m-%d')

            year = date_obj.year
            month = date_obj.month
            day = date_obj.day

            # Ensure Day→Month→Year hierarchy (CANONICAL V6 SCHEMA - fixed Oct 18, 2025)
            with self.driver.session() as session:
                year_month_str = f"{year}-{month:02d}"
                date_str_formatted = f"{year}-{month:02d}-{day:02d}"

                session.run("""
                    // Ensure Day node exists (canonical schema: date as primary key)
                    MERGE (d:Day {date: $date_str})
                    ON CREATE SET d.year = $year, d.month = $month, d.day = $day

                    // Ensure Month node exists (canonical schema: date in YYYY-MM format)
                    MERGE (m:Month {date: $year_month})
                    ON CREATE SET m.month = $month, m.year = $year

                    // Ensure Year node exists
                    MERGE (y:Year {year: $year})

                    // Create Day→Month relationship
                    MERGE (d)-[:PART_OF_MONTH]->(m)

                    // Create Month→Year relationship
                    MERGE (m)-[:PART_OF_YEAR]->(y)
                """, year=year, month=month, day=day, date_str=date_str_formatted, year_month=year_month_str)

            logger.debug(f"✅ Temporal hierarchy ensured for {year}-{month:02d}-{day:02d}")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to ensure temporal hierarchy for {date_str}: {e}")
            return False

    def validate_v6_compliance(self, observation_ids: List[str]) -> Dict:
        """
        Validate observations against V6 Compliance Audit Standards (11 requirements).

        Implements automated enforcement of:
        - /llm/memory/perennial/docs/standards/V6_COMPLIANCE_AUDIT_STANDARDS.md

        This method runs after observation creation to verify:
        1. V6 Node Labels (Observation:Perennial:Entity)
        2. content property exists
        3. created_at property (ISO 8601 format)
        4. jina_vec_v3 embeddings (256D)
        5. semantic_theme property
        6. conversation_id property (for conversation-derived observations)
        7. No V5 legacy properties (timestamp, theme)
        8. ENTITY_HAS_OBSERVATION relationships exist
        9. OCCURRED_ON temporal relationships exist
        10. Day→Month→Year hierarchy complete
        11. CONVERSATION_SESSION_ADDED_OBSERVATION (when applicable)

        Args:
            observation_ids: List of observation node IDs to validate

        Returns:
            Dict with compliance status and any violations found
        """
        try:
            violations = []
            compliant_count = 0

            with self.driver.session() as session:
                for obs_id in observation_ids:
                    # Query observation properties and relationships
                    result = session.run("""
                        MATCH (o:Observation)
                        WHERE elementId(o) = $obs_id
                        OPTIONAL MATCH (o)-[:ENTITY_HAS_OBSERVATION]-(e)
                        OPTIONAL MATCH (o)-[:OCCURRED_ON]->(d:Day)
                        OPTIONAL MATCH (d)-[:PART_OF_MONTH]->(m:Month)
                        OPTIONAL MATCH (m)-[:PART_OF_YEAR]->(y:Year)
                        OPTIONAL MATCH (cs:ConversationSession)-[:CONVERSATION_SESSION_ADDED_OBSERVATION]->(o)
                        RETURN
                            o,
                            labels(o) as labels,
                            count(e) as entity_count,
                            d, m, y,
                            cs.session_id as conversation_session_id
                    """, obs_id=obs_id).single()

                    if not result:
                        violations.append(f"Observation {obs_id} not found")
                        continue

                    obs = result['o']
                    obs_labels = result['labels']

                    # Requirement 1: V6 Node Labels
                    if not ('Observation' in obs_labels and 'Perennial' in obs_labels and 'Entity' in obs_labels):
                        violations.append(f"{obs_id}: Missing V6 labels (got {obs_labels})")

                    # Requirement 2: content property
                    if not obs.get('content'):
                        violations.append(f"{obs_id}: Missing content property")

                    # Requirement 3: created_at (ISO 8601)
                    created_at = obs.get('created_at')
                    if not created_at:
                        violations.append(f"{obs_id}: Missing created_at property")
                    elif not isinstance(created_at, str) or not created_at.endswith('Z'):
                        violations.append(f"{obs_id}: created_at not ISO 8601 format: {created_at}")

                    # Requirement 4: jina_vec_v3 embeddings
                    embedding = obs.get('jina_vec_v3')
                    if not embedding:
                        violations.append(f"{obs_id}: Missing jina_vec_v3 embedding")
                    elif len(embedding) != 256:
                        violations.append(f"{obs_id}: Invalid embedding dimensions: {len(embedding)} (expected 256)")

                    # Requirement 5: semantic_theme
                    if not obs.get('semantic_theme'):
                        violations.append(f"{obs_id}: Missing semantic_theme property")

                    # Requirement 6: conversation_id (for MCP-created observations)
                    source = obs.get('source', '')
                    if source in ['mcp_tool', 'perennial_v6_mcp_bridge'] and not obs.get('conversation_id'):
                        violations.append(f"{obs_id}: Missing conversation_id (source: {source})")

                    # Requirement 7: No V5 legacy properties
                    if obs.get('timestamp'):
                        violations.append(f"{obs_id}: Has V5 timestamp property (should be created_at)")
                    if obs.get('theme'):
                        violations.append(f"{obs_id}: Has V5 theme property (should be semantic_theme)")

                    # Requirement 8: ENTITY_HAS_OBSERVATION relationship
                    if result['entity_count'] == 0:
                        violations.append(f"{obs_id}: No ENTITY_HAS_OBSERVATION relationship")

                    # Requirement 9: OCCURRED_ON temporal relationship + hierarchy
                    if not result['d']:
                        violations.append(f"{obs_id}: Missing OCCURRED_ON → Day relationship")
                    elif not result['m']:
                        violations.append(f"{obs_id}: Day node missing PART_OF_MONTH → Month")
                        # Auto-fix: ensure temporal hierarchy
                        if created_at:
                            self.ensure_temporal_hierarchy(created_at)
                    elif not result['y']:
                        violations.append(f"{obs_id}: Month node missing PART_OF_YEAR → Year")
                        # Auto-fix: ensure temporal hierarchy
                        if created_at:
                            self.ensure_temporal_hierarchy(created_at)

                    # Requirement 10: CONVERSATION_SESSION_ADDED_OBSERVATION (if in conversation)
                    if obs.get('conversation_id') and not result['conversation_session_id']:
                        violations.append(f"{obs_id}: Has conversation_id but no CONVERSATION_SESSION_ADDED_OBSERVATION")

                    # If no violations for this observation, it's compliant
                    if not any(v.startswith(obs_id) for v in violations):
                        compliant_count += 1

            total_validated = len(observation_ids)
            compliance_percentage = (compliant_count / total_validated * 100) if total_validated > 0 else 0

            return {
                'compliant': len(violations) == 0,
                'total_validated': total_validated,
                'compliant_count': compliant_count,
                'compliance_percentage': compliance_percentage,
                'violations': violations,
                'auto_fixes_applied': sum(1 for v in violations if 'Auto-fix' in v),
                'validated_at': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"❌ V6 compliance validation failed: {e}")
            return {
                'compliant': False,
                'error': str(e),
                'validated_at': datetime.now().isoformat()
            }

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
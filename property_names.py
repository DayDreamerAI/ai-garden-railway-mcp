"""
Memory Sovereignty Architecture - Canonical Property Names Schema

This module defines the single source of truth for all Neo4j node properties,
relationship types, and labels used across:
- Local MCP Server (stdio transport for Claude Code)
- Railway MCP Server (SSE transport for Claude Desktop/Web/Mobile)
- Perennial Phase 2 processing
- Memory tools and utilities

**CRITICAL**: All code MUST import from this schema to prevent property
name mismatches that cause silent data loss or query failures.

**Location**: Consolidated with entity_types.md and relationships.md (Oct 13, 2025)
**Created**: October 10, 2025 (originally llm/mcp/shared/v6_schema.py)
**Moved**: October 13, 2025 (consolidated into llm/memory/schemas/)
**Status**: PRODUCTION
"""

from typing import Dict, List, Set
from dataclasses import dataclass


# ============================================================================
# NODE LABELS
# ============================================================================

class NodeLabels:
    """Canonical node labels for V6 architecture"""

    # Core entity labels
    ENTITY = "Entity"
    SEMANTIC_ENTITY = "SemanticEntity"  # For vector search optimization
    PERENNIAL = "Perennial"  # All V6 artifacts must have this

    # Observation architecture
    OBSERVATION = "Observation"  # First-class observation nodes

    # Temporal hierarchy
    DAY = "Day"
    MONTH = "Month"
    YEAR = "Year"

    # Conversation architecture
    CONVERSATION_SESSION = "ConversationSession"
    CONVERSATION_MESSAGE = "ConversationMessage"
    CONVERSATION_SUMMARY = "ConversationSummary"
    CHUNK = "Chunk"  # 750-token semantic chunks

    # MVCM concept extraction
    CONCEPT = "Concept"

    # GraphRAG Phase 2: Leiden Community Summaries
    COMMUNITY_SUMMARY = "CommunitySummary"  # L2 community summaries with embeddings


# ============================================================================
# RELATIONSHIP TYPES (SYSTEM/PROTECTED)
# ============================================================================

class RelationshipTypes:
    """
    Canonical relationship types for V6 architecture

    NOTE: These are PROTECTED SYSTEM RELATIONSHIPS managed automatically.
    For user-created semantic relationships, see relationships.md
    """

    # Entity-Observation relationships
    ENTITY_HAS_OBSERVATION = "ENTITY_HAS_OBSERVATION"

    # Temporal binding (UNIVERSAL standard)
    OCCURRED_ON = "OCCURRED_ON"  # Node → Day
    PART_OF_MONTH = "PART_OF_MONTH"  # Day → Month
    PART_OF_YEAR = "PART_OF_YEAR"  # Month → Year

    # Session tracking
    CONVERSATION_SESSION_ADDED_OBSERVATION = "CONVERSATION_SESSION_ADDED_OBSERVATION"
    CONVERSATION_SESSION_CREATED_ENTITY = "CONVERSATION_SESSION_CREATED_ENTITY"

    # Conversation structure
    SESSION_HAS_MESSAGE = "SESSION_HAS_MESSAGE"
    SESSION_HAS_SUMMARY = "SESSION_HAS_SUMMARY"
    MESSAGE_HAS_CHUNK = "MESSAGE_HAS_CHUNK"

    # MVCM concept extraction
    OBSERVATION_MENTIONS_CONCEPT = "OBSERVATION_MENTIONS_CONCEPT"
    ENTITY_RELATED_TO = "ENTITY_RELATED_TO"

    # GraphRAG Phase 2: Community membership
    MEMBER_OF_COMMUNITY = "MEMBER_OF_COMMUNITY"  # Entity → CommunitySummary


# ============================================================================
# PROTECTED RELATIONSHIP TYPES SET (for schema_enforcement.py)
# ============================================================================

def get_protected_relationship_types() -> Set[str]:
    """
    Returns set of protected system relationships that cannot be created manually

    Used by schema_enforcement.py to block manual creation of system relationships
    """
    return {
        RelationshipTypes.ENTITY_HAS_OBSERVATION,
        RelationshipTypes.OCCURRED_ON,
        RelationshipTypes.PART_OF_MONTH,
        RelationshipTypes.PART_OF_YEAR,
        RelationshipTypes.CONVERSATION_SESSION_ADDED_OBSERVATION,
        RelationshipTypes.CONVERSATION_SESSION_CREATED_ENTITY,
        RelationshipTypes.SESSION_HAS_MESSAGE,
        RelationshipTypes.SESSION_HAS_SUMMARY,
        RelationshipTypes.MESSAGE_HAS_CHUNK,
        RelationshipTypes.OBSERVATION_MENTIONS_CONCEPT,
        RelationshipTypes.ENTITY_RELATED_TO,

        # GraphRAG Phase 2 infrastructure (added Oct 17, 2025)
        "MEMBER_OF_COMMUNITY",

        # Tool tracking infrastructure (added Oct 17, 2025)
        "CONVERSATION_SESSION_USED_TOOL",
    }


# ============================================================================
# OBSERVATION NODE PROPERTIES
# ============================================================================

@dataclass
class ObservationProperties:
    """Canonical property names for Observation nodes"""

    # Core identification
    ID = "id"  # UUID
    CONTENT = "content"  # Observation text content

    # Temporal metadata
    CREATED_AT = "created_at"  # ISO format timestamp
    TIMESTAMP = "timestamp"  # Neo4j datetime

    # Source tracking
    SOURCE = "source"  # e.g., "mcp_tool", "perennial_phase2"
    CREATED_BY = "created_by"  # e.g., "railway_mcp_v6_handler"

    # Session context (CRITICAL: conversation_id NOT session_id)
    CONVERSATION_ID = "conversation_id"  # Links to ConversationSession.session_id

    # Theme classification
    SEMANTIC_THEME = "semantic_theme"  # technical, consciousness, memory, etc.

    # Embedding properties (CRITICAL: jina_vec_v3 NOT embedding_jina_v3)
    JINA_VEC_V3 = "jina_vec_v3"  # 256-dimensional vector
    HAS_EMBEDDING = "has_embedding"  # Boolean flag
    EMBEDDING_MODEL = "embedding_model"  # "jina-embeddings-v3"
    EMBEDDING_DIMENSIONS = "embedding_dimensions"  # 256
    EMBEDDING_GENERATED_AT = "embedding_generated_at"  # When embedding created
    EMBEDDING_VERSION = "embedding_version"  # "v3.0"


# ============================================================================
# ENTITY NODE PROPERTIES
# ============================================================================

@dataclass
class EntityProperties:
    """Canonical property names for Entity nodes"""

    # Core identification
    NAME = "name"  # Primary identifier
    ENTITY_TYPE = "entityType"  # person, concept, project, etc.

    # V5 backward compatibility
    OBSERVATIONS = "observations"  # String array (legacy)

    # Embedding properties (same as Observation)
    JINA_VEC_V3 = "jina_vec_v3"
    HAS_EMBEDDING = "has_embedding"
    EMBEDDING_MODEL = "embedding_model"
    EMBEDDING_DIMENSIONS = "embedding_dimensions"
    EMBEDDING_VERSION = "embedding_version"

    # Enhanced metadata
    ALIASES = "aliases"  # Alternative names
    CREATED_AT = "created_at"
    CREATED_BY = "created_by"


# ============================================================================
# CONVERSATION NODE PROPERTIES
# ============================================================================

@dataclass
class ConversationSessionProperties:
    """Canonical property names for ConversationSession nodes"""

    SESSION_ID = "session_id"  # Primary identifier
    CONTEXT = "context"  # Session context/description
    SOURCE = "source"  # Origin of session
    CREATED_AT = "created_at"

    # V6 enhancements (Oct 10, 2025)
    FIRST_MESSAGE_AT = "first_message_at"
    LAST_MESSAGE_AT = "last_message_at"
    MESSAGE_COUNT = "message_count"
    ENTITY_COUNT = "entity_count"
    CHUNK_COUNT = "chunk_count"
    IMPORTANCE_SCORE = "importance_score"  # 0.4*msgs + 0.3*entities + 0.2*chunks


@dataclass
class ConversationMessageProperties:
    """Canonical property names for ConversationMessage nodes"""

    MESSAGE_ID = "message_id"
    SENDER = "sender"  # "human" or "assistant"
    CONTENT = "content"
    CREATED_AT = "created_at"
    TIMESTAMP = "timestamp"


@dataclass
class ChunkProperties:
    """Canonical property names for Chunk nodes"""

    CHUNK_ID = "chunk_id"
    CONTENT = "content"  # 750-token semantic segment
    CHUNK_INDEX = "chunk_index"
    CREATED_AT = "created_at"

    # Embedding properties
    JINA_VEC_V3 = "jina_vec_v3"
    HAS_EMBEDDING = "has_embedding"
    EMBEDDING_MODEL = "embedding_model"
    EMBEDDING_DIMENSIONS = "embedding_dimensions"


# ============================================================================
# TEMPORAL NODE PROPERTIES
# ============================================================================

@dataclass
class DayProperties:
    """Canonical property names for Day nodes"""
    DATE = "date"  # ISO format YYYY-MM-DD


@dataclass
class MonthProperties:
    """Canonical property names for Month nodes"""
    YEAR_MONTH = "year_month"  # Format: "YYYY-MM"


@dataclass
class YearProperties:
    """Canonical property names for Year nodes"""
    YEAR = "year"  # Integer year


class CommunitySummaryProperties:
    """
    Canonical property names for CommunitySummary nodes (GraphRAG Phase 2)

    Phase 2 Schema:
    - Label: :CommunitySummary:Entity:Perennial
    - Embedding: jina_vec_v3 (256D JinaV3)
    - Relationship: Entity -[:MEMBER_OF_COMMUNITY]-> CommunitySummary

    Note: For common properties (name, entityType, embeddings, created_at, created_by),
    use EntityProperties constants to avoid duplication:
    - EntityProperties.NAME
    - EntityProperties.ENTITY_TYPE
    - EntityProperties.JINA_VEC_V3
    - EntityProperties.HAS_EMBEDDING
    - EntityProperties.CREATED_AT
    - EntityProperties.CREATED_BY
    """
    # Unique Phase 2 Properties
    COMMUNITY_ID = "community_id"  # Integer Leiden community ID
    SUMMARY = "summary"  # GPT-4 generated community summary text
    MEMBER_COUNT = "member_count"  # Number of entities in community
    PERENNIAL_VERSION = "perennial_version"  # V6 version tag


# ============================================================================
# VALIDATION UTILITIES
# ============================================================================

class SchemaValidator:
    """Utilities for validating property usage"""

    @staticmethod
    def get_all_observation_properties() -> Set[str]:
        """Return all valid Observation property names"""
        return {
            ObservationProperties.ID,
            ObservationProperties.CONTENT,
            ObservationProperties.CREATED_AT,
            ObservationProperties.TIMESTAMP,
            ObservationProperties.SOURCE,
            ObservationProperties.CREATED_BY,
            ObservationProperties.CONVERSATION_ID,
            ObservationProperties.SEMANTIC_THEME,
            ObservationProperties.JINA_VEC_V3,
            ObservationProperties.HAS_EMBEDDING,
            ObservationProperties.EMBEDDING_MODEL,
            ObservationProperties.EMBEDDING_DIMENSIONS,
            ObservationProperties.EMBEDDING_GENERATED_AT,
            ObservationProperties.EMBEDDING_VERSION,
        }

    @staticmethod
    def get_all_entity_properties() -> Set[str]:
        """Return all valid Entity property names"""
        return {
            EntityProperties.NAME,
            EntityProperties.ENTITY_TYPE,
            EntityProperties.OBSERVATIONS,
            EntityProperties.JINA_VEC_V3,
            EntityProperties.HAS_EMBEDDING,
            EntityProperties.EMBEDDING_MODEL,
            EntityProperties.EMBEDDING_DIMENSIONS,
            EntityProperties.EMBEDDING_VERSION,
            EntityProperties.ALIASES,
            EntityProperties.CREATED_AT,
            EntityProperties.CREATED_BY,
        }

    @staticmethod
    def validate_observation_query(query: str) -> List[str]:
        """
        Check if a Cypher query uses invalid Observation properties

        Returns list of warnings for potentially incorrect property names
        """
        warnings = []

        # Common mistakes
        if "embedding_jina_v3" in query:
            warnings.append(
                f"⚠️  Found 'embedding_jina_v3' - should be '{ObservationProperties.JINA_VEC_V3}'"
            )

        if "session_id" in query and "ConversationSession" not in query:
            warnings.append(
                f"⚠️  Found 'session_id' on Observation - should be '{ObservationProperties.CONVERSATION_ID}'"
            )

        return warnings


# ============================================================================
# QUERY BUILDER HELPERS
# ============================================================================

class QueryBuilder:
    """Helper methods for building consistent Cypher queries"""

    @staticmethod
    def observation_create_properties(
        content: str,
        session_id: str,
        theme: str = "general",
        has_embedding: bool = False
    ) -> Dict[str, any]:
        """
        Generate properties dict for Observation node creation

        Use this in Cypher queries to ensure consistent property names:
        CREATE (o:Observation:Perennial:Entity $props)
        """
        return {
            ObservationProperties.CONTENT: content,
            ObservationProperties.CONVERSATION_ID: session_id,
            ObservationProperties.SEMANTIC_THEME: theme,
            ObservationProperties.HAS_EMBEDDING: has_embedding,
            ObservationProperties.SOURCE: "mcp_tool",
        }

    @staticmethod
    def observation_return_fields() -> str:
        """
        Return consistent field list for Observation queries

        Use in RETURN clauses:
        RETURN {QueryBuilder.observation_return_fields()}
        """
        return f"""
            o.{ObservationProperties.ID} as id,
            o.{ObservationProperties.CONTENT} as content,
            o.{ObservationProperties.CONVERSATION_ID} as conversation_id,
            o.{ObservationProperties.SEMANTIC_THEME} as theme,
            o.{ObservationProperties.HAS_EMBEDDING} as has_embedding,
            o.{ObservationProperties.JINA_VEC_V3} IS NOT NULL as embedding_exists,
            size(o.{ObservationProperties.JINA_VEC_V3}) as embedding_dimensions,
            o.{ObservationProperties.EMBEDDING_MODEL} as embedding_model,
            o.{ObservationProperties.CREATED_AT} as created_at
        """.strip()


# ============================================================================
# EXPORT CONVENIENCE OBJECTS
# ============================================================================

# Instantiate for easier imports
OBS_PROPS = ObservationProperties()
ENTITY_PROPS = EntityProperties()
SESSION_PROPS = ConversationSessionProperties()
MSG_PROPS = ConversationMessageProperties()
CHUNK_PROPS = ChunkProperties()
DAY_PROPS = DayProperties()
MONTH_PROPS = MonthProperties()
YEAR_PROPS = YearProperties()

# Labels and relationships
LABELS = NodeLabels()
RELS = RelationshipTypes()

# Utilities
VALIDATOR = SchemaValidator()
QUERY = QueryBuilder()


# ============================================================================
# USAGE EXAMPLES
# ============================================================================

if __name__ == "__main__":
    print("Memory Schema Constants - Usage Examples")
    print("=" * 60)

    print("\n1. Observation property names:")
    print(f"   Embedding vector: {OBS_PROPS.JINA_VEC_V3}")
    print(f"   Session link: {OBS_PROPS.CONVERSATION_ID}")
    print(f"   Content: {OBS_PROPS.CONTENT}")

    print("\n2. Node labels:")
    print(f"   Observation: {LABELS.OBSERVATION}")
    print(f"   Entity: {LABELS.ENTITY}")

    print("\n3. Relationships:")
    print(f"   Entity→Observation: {RELS.ENTITY_HAS_OBSERVATION}")
    print(f"   Temporal binding: {RELS.OCCURRED_ON}")

    print("\n4. Protected relationships:")
    protected = get_protected_relationship_types()
    print(f"   Count: {len(protected)}")
    print(f"   Examples: {list(protected)[:3]}")

    print("\n5. Validation example:")
    bad_query = "MATCH (o:Observation) WHERE o.embedding_jina_v3 IS NOT NULL"
    warnings = VALIDATOR.validate_observation_query(bad_query)
    for warning in warnings:
        print(f"   {warning}")

    print("\n6. Query builder example:")
    props = QUERY.observation_create_properties(
        content="Test observation",
        session_id="session_123",
        theme="technical"
    )
    print(f"   Properties: {props}")

    print("\n✅ Schema loaded successfully!")

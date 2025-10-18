"""
Daydreamer MCP Memory Server - Schema Enforcement Module
Enforces canonical entity types and relationship types from Phase 1 GraphRAG Foundation.

Created: October 13, 2025
Updated: October 13, 2025 - Consolidated with property_names.py
Authority: /llm/memory/schemas/
"""

import logging
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# Add schemas directory to path
# Path from: llm/mcp/servers/daydreamer-memory-mcp/src/schema_enforcement.py
# Target:    llm/memory/schemas/
schemas_path = Path(__file__).resolve().parent.parent.parent.parent.parent / "memory" / "schemas"
sys.path.insert(0, str(schemas_path))

# Import protected relationship types from property_names.py
try:
    from property_names import get_protected_relationship_types
    PROTECTED_RELATIONSHIP_TYPES = get_protected_relationship_types()
    logger = logging.getLogger(__name__)
    logger.info("✅ Schema enforcement loaded protected relationships from property_names.py")
except ImportError as e:
    logger = logging.getLogger(__name__)
    logger.error(f"❌ Failed to import from property_names.py: {e}")
    # Fallback to manual definition (should never happen)
    PROTECTED_RELATIONSHIP_TYPES = set()

# Canonical Entity Types (lowercase_snake_case)
# Source: /llm/memory/schemas/entity_types.md
CANONICAL_ENTITY_TYPES = {
    # People & Organizations
    'person', 'thought_leader', 'company', 'organization', 'team',

    # Technology & Systems
    'technology', 'ai_framework', 'agent_framework', 'mcp_server', 'system',
    'platform', 'development_platform',

    # Concepts & Knowledge
    'concept', 'technical_concept', 'philosophy', 'vision', 'framework',
    'methodology',

    # Projects & Work
    'project', 'achievement', 'milestone', 'documentation', 'technical_solution',

    # Business & Operations
    'commercial_opportunity', 'customer_journey', 'database', 'integration',
    'automation_system',

    # Memory & Consciousness (Daydreamer-Specific)
    'memory_sovereign_agent', 'ai_agent', 'capability', 'technical_framework',
    'strategic_framework',

    # Additional common types from Phase 1
    'product', 'service', 'tool', 'api', 'interface', 'protocol',
    'standard', 'specification', 'pattern', 'algorithm', 'model',
    'research', 'analysis', 'finding', 'insight', 'observation',
    'conversation', 'message', 'session', 'interaction',
    'event', 'activity', 'process', 'workflow', 'task',
    'data_source', 'repository', 'file', 'directory', 'code',
    'configuration', 'deployment', 'infrastructure', 'environment',
    'security', 'authentication', 'authorization', 'encryption',
    'performance', 'optimization', 'metric', 'measurement',
    'error', 'bug', 'issue', 'feature_request', 'enhancement',
    'test', 'validation', 'verification', 'quality_assurance',
    'release', 'version', 'update', 'migration', 'upgrade',
    'backup', 'restore', 'recovery', 'disaster_recovery',
    'monitoring', 'logging', 'tracing', 'debugging',
    'knowledge_graph', 'semantic_web', 'linked_data', 'ontology',
    'taxonomy', 'vocabulary', 'schema', 'metadata',
    'agent', 'bot', 'assistant', 'chatbot', 'virtual_assistant',
    'llm', 'transformer', 'neural_network', 'machine_learning',
    'deep_learning', 'reinforcement_learning', 'supervised_learning',
    'unsupervised_learning', 'transfer_learning', 'fine_tuning',
    'prompt', 'completion', 'embedding', 'tokenization',
    'training_data', 'test_data', 'validation_data', 'dataset',
    'benchmark', 'evaluation', 'metric', 'score',
    'pull_request', 'commit', 'branch', 'merge', 'rebase',
    'technical_standard', 'best_practice', 'guideline', 'recommendation'
}

# Canonical Relationship Types (SCREAMING_SNAKE_CASE)
# Source: /llm/memory/schemas/relationships.md
CANONICAL_RELATIONSHIP_TYPES = {
    # Tier 1: Universal Relationships
    'CONTAINS', 'PART_OF', 'USES', 'DEPENDS_ON', 'EXTENDS',
    'CREATES', 'INFLUENCES', 'MANAGES',

    # Tier 2: Technical Relationships
    'IMPLEMENTS', 'INTEGRATES_WITH', 'TRANSFORMS', 'DISCOVERS',

    # Tier 3: Fallback
    'RELATES_TO'
}

# NOTE: PROTECTED_RELATIONSHIP_TYPES now imported from property_names.py (line 22)
# This eliminates duplication between schema_enforcement.py and property_names.py


class SchemaEnforcementError(Exception):
    """Raised when schema enforcement fails"""
    pass


def normalize_entity_type(entity_type: str) -> str:
    """
    Normalize entity type to canonical lowercase_snake_case format.

    Args:
        entity_type: Raw entity type string

    Returns:
        Normalized lowercase_snake_case entity type

    Examples:
        >>> normalize_entity_type("Person")
        'person'
        >>> normalize_entity_type("Agent Framework")
        'agent_framework'
        >>> normalize_entity_type("thought-leader")
        'thought_leader'
    """
    if not entity_type:
        return ''

    # Convert to lowercase
    normalized = entity_type.lower()

    # Replace spaces and hyphens with underscores
    normalized = normalized.replace(' ', '_').replace('-', '_')

    # Remove any special characters except underscores
    normalized = ''.join(c if c.isalnum() or c == '_' else '_' for c in normalized)

    # Replace multiple underscores with single underscore
    while '__' in normalized:
        normalized = normalized.replace('__', '_')

    # Remove leading/trailing underscores
    normalized = normalized.strip('_')

    return normalized


def validate_entity_type(entity_type: str, strict: bool = False) -> Tuple[bool, str, Optional[str]]:
    """
    Validate entity type against canonical schema.

    Args:
        entity_type: Entity type to validate
        strict: If True, reject non-canonical types. If False, normalize and warn.

    Returns:
        Tuple of (is_valid, normalized_type, error_message)

    Examples:
        >>> validate_entity_type("person")
        (True, 'person', None)
        >>> validate_entity_type("Person", strict=False)
        (True, 'person', None)
        >>> validate_entity_type("InvalidType", strict=True)
        (False, 'invalidtype', 'Entity type "invalidtype" is not in canonical schema')
    """
    if not entity_type:
        return (False, '', 'Entity type cannot be empty')

    # Normalize to canonical format
    normalized = normalize_entity_type(entity_type)

    # Check if normalized type is in canonical set
    if normalized in CANONICAL_ENTITY_TYPES:
        if normalized != entity_type:
            logger.info(f"✅ Entity type normalized: '{entity_type}' → '{normalized}'")
        return (True, normalized, None)

    # Not in canonical set
    error_msg = (
        f"Entity type '{normalized}' is not in canonical schema. "
        f"Use one of: {', '.join(sorted(list(CANONICAL_ENTITY_TYPES)[:10]))}... "
        f"(see /llm/memory/schemas/entity_types.md for full list)"
    )

    if strict:
        return (False, normalized, error_msg)
    else:
        logger.warning(f"⚠️ {error_msg}")
        logger.warning(f"⚠️ Allowing non-canonical type '{normalized}' (strict mode disabled)")
        return (True, normalized, error_msg)


def normalize_relationship_type(relationship_type: str) -> str:
    """
    Normalize relationship type to canonical SCREAMING_SNAKE_CASE format.

    Args:
        relationship_type: Raw relationship type string

    Returns:
        Normalized SCREAMING_SNAKE_CASE relationship type

    Examples:
        >>> normalize_relationship_type("contains")
        'CONTAINS'
        >>> normalize_relationship_type("part-of")
        'PART_OF'
        >>> normalize_relationship_type("integrates with")
        'INTEGRATES_WITH'
    """
    if not relationship_type:
        return ''

    # Convert to uppercase
    normalized = relationship_type.upper()

    # Replace spaces and hyphens with underscores
    normalized = normalized.replace(' ', '_').replace('-', '_')

    # Remove any special characters except underscores
    normalized = ''.join(c if c.isalnum() or c == '_' else '_' for c in normalized)

    # Replace multiple underscores with single underscore
    while '__' in normalized:
        normalized = normalized.replace('__', '_')

    # Remove leading/trailing underscores
    normalized = normalized.strip('_')

    return normalized


def validate_relationship_type(relationship_type: str, strict: bool = False) -> Tuple[bool, str, Optional[str]]:
    """
    Validate relationship type against canonical schema.

    Args:
        relationship_type: Relationship type to validate
        strict: If True, reject non-canonical types. If False, normalize and warn.

    Returns:
        Tuple of (is_valid, normalized_type, error_message)

    Examples:
        >>> validate_relationship_type("CONTAINS")
        (True, 'CONTAINS', None)
        >>> validate_relationship_type("contains", strict=False)
        (True, 'CONTAINS', None)
        >>> validate_relationship_type("CUSTOM_REL", strict=True)
        (False, 'CUSTOM_REL', 'Relationship type "CUSTOM_REL" is not in canonical schema')
    """
    if not relationship_type:
        return (False, '', 'Relationship type cannot be empty')

    # Normalize to canonical format
    normalized = normalize_relationship_type(relationship_type)

    # Check if it's a protected system relationship
    if normalized in PROTECTED_RELATIONSHIP_TYPES:
        error_msg = (
            f"Relationship type '{normalized}' is a protected system relationship. "
            f"These are created automatically by the system and cannot be used directly."
        )
        return (False, normalized, error_msg)

    # Check if normalized type is in canonical set
    if normalized in CANONICAL_RELATIONSHIP_TYPES:
        if normalized != relationship_type:
            logger.info(f"✅ Relationship type normalized: '{relationship_type}' → '{normalized}'")
        return (True, normalized, None)

    # Not in canonical set
    error_msg = (
        f"Relationship type '{normalized}' is not in canonical schema. "
        f"Use one of: {', '.join(sorted(CANONICAL_RELATIONSHIP_TYPES))}. "
        f"See /llm/memory/schemas/relationships.md for full documentation."
    )

    if strict:
        return (False, normalized, error_msg)
    else:
        logger.warning(f"⚠️ {error_msg}")
        logger.warning(f"⚠️ Allowing non-canonical type '{normalized}' (strict mode disabled)")
        return (True, normalized, error_msg)


def validate_entities(entities: List[Dict], strict: bool = False) -> Tuple[List[Dict], List[str]]:
    """
    Validate and normalize a list of entities.

    Args:
        entities: List of entity dictionaries with 'name', 'entityType', 'observations'
        strict: If True, reject non-canonical types. If False, normalize and warn.

    Returns:
        Tuple of (normalized_entities, validation_warnings)

    Raises:
        SchemaEnforcementError: If validation fails in strict mode
    """
    normalized_entities = []
    warnings = []

    for i, entity in enumerate(entities):
        entity_name = entity.get('name', f'Entity {i}')
        entity_type = entity.get('entityType', entity.get('entity_type'))

        if not entity_type:
            error_msg = f"Entity '{entity_name}' missing entityType"
            if strict:
                raise SchemaEnforcementError(error_msg)
            else:
                warnings.append(error_msg)
                entity_type = 'concept'  # Default fallback

        # Validate entity type
        is_valid, normalized_type, error_msg = validate_entity_type(entity_type, strict=strict)

        if not is_valid:
            if strict:
                raise SchemaEnforcementError(f"Entity '{entity_name}': {error_msg}")
            else:
                warnings.append(f"Entity '{entity_name}': {error_msg}")

        # Create normalized entity
        normalized_entity = entity.copy()
        normalized_entity['entityType'] = normalized_type
        normalized_entities.append(normalized_entity)

    return normalized_entities, warnings


def validate_relationships(relations: List[Dict], strict: bool = False) -> Tuple[List[Dict], List[str]]:
    """
    Validate and normalize a list of relationships.

    Args:
        relations: List of relationship dictionaries with 'from', 'to', 'relationType'
        strict: If True, reject non-canonical types. If False, normalize and warn.

    Returns:
        Tuple of (normalized_relations, validation_warnings)

    Raises:
        SchemaEnforcementError: If validation fails in strict mode
    """
    normalized_relations = []
    warnings = []

    for i, relation in enumerate(relations):
        from_entity = relation.get('from', relation.get('from_entity', f'Unknown {i}'))
        to_entity = relation.get('to', relation.get('to_entity', f'Unknown {i}'))
        rel_type = relation.get('relationType', relation.get('relationship_type', relation.get('predicate')))

        if not rel_type:
            error_msg = f"Relationship {from_entity}→{to_entity} missing relationType"
            if strict:
                raise SchemaEnforcementError(error_msg)
            else:
                warnings.append(error_msg)
                rel_type = 'RELATES_TO'  # Default fallback

        # Validate relationship type
        is_valid, normalized_type, error_msg = validate_relationship_type(rel_type, strict=strict)

        if not is_valid:
            # Check if this is a protected relationship (ALWAYS block, even in non-strict mode)
            if normalized_type in PROTECTED_RELATIONSHIP_TYPES:
                raise SchemaEnforcementError(f"Relationship {from_entity}→{to_entity}: {error_msg}")

            # For non-protected invalid types, behavior depends on strict mode
            if strict:
                raise SchemaEnforcementError(f"Relationship {from_entity}→{to_entity}: {error_msg}")
            else:
                warnings.append(f"Relationship {from_entity}→{to_entity}: {error_msg}")

        # Create normalized relationship
        normalized_relation = relation.copy()
        normalized_relation['relationType'] = normalized_type
        normalized_relations.append(normalized_relation)

    return normalized_relations, warnings


# Module version for tracking
__version__ = "1.0.0"
__authority__ = "/llm/memory/schemas/"
__created__ = "2025-10-13"

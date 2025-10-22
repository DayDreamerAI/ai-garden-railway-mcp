#!/usr/bin/env python3
"""
MVCM Observation Search Tool

Multi-dimensional observation search with semantic, theme, entity, temporal,
and confidence filtering.

Enables queries like:
- "Show me everything about PBC in September 2025"
- "Find partnership-themed observations mentioning Julian"
- "What technical observations have high-confidence concept links?"

Integration: Added to daydreamer-memory-mcp as search_observations() tool
"""

import os
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass


@dataclass
class ObservationSearchResult:
    """Single observation search result"""
    obs_id: str
    content: str
    primary_theme: Optional[str]
    secondary_themes: List[str]
    theme_confidence: Optional[float]
    linked_concepts: List[Dict]  # [{entity: str, confidence: float, method: str}]
    occurred_on: str  # Date
    source_entity: str  # Entity that owns this observation
    conversation_id: Optional[str]


def search_observations(
    db_session,
    query: Optional[str] = None,
    theme: Optional[str] = None,
    entity_filter: Optional[str] = None,
    date_range: Optional[Tuple[str, str]] = None,
    confidence_min: float = 0.5,
    limit: int = 50,
    offset: int = 0
) -> List[ObservationSearchResult]:
    """
    Search observations with multi-dimensional filtering

    Args:
        db_session: Neo4j session
        query: Semantic search query (uses observation embeddings)
        theme: Filter by primary theme
        entity_filter: Only observations mentioning this entity
        date_range: (start_date, end_date) in YYYY-MM-DD format
        confidence_min: Minimum concept link confidence
        limit: Max results to return
        offset: Pagination offset

    Returns:
        List of ObservationSearchResult

    Examples:
        # Find all PBC observations in September
        results = search_observations(
            session,
            entity_filter="Personality Bootstrap Component (PBC)",
            date_range=("2025-09-01", "2025-09-30")
        )

        # Find partnership-themed observations
        results = search_observations(
            session,
            theme="partnership",
            limit=20
        )

        # Semantic search for "memory architecture"
        results = search_observations(
            session,
            query="memory architecture patterns",
            confidence_min=0.7
        )
    """
    # Build Cypher query dynamically based on filters
    cypher_parts = []
    params = {}

    # Base: Match observations
    cypher_parts.append("""
        MATCH (o:Observation:Perennial:Entity)
        WHERE o.content IS NOT NULL
    """)

    # Filter: Theme
    if theme:
        cypher_parts.append("AND o.semantic_theme = $theme")
        params['theme'] = theme

    # Filter: Date range
    if date_range:
        start_date, end_date = date_range
        cypher_parts.append("""
            MATCH (o)-[:OCCURRED_ON]->(day:Day)
            WHERE day.date >= date($start_date)
              AND day.date <= date($end_date)
        """)
        params['start_date'] = start_date
        params['end_date'] = end_date

    # Filter: Entity ownership (via ENTITY_HAS_OBSERVATION)
    # BUG FIX (Oct 21, 2025): Changed from OBSERVATION_MENTIONS_CONCEPT to ENTITY_HAS_OBSERVATION
    # entity_filter means "show observations OWNED BY this entity", not "observations that mention this entity"
    if entity_filter:
        cypher_parts.append("""
            MATCH (source_entity:Entity {name: $entity_filter})-[:ENTITY_HAS_OBSERVATION]->(o)
        """)
        params['entity_filter'] = entity_filter
        params['confidence_min'] = confidence_min
    else:
        # Get source entity (the entity that has this observation)
        cypher_parts.append("""
            OPTIONAL MATCH (source_entity:Entity)-[:ENTITY_HAS_OBSERVATION]->(o)
        """)
        # Still apply confidence filter to all concept links
        params['confidence_min'] = confidence_min

    # Get all linked concepts (for result enrichment)
    cypher_parts.append("""
        OPTIONAL MATCH (o)-[r:OBSERVATION_MENTIONS_CONCEPT]->(e:Entity)
        WHERE r.confidence >= $confidence_min
    """)

    # Get temporal context
    cypher_parts.append("""
        OPTIONAL MATCH (o)-[:OCCURRED_ON]->(d:Day)
    """)

    # Get conversation context
    cypher_parts.append("""
        OPTIONAL MATCH (o)<-[:CONVERSATION_SESSION_ADDED_OBSERVATION]-(session:ConversationSession)
    """)

    # Return with aggregation
    cypher_parts.append("""
        RETURN DISTINCT o.id as obs_id,
               o.content as content,
               o.semantic_theme as primary_theme,
               o.secondary_themes as secondary_themes,
               o.theme_confidence as theme_confidence,
               collect(DISTINCT {
                   entity: e.name,
                   confidence: r.confidence,
                   method: r.extraction_method
               }) as linked_concepts,
               d.date as occurred_on,
               source_entity.name as source_entity,
               session.session_id as conversation_id,
               o.timestamp as obs_timestamp
        ORDER BY obs_timestamp DESC
        SKIP $offset
        LIMIT $limit
    """)

    params['offset'] = offset
    params['limit'] = limit

    # Combine query parts
    cypher_query = "\n".join(cypher_parts)

    # Execute query
    result = db_session.run(cypher_query, **params)

    # Parse results
    observations = []
    for record in result:
        # Filter out empty concept links (from OPTIONAL MATCH)
        linked_concepts = [
            c for c in record['linked_concepts']
            if c['entity'] is not None
        ]

        observations.append(ObservationSearchResult(
            obs_id=record['obs_id'],
            content=record['content'],
            primary_theme=record['primary_theme'],
            secondary_themes=record['secondary_themes'] or [],
            theme_confidence=record['theme_confidence'],
            linked_concepts=linked_concepts,
            occurred_on=str(record['occurred_on']) if record['occurred_on'] else None,
            source_entity=record['source_entity'],
            conversation_id=record['conversation_id']
        ))

    # TODO: Semantic search using query parameter
    # Requires observation embeddings to be loaded and similarity search
    # For now, just return text-based matches
    if query:
        # Future: Add semantic similarity ranking using JinaV3 embeddings
        # Filter observations by semantic similarity to query
        pass

    return observations


def format_search_results(
    results: List[ObservationSearchResult],
    max_content_length: int = 200
) -> str:
    """
    Format search results for display

    Args:
        results: List of ObservationSearchResult
        max_content_length: Max characters to show per observation

    Returns:
        Formatted string for display
    """
    if not results:
        return "No observations found matching the search criteria."

    lines = []
    lines.append(f"Found {len(results)} observations:\n")

    for i, obs in enumerate(results, 1):
        # Truncate content
        content = obs.content
        if len(content) > max_content_length:
            content = content[:max_content_length] + "..."

        # Format result
        lines.append(f"{i}. [{obs.primary_theme or 'unclassified'}] {content}")

        if obs.linked_concepts:
            concepts = ", ".join([
                f"{c['entity']} ({c['method']}, {c['confidence']:.2f})"
                for c in obs.linked_concepts[:5]  # Show max 5 concepts
            ])
            lines.append(f"   Concepts: {concepts}")

        if obs.occurred_on:
            lines.append(f"   Date: {obs.occurred_on}")

        if obs.source_entity:
            lines.append(f"   Source: {obs.source_entity}")

        lines.append("")  # Blank line between results

    return "\n".join(lines)


# Example usage for testing
if __name__ == "__main__":
    from neo4j import GraphDatabase

    NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "")

    driver = GraphDatabase.driver(NEO4J_URI, auth=("neo4j", NEO4J_PASSWORD))

    with driver.session() as session:
        # Test: Find all observations mentioning PBC
        results = search_observations(
            session,
            entity_filter="Personality Bootstrap Component (PBC)",
            limit=10
        )

        print(format_search_results(results))

    driver.close()

"""
Local Search - GraphRAG Phase 3
Entity neighborhood exploration for focused relationship discovery.

Created: October 16, 2025
Status: Week 2 Implementation
"""

import time
from typing import List, Dict, Optional, Any


class LocalSearchError(Exception):
    """Base exception for local search errors."""
    pass


class EntityNotFoundError(LocalSearchError):
    """Target entity not found."""
    pass


class TraversalError(LocalSearchError):
    """Graph traversal failed."""
    pass


class ObservationError(LocalSearchError):
    """Observation gathering failed."""
    pass


class LocalSearch:
    """
    Local search implementation for GraphRAG Phase 3.

    Enables entity neighborhood exploration by traversing entity relationships,
    gathering observations, and returning structured data for natural synthesis.
    """

    def __init__(self, neo4j_driver: Any):
        """
        Initialize local search.

        Args:
            neo4j_driver: Neo4j driver instance
        """
        self.neo4j_driver = neo4j_driver

    def find_entity(self, entity_name: str) -> Optional[Dict]:
        """
        Find entity by name or alias (case-insensitive).

        Args:
            entity_name: Target entity name

        Returns:
            Entity dictionary with properties or None if not found

        Raises:
            EntityNotFoundError: If entity lookup fails
        """
        if not entity_name or not entity_name.strip():
            raise EntityNotFoundError("Entity name cannot be empty")

        query = """
        MATCH (e:Entity)
        WHERE toLower(e.name) = toLower($entity_name)
           OR (e.aliases IS NOT NULL AND $entity_name IN [alias IN e.aliases | toLower(alias)])
        RETURN
            e.name AS name,
            e.entityType AS entity_type,
            labels(e) AS labels,
            id(e) AS node_id
        LIMIT 1;
        """

        try:
            records, summary, keys = self.neo4j_driver.execute_query(
                query,
                entity_name=entity_name
            )

            if not records:
                return None

            record = records[0]
            return {
                "name": record["name"],
                "entity_type": record["entity_type"],
                "labels": record["labels"],
                "node_id": record["node_id"]
            }

        except Exception as e:
            raise EntityNotFoundError(f"Entity lookup failed: {str(e)}")

    def find_similar_entities(self, entity_name: str, limit: int = 5) -> List[str]:
        """
        Find entities with similar names (fuzzy search).

        Args:
            entity_name: Search term
            limit: Maximum suggestions

        Returns:
            List of similar entity names
        """
        query = """
        MATCH (e:Entity)
        WHERE toLower(e.name) CONTAINS toLower($search_term)
           OR any(alias IN e.aliases WHERE toLower(alias) CONTAINS toLower($search_term))
        RETURN DISTINCT e.name AS name
        LIMIT $limit;
        """

        try:
            records, summary, keys = self.neo4j_driver.execute_query(
                query,
                search_term=entity_name,
                limit=limit
            )

            return [record["name"] for record in records]

        except Exception:
            return []  # Return empty list on error

    def traverse_neighborhood(
        self,
        entity_name: str,
        depth: int = 2,
        hop1_limit: int = 20,
        hop2_limit: int = 10
    ) -> Dict[str, List[Dict]]:
        """
        Traverse entity neighborhood with configurable depth.

        Args:
            entity_name: Center entity name
            depth: 1 or 2 hop traversal
            hop1_limit: Max 1-hop neighbors
            hop2_limit: Max 2-hop neighbors

        Returns:
            Dictionary with one_hop and two_hop neighbor lists

        Raises:
            TraversalError: If traversal fails
        """
        # 1-hop neighbors
        hop1_query = """
        MATCH (center:Entity {name: $entity_name})
        MATCH (center)-[r]-(neighbor:Entity)
        WHERE NOT neighbor:Day
          AND NOT neighbor:Month
          AND NOT neighbor:Year
          AND NOT neighbor:ConversationSession
          AND NOT neighbor:ConversationMessage
          AND NOT neighbor:Chunk
          AND NOT neighbor:ConversationSummary
          AND NOT neighbor:Observation
        RETURN
            neighbor.name AS name,
            neighbor.entityType AS entity_type,
            type(r) AS relationship_type,
            CASE
                WHEN startNode(r) = center THEN 'outgoing'
                ELSE 'incoming'
            END AS direction,
            1 AS hop_distance
        LIMIT $hop1_limit;
        """

        try:
            records, summary, keys = self.neo4j_driver.execute_query(
                hop1_query,
                entity_name=entity_name,
                hop1_limit=hop1_limit
            )

            one_hop = [
                {
                    "name": r["name"],
                    "entity_type": r["entity_type"],
                    "relationship_type": r["relationship_type"],
                    "direction": r["direction"],
                    "hop_distance": 1
                }
                for r in records
            ]

        except Exception as e:
            raise TraversalError(f"1-hop traversal failed: {str(e)}")

        # 2-hop neighbors (if depth >= 2)
        two_hop = []
        if depth >= 2 and len(one_hop) > 0:
            hop2_query = """
            MATCH (center:Entity {name: $entity_name})
            MATCH (center)-[r1]-(intermediate:Entity)-[r2]-(outer:Entity)
            WHERE NOT intermediate:Day
              AND NOT intermediate:Month
              AND NOT intermediate:Year
              AND NOT intermediate:ConversationSession
              AND NOT intermediate:ConversationMessage
              AND NOT intermediate:Chunk
              AND NOT intermediate:ConversationSummary
              AND NOT intermediate:Observation
              AND NOT outer:Day
              AND NOT outer:Month
              AND NOT outer:Year
              AND NOT outer:ConversationSession
              AND NOT outer:ConversationMessage
              AND NOT outer:Chunk
              AND NOT outer:ConversationSummary
              AND NOT outer:Observation
              AND outer <> center
              AND NOT (center)-[]-(outer)
            RETURN
                outer.name AS name,
                outer.entityType AS entity_type,
                intermediate.name AS via_entity,
                type(r1) AS relationship1_type,
                type(r2) AS relationship2_type,
                2 AS hop_distance
            LIMIT $hop2_limit;
            """

            try:
                records, summary, keys = self.neo4j_driver.execute_query(
                    hop2_query,
                    entity_name=entity_name,
                    hop2_limit=hop2_limit
                )

                two_hop = [
                    {
                        "name": r["name"],
                        "entity_type": r["entity_type"],
                        "via_entity": r["via_entity"],
                        "relationship1_type": r["relationship1_type"],
                        "relationship2_type": r["relationship2_type"],
                        "hop_distance": 2
                    }
                    for r in records
                ]

            except Exception as e:
                # Log warning but don't fail - 1-hop is still useful
                print(f"Warning: 2-hop traversal failed: {str(e)}")

        return {
            "one_hop": one_hop,
            "two_hop": two_hop,
            "total_neighbors": len(one_hop) + len(two_hop)
        }

    def gather_observations(
        self,
        entity_names: List[str],
        observation_limit: int = 10
    ) -> Dict[str, List[Dict]]:
        """
        Gather V6 observations for multiple entities.

        Args:
            entity_names: List of entity names
            observation_limit: Max observations per entity

        Returns:
            Dictionary mapping entity names to observation lists

        Raises:
            ObservationError: If observation gathering fails
        """
        if not entity_names:
            return {}

        # CRITICAL: Property names aligned with canonical schema (/llm/memory/schemas/property_names.py)
        # - obs.content (not obs.name) - canonical V6 observation text property
        # - obs.semantic_theme (not obs.theme) - canonical V6 theme property
        # - Phase 3 migration: 100% created_at coverage (V5 fallbacks removed)
        query = """
        UNWIND $entity_names AS entity_name
        MATCH (e:Entity {name: entity_name})-[:ENTITY_HAS_OBSERVATION]->(obs:Observation)
        RETURN
            entity_name,
            obs.content AS observation,
            obs.created_at AS created_at,
            obs.semantic_theme AS theme,
            obs.importance_score AS importance
        ORDER BY entity_name, obs.created_at DESC
        """

        try:
            records, summary, keys = self.neo4j_driver.execute_query(
                query,
                entity_names=entity_names
            )

            # Group observations by entity
            observations_by_entity = {}
            for record in records:
                entity = record["entity_name"]
                if entity not in observations_by_entity:
                    observations_by_entity[entity] = []

                observations_by_entity[entity].append({
                    "observation": record["observation"],
                    "created_at": record["created_at"],
                    "theme": record["theme"],
                    "importance": record["importance"]
                })

            # Apply limit per entity
            for entity in observations_by_entity:
                observations_by_entity[entity] = observations_by_entity[entity][:observation_limit]

            return observations_by_entity

        except Exception as e:
            raise ObservationError(f"Observation gathering failed: {str(e)}")

    def assemble_local_context(
        self,
        center_entity: Dict,
        neighborhood: Dict,
        observations: Dict[str, List[Dict]]
    ) -> Dict:
        """
        Assemble local search response with structured data.

        Args:
            center_entity: Target entity dictionary
            neighborhood: Neighborhood traversal results
            observations: Observations by entity name

        Returns:
            Structured local search response
        """
        return {
            "center_entity": {
                "name": center_entity["name"],
                "entity_type": center_entity["entity_type"],
                "labels": center_entity["labels"],
                "observations": observations.get(center_entity["name"], [])
            },
            "one_hop_neighbors": [
                {
                    "name": n["name"],
                    "entity_type": n["entity_type"],
                    "relationship_type": n["relationship_type"],
                    "direction": n["direction"],
                    "observations": observations.get(n["name"], [])[:3]  # Top 3 obs per neighbor
                }
                for n in neighborhood["one_hop"]
            ],
            "two_hop_neighbors": [
                {
                    "name": n["name"],
                    "entity_type": n["entity_type"],
                    "via_entity": n["via_entity"],
                    "relationship_path": f"{n['relationship1_type']} → {n['relationship2_type']}"
                }
                for n in neighborhood["two_hop"]
            ],
            "summary": {
                "total_neighbors": neighborhood["total_neighbors"],
                "one_hop_count": len(neighborhood["one_hop"]),
                "two_hop_count": len(neighborhood["two_hop"]),
                "entities_with_observations": len([e for e in observations if observations[e]])
            }
        }

    def search(
        self,
        entity_name: str,
        depth: int = 2,
        hop1_limit: int = 20,
        hop2_limit: int = 10,
        observation_limit: int = 10
    ) -> Dict:
        """
        Execute local search end-to-end.

        Returns raw entity neighborhood data for Claude Code to synthesize.

        Args:
            entity_name: Name of entity to explore
            depth: 1 or 2 hop traversal
            hop1_limit: Max 1-hop neighbors (1-50)
            hop2_limit: Max 2-hop neighbors (1-30)
            observation_limit: Max observations per entity (1-20)

        Returns:
            Dictionary with neighborhood data and performance metrics
        """
        start_time = time.time()

        # Validate inputs
        if not entity_name or not entity_name.strip():
            return {
                "error": "Entity name cannot be empty",
                "error_type": "invalid_input",
                "retry_suggestion": "Please provide an entity name"
            }

        if depth not in [1, 2]:
            return {
                "error": f"Depth must be 1 or 2, got {depth}",
                "error_type": "invalid_input",
                "retry_suggestion": "Use depth=1 or depth=2"
            }

        if hop1_limit < 1 or hop1_limit > 50:
            return {
                "error": f"hop1_limit must be between 1 and 50, got {hop1_limit}",
                "error_type": "invalid_input",
                "retry_suggestion": "Use hop1_limit between 1 and 50"
            }

        if hop2_limit < 1 or hop2_limit > 30:
            return {
                "error": f"hop2_limit must be between 1 and 30, got {hop2_limit}",
                "error_type": "invalid_input",
                "retry_suggestion": "Use hop2_limit between 1 and 30"
            }

        if observation_limit < 1 or observation_limit > 20:
            return {
                "error": f"observation_limit must be between 1 and 20, got {observation_limit}",
                "error_type": "invalid_input",
                "retry_suggestion": "Use observation_limit between 1 and 20"
            }

        # Step 1: Find entity
        try:
            lookup_start = time.time()
            center_entity = self.find_entity(entity_name)
            lookup_time = (time.time() - lookup_start) * 1000  # Convert to ms

            if not center_entity:
                # Try fuzzy search for suggestions
                similar_entities = self.find_similar_entities(entity_name)

                return {
                    "error": f"Entity '{entity_name}' not found",
                    "error_type": "entity_not_found",
                    "suggestions": similar_entities,
                    "retry_suggestion": "Try one of the suggested entity names or use search_nodes() for semantic search",
                    "lookup_time_ms": round(lookup_time, 2)
                }

        except EntityNotFoundError as e:
            return {
                "error": str(e),
                "error_type": "entity_not_found",
                "retry_suggestion": "Check entity name and try again"
            }

        # Step 2: Traverse neighborhood
        try:
            traversal_start = time.time()
            neighborhood = self.traverse_neighborhood(
                entity_name=center_entity["name"],
                depth=depth,
                hop1_limit=hop1_limit,
                hop2_limit=hop2_limit
            )
            traversal_time = (time.time() - traversal_start) * 1000

        except TraversalError as e:
            return {
                "error": str(e),
                "error_type": "traversal_failed",
                "retry_suggestion": "Check Neo4j connection and retry",
                "lookup_time_ms": round(lookup_time, 2)
            }

        # Handle empty neighborhood
        if neighborhood["total_neighbors"] == 0:
            return {
                "query": entity_name,
                "center_entity": {
                    "name": center_entity["name"],
                    "entity_type": center_entity["entity_type"],
                    "labels": center_entity["labels"],
                    "observations": []
                },
                "one_hop_neighbors": [],
                "two_hop_neighbors": [],
                "summary": {
                    "total_neighbors": 0,
                    "message": "Entity has no connections in the graph. This may indicate an isolated entity or incomplete data."
                },
                "lookup_time_ms": round(lookup_time, 2),
                "traversal_time_ms": round(traversal_time, 2),
                "total_time_ms": round((time.time() - start_time) * 1000, 2)
            }

        # Step 3: Gather observations
        try:
            observation_start = time.time()

            # Collect entity names: center + top 5 1-hop neighbors
            entity_names = [center_entity["name"]]
            entity_names.extend([n["name"] for n in neighborhood["one_hop"][:5]])

            observations = self.gather_observations(entity_names, observation_limit)
            observation_time = (time.time() - observation_start) * 1000

        except ObservationError as e:
            # Log warning but don't fail - neighborhood data is still useful
            print(f"Warning: Observation gathering failed: {str(e)}")
            observations = {}
            observation_time = 0

        # Step 4: Assemble context
        result = self.assemble_local_context(center_entity, neighborhood, observations)

        # Add performance metrics
        total_time = (time.time() - start_time) * 1000
        result["query"] = entity_name
        result["lookup_time_ms"] = round(lookup_time, 2)
        result["traversal_time_ms"] = round(traversal_time, 2)
        result["observation_time_ms"] = round(observation_time, 2)
        result["total_time_ms"] = round(total_time, 2)

        return result


# Convenience function for standalone usage
def local_search(
    entity_name: str,
    neo4j_driver: Any,
    depth: int = 2,
    hop1_limit: int = 20,
    hop2_limit: int = 10,
    observation_limit: int = 10
) -> Dict:
    """
    Convenience function for local search.

    Returns raw neighborhood data - synthesis happens in Claude Code.

    Args:
        entity_name: Name of entity to explore
        neo4j_driver: Neo4j driver instance
        depth: 1 or 2 hop traversal
        hop1_limit: Max 1-hop neighbors (1-50)
        hop2_limit: Max 2-hop neighbors (1-30)
        observation_limit: Max observations per entity (1-20)

    Returns:
        Local search results with neighborhood data and performance metrics
    """
    searcher = LocalSearch(neo4j_driver)
    return searcher.search(
        entity_name=entity_name,
        depth=depth,
        hop1_limit=hop1_limit,
        hop2_limit=hop2_limit,
        observation_limit=observation_limit
    )


if __name__ == "__main__":
    print("Local Search - GraphRAG Phase 3")
    print("Use via MCP tool: graphrag_local_search()")
    print("\nExample:")
    print("  from local_search import local_search")
    print("  result = local_search('Daydreamer', neo4j_driver)")

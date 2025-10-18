"""
MCP Integration - GraphRAG Phase 3
Wrappers for global_search and local_search MCP tools.

Created: October 16, 2025
Status: Global Search MVP
"""

import json
from typing import Dict, Any, Optional
from pathlib import Path

from global_search import GlobalSearch, GlobalSearchError
from local_search import LocalSearch, LocalSearchError


# Feature flags location
FEATURE_FLAGS_PATH = Path("/tmp/graphrag_phase3_flags.json")


def load_feature_flags() -> Dict[str, bool]:
    """
    Load GraphRAG Phase 3 feature flags.

    Returns:
        Dictionary of feature flags
    """
    if not FEATURE_FLAGS_PATH.exists():
        # Default flags (all disabled)
        return {
            "graphrag_enabled": False,
            "graphrag_global_search": False,
            "graphrag_local_search": False,
            "graphrag_community_summaries": True,  # Phase 2 complete
            "graphrag_community_embeddings": True,  # Phase 2 complete
            "graphrag_vector_index": True  # Phase 2 complete
        }

    try:
        with open(FEATURE_FLAGS_PATH, 'r') as f:
            return json.load(f)
    except Exception:
        return {}


def check_feature_flags_enabled() -> tuple[bool, Dict[str, bool]]:
    """
    Check if all required feature flags are enabled.

    Returns:
        Tuple of (all_enabled, flags_dict)
    """
    flags = load_feature_flags()

    required = [
        "graphrag_enabled",
        "graphrag_global_search",
        "graphrag_community_summaries",
        "graphrag_community_embeddings",
        "graphrag_vector_index"
    ]

    all_enabled = all(flags.get(flag, False) for flag in required)

    return all_enabled, flags


async def graphrag_global_search_handler(
    query: str,
    neo4j_driver: Any,
    limit: int = 5,
    min_similarity: float = 0.6,
    embedder: Optional[Any] = None
) -> Dict:
    """
    MCP tool handler for graphrag_global_search.

    Returns raw community data for Claude Code to synthesize naturally.

    Args:
        query: Natural language question
        neo4j_driver: Neo4j driver instance
        limit: Maximum communities to retrieve (default: 5, max: 20)
        min_similarity: Minimum cosine similarity (default: 0.6, range: 0.0-1.0)

    Returns:
        Dictionary with communities and performance metrics
    """
    # Check feature flags
    flags_enabled, flags = check_feature_flags_enabled()

    if not flags_enabled:
        return {
            "error": "Global search is not enabled",
            "error_type": "feature_disabled",
            "retry_suggestion": "Enable graphrag feature flags in config",
            "required_flags": {
                flag: flags.get(flag, False)
                for flag in [
                    "graphrag_enabled",
                    "graphrag_global_search",
                    "graphrag_community_summaries",
                    "graphrag_community_embeddings",
                    "graphrag_vector_index"
                ]
            }
        }

    # Validate inputs
    if not query or not query.strip():
        return {
            "error": "Query parameter is required",
            "error_type": "invalid_input",
            "retry_suggestion": "Provide a query string"
        }

    # Execute global search - returns raw communities for Claude Code synthesis
    try:
        searcher = GlobalSearch(neo4j_driver, embedder=embedder)

        result = await searcher.search(
            query=query,
            limit=limit,
            min_similarity=min_similarity
        )

        return result

    except GlobalSearchError as e:
        return {
            "error": str(e),
            "error_type": "search_failed",
            "retry_suggestion": "Check logs for details"
        }
    except Exception as e:
        return {
            "error": f"Unexpected error: {str(e)}",
            "error_type": "internal_error",
            "retry_suggestion": "Check MCP server logs"
        }


async def graphrag_local_search_handler(
    entity_name: str,
    neo4j_driver: Any,
    depth: int = 2,
    hop1_limit: int = 20,
    hop2_limit: int = 10,
    observation_limit: int = 10
) -> Dict:
    """
    MCP tool handler for graphrag_local_search.

    Returns raw entity neighborhood data for Claude Code to synthesize naturally.

    Args:
        entity_name: Name of entity to explore (supports aliases)
        neo4j_driver: Neo4j driver instance
        depth: 1 or 2 hop traversal (default: 2)
        hop1_limit: Max 1-hop neighbors (default: 20, max: 50)
        hop2_limit: Max 2-hop neighbors (default: 10, max: 30)
        observation_limit: Max observations per entity (default: 10, max: 20)

    Returns:
        Dictionary with entity neighborhood, relationships, observations, and performance metrics
    """
    # Check feature flags
    flags = load_feature_flags()

    if not flags.get("graphrag_enabled") or not flags.get("graphrag_local_search"):
        return {
            "error": "Local search is not enabled",
            "error_type": "feature_disabled",
            "retry_suggestion": "Enable graphrag_local_search feature flag",
            "required_flags": {
                "graphrag_enabled": flags.get("graphrag_enabled", False),
                "graphrag_local_search": flags.get("graphrag_local_search", False)
            }
        }

    # Validate inputs
    if not entity_name or not entity_name.strip():
        return {
            "error": "entity_name parameter is required",
            "error_type": "invalid_input",
            "retry_suggestion": "Provide an entity name"
        }

    # Execute local search - returns raw neighborhood data for Claude Code synthesis
    try:
        searcher = LocalSearch(neo4j_driver)

        result = searcher.search(
            entity_name=entity_name,
            depth=depth,
            hop1_limit=hop1_limit,
            hop2_limit=hop2_limit,
            observation_limit=observation_limit
        )

        return result

    except LocalSearchError as e:
        return {
            "error": str(e),
            "error_type": "search_failed",
            "retry_suggestion": "Check logs for details"
        }
    except Exception as e:
        return {
            "error": f"Unexpected error: {str(e)}",
            "error_type": "internal_error",
            "retry_suggestion": "Check MCP server logs"
        }


def create_feature_flags_file(enable_global: bool = False, enable_local: bool = False) -> None:
    """
    Create feature flags file with specified settings.

    Args:
        enable_global: Enable global search
        enable_local: Enable local search
    """
    flags = {
        "graphrag_enabled": enable_global or enable_local,
        "graphrag_global_search": enable_global,
        "graphrag_local_search": enable_local,
        "graphrag_community_summaries": True,
        "graphrag_community_embeddings": True,
        "graphrag_vector_index": True
    }

    FEATURE_FLAGS_PATH.parent.mkdir(parents=True, exist_ok=True)

    with open(FEATURE_FLAGS_PATH, 'w') as f:
        json.dump(flags, f, indent=2)

    print(f"Feature flags created at {FEATURE_FLAGS_PATH}")
    print(json.dumps(flags, indent=2))


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "enable-global":
        create_feature_flags_file(enable_global=True)
        print("\n✅ Global search enabled!")
    elif len(sys.argv) > 1 and sys.argv[1] == "enable-all":
        create_feature_flags_file(enable_global=True, enable_local=True)
        print("\n✅ Global and local search enabled!")
    else:
        print("MCP Integration - GraphRAG Phase 3")
        print("\nUsage:")
        print("  python mcp_integration.py enable-global   # Enable global search only")
        print("  python mcp_integration.py enable-all      # Enable both global and local")
        print("\nCurrent flags:")
        flags = load_feature_flags()
        print(json.dumps(flags, indent=2))

"""
Global Search - GraphRAG Phase 3
Community-level synthesis search for high-level questions.

Created: October 16, 2025
Status: MVP Implementation
"""

import time
from typing import List, Dict, Optional, Any
from pathlib import Path
import sys

# Add parent directories to path for imports
current_dir = Path(__file__).parent
phase3_dir = current_dir.parent
memory_dir = phase3_dir.parent
project_root = memory_dir.parent.parent

sys.path.insert(0, str(project_root / "llm" / "mcp" / "servers" / "daydreamer-memory-mcp" / "src"))

from jina_v3_optimized_embedder import JinaV3OptimizedEmbedder


class GlobalSearchError(Exception):
    """Base exception for global search errors."""
    pass


class EmbeddingError(GlobalSearchError):
    """Query embedding failed."""
    pass


class SearchError(GlobalSearchError):
    """Vector search failed."""
    pass


class SynthesisError(GlobalSearchError):
    """Answer synthesis failed."""
    pass


class GlobalSearch:
    """
    Global search implementation for GraphRAG Phase 3.

    Enables synthesis questions by querying community-level knowledge
    using vector similarity and LLM-based answer synthesis.
    """

    def __init__(
        self,
        neo4j_driver: Any,
        embedder: Optional[JinaV3OptimizedEmbedder] = None
    ):
        """
        Initialize global search.

        Args:
            neo4j_driver: Neo4j driver instance
            embedder: JinaV3 embedder instance (optional, will create if None)
        """
        self.neo4j_driver = neo4j_driver
        self.embedder = embedder or JinaV3OptimizedEmbedder()

    async def embed_query(self, query: str) -> List[float]:
        """
        Embed user query using JinaV3.

        Args:
            query: Natural language query

        Returns:
            256D embedding vector

        Raises:
            EmbeddingError: If embedding fails
        """
        if not query or not query.strip():
            raise EmbeddingError("Query cannot be empty")

        try:
            # Use async encode_single_async() for async context
            vector = await self.embedder.encode_single_async(query)

            if not vector or len(vector) != 256:
                raise EmbeddingError(f"Invalid embedding dimension: {len(vector)}")

            return vector

        except Exception as e:
            raise EmbeddingError(f"Failed to embed query: {str(e)}")

    async def vector_search_communities(
        self,
        query_vector: List[float],
        limit: int = 5
    ) -> List[Dict]:
        """
        Search communities using vector similarity.

        Args:
            query_vector: 256D embedding vector
            limit: Maximum communities to return

        Returns:
            List of community dictionaries with metadata and scores

        Raises:
            SearchError: If vector search fails
        """
        if not query_vector or len(query_vector) != 256:
            raise SearchError(f"Invalid query vector dimension: {len(query_vector)}")

        if limit < 1 or limit > 20:
            raise SearchError(f"Limit must be between 1 and 20, got {limit}")

        # Calculate scan limit: need 10x overscan since 89% communities are single-entity
        # This overcomes the post-filter trap where vector search returns top-K BEFORE WHERE filtering
        scan_limit = limit * 10

        query = """
        CALL db.index.vector.queryNodes(
            'community_summary_vector_idx',
            $scan_limit,
            $query_vector
        )
        YIELD node, score
        WHERE node:CommunitySummary AND node.member_count >= 3
        RETURN
            node.community_id AS community_id,
            node.name AS name,
            node.summary AS summary,
            node.member_count AS member_count,
            score
        ORDER BY score DESC
        LIMIT $limit;
        """

        try:
            records, summary, keys = self.neo4j_driver.execute_query(
                query,
                query_vector=query_vector,
                scan_limit=scan_limit,
                limit=limit
            )

            results = []
            for record in records:
                results.append({
                    "community_id": record["community_id"],
                    "name": record["name"],
                    "summary": record["summary"],
                    "member_count": record["member_count"],
                    "similarity_score": record["score"]
                })

            return results

        except Exception as e:
            # Check for specific Neo4j errors
            error_msg = str(e).lower()

            if "index" in error_msg and "not found" in error_msg:
                raise SearchError(
                    "Vector index 'community_summary_vector_idx' not found. "
                    "Run Phase 2 index creation script."
                )
            elif "connection" in error_msg:
                raise SearchError(f"Neo4j connection failed: {str(e)}")
            else:
                raise SearchError(f"Vector search failed: {str(e)}")

    def rank_and_filter_communities(
        self,
        communities: List[Dict],
        min_similarity: float = 0.6
    ) -> List[Dict]:
        """
        Filter and rank communities by relevance.

        Args:
            communities: List of community dictionaries
            min_similarity: Minimum cosine similarity threshold

        Returns:
            Filtered and ranked communities
        """
        # Filter by minimum similarity
        filtered = [
            c for c in communities
            if c["similarity_score"] >= min_similarity
        ]

        # Add rank position (already sorted by Neo4j)
        for idx, community in enumerate(filtered):
            community["rank"] = idx + 1

        return filtered


    async def search(
        self,
        query: str,
        limit: int = 5,
        min_similarity: float = 0.6
    ) -> Dict:
        """
        Execute global search end-to-end.

        Returns raw community data for Claude Code to synthesize.

        Args:
            query: Natural language question
            limit: Maximum communities to retrieve (1-20)
            min_similarity: Minimum cosine similarity (0.0-1.0)

        Returns:
            Dictionary with communities and performance metrics
        """
        start_time = time.time()

        # Validate inputs
        if not query or not query.strip():
            return {
                "error": "Query cannot be empty",
                "error_type": "invalid_input",
                "retry_suggestion": "Please provide a meaningful query"
            }

        if limit < 1 or limit > 20:
            return {
                "error": f"Limit must be between 1 and 20, got {limit}",
                "error_type": "invalid_input",
                "retry_suggestion": "Use limit between 1 and 20"
            }

        if min_similarity < 0.0 or min_similarity > 1.0:
            return {
                "error": f"Minimum similarity must be between 0.0 and 1.0, got {min_similarity}",
                "error_type": "invalid_input",
                "retry_suggestion": "Use min_similarity between 0.0 and 1.0"
            }

        # Step 1: Embed query
        try:
            embed_start = time.time()
            query_vector = await self.embed_query(query)
            embed_time = (time.time() - embed_start) * 1000  # Convert to ms
        except EmbeddingError as e:
            return {
                "error": str(e),
                "error_type": "embedding_failed",
                "retry_suggestion": "Check JinaV3 embedder availability",
                "fallback_available": False
            }

        # Step 2: Vector search
        try:
            search_start = time.time()
            communities = await self.vector_search_communities(query_vector, limit)
            search_time = (time.time() - search_start) * 1000
        except SearchError as e:
            return {
                "error": str(e),
                "error_type": "search_failed",
                "retry_suggestion": "Check Neo4j connection and vector index",
                "fallback_available": False,
                "query_embedding_time_ms": embed_time
            }

        # Step 3: Rank and filter
        filtered_communities = self.rank_and_filter_communities(communities, min_similarity)

        # Handle no results
        if not filtered_communities:
            # Try with lower threshold
            filtered_communities = self.rank_and_filter_communities(communities, min_similarity * 0.8)

            if not filtered_communities:
                # Return top 3 regardless
                filtered_communities = communities[:3] if communities else []

                if not filtered_communities:
                    return {
                        "communities": [],
                        "query": query,
                        "message": "No relevant communities found. Try broader search terms or local search.",
                        "query_embedding_time_ms": round(embed_time, 2),
                        "search_time_ms": round(search_time, 2),
                        "total_time_ms": round((time.time() - start_time) * 1000, 2)
                    }

        # Return raw community data for Claude Code to synthesize
        total_time = (time.time() - start_time) * 1000

        return {
            "query": query,
            "communities": filtered_communities,
            "query_embedding_time_ms": round(embed_time, 2),
            "search_time_ms": round(search_time, 2),
            "total_time_ms": round(total_time, 2)
        }


# Convenience function for standalone usage
async def global_search(
    query: str,
    neo4j_driver: Any,
    limit: int = 5,
    min_similarity: float = 0.6
) -> Dict:
    """
    Convenience function for global search.

    Returns raw community data - synthesis happens in Claude Code.

    Args:
        query: Natural language question
        neo4j_driver: Neo4j driver instance
        limit: Maximum communities to retrieve (1-20)
        min_similarity: Minimum cosine similarity (0.0-1.0)

    Returns:
        Search results with communities and performance metrics
    """
    searcher = GlobalSearch(neo4j_driver)
    return await searcher.search(
        query=query,
        limit=limit,
        min_similarity=min_similarity
    )


if __name__ == "__main__":
    print("Global Search MVP - GraphRAG Phase 3")
    print("Use via MCP tool: graphrag_global_search()")
    print("\nExample:")
    print("  from global_search import global_search")
    print("  result = await global_search('What are the major technical themes?', neo4j_driver)")

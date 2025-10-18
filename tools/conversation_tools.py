"""
Conversation-aware memory tools for Perennial V6
Enables queries across preserved conversation sessions
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from neo4j import Driver


class ConversationTools:
    """Tools for querying conversation sessions and their context"""

    def __init__(self, driver: Driver):
        self.driver = driver

    def search_conversations(
        self,
        topic: Optional[str] = None,
        date_range: Optional[Tuple[str, str]] = None,
        min_messages: Optional[int] = None,
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search preserved conversation sessions

        Args:
            topic: Keyword to search in chunks/messages
            date_range: Tuple of (start_date, end_date) in ISO format
            min_messages: Minimum message count filter
            max_results: Maximum results to return

        Returns:
            List of conversation summaries with metadata
        """
        with self.driver.session() as session:
            query = """
            MATCH (s:ConversationSession)
            WHERE 1=1
            """

            params = {"max_results": max_results}

            # Add topic filter if provided
            if topic:
                query += """
                AND exists {
                    MATCH (s)-[:HAS_CHUNK]->(chunk:Chunk)
                    WHERE chunk.content CONTAINS $topic
                }
                """
                params["topic"] = topic

            # Add date range filter if provided
            if date_range:
                start_date, end_date = date_range
                query += """
                AND s.first_message_at >= datetime($start_date)
                AND s.first_message_at <= datetime($end_date)
                """
                params["start_date"] = start_date
                params["end_date"] = end_date

            # Add message count filter if provided
            if min_messages:
                query += """
                AND s.message_count >= $min_messages
                """
                params["min_messages"] = min_messages

            # Return results ordered by importance
            query += """
            RETURN
                s.conversation_id as conversation_id,
                s.first_message_at as first_message_at,
                s.last_message_at as last_message_at,
                s.message_count as message_count,
                s.entity_count as entity_count,
                s.chunk_count as chunk_count,
                s.importance_score as importance_score
            ORDER BY s.importance_score DESC
            LIMIT $max_results
            """

            result = session.run(query, params)

            conversations = []
            for record in result:
                # Handle datetime conversion safely
                first_msg = record["first_message_at"]
                if first_msg:
                    first_msg = first_msg.isoformat() if hasattr(first_msg, 'isoformat') else str(first_msg)

                last_msg = record["last_message_at"]
                if last_msg:
                    last_msg = last_msg.isoformat() if hasattr(last_msg, 'isoformat') else str(last_msg)

                conversations.append({
                    "conversation_id": record["conversation_id"],
                    "first_message_at": first_msg,
                    "last_message_at": last_msg,
                    "message_count": record["message_count"],
                    "entity_count": record["entity_count"],
                    "chunk_count": record["chunk_count"],
                    "importance_score": record["importance_score"]
                })

            return conversations

    def trace_entity_origin(
        self,
        entity_name: str
    ) -> List[Dict[str, Any]]:
        """
        Find which conversations created or discussed an entity

        Args:
            entity_name: Name of the entity to trace

        Returns:
            List of conversations that created/mentioned the entity
        """
        with self.driver.session() as session:
            query = """
            MATCH (entity:Entity {name: $entity_name})
            OPTIONAL MATCH (session:ConversationSession)-[r:CONVERSATION_CREATED_ENTITY]->(entity)
            WITH entity, session, r
            ORDER BY r.created_at DESC
            RETURN
                session.conversation_id as conversation_id,
                session.first_message_at as first_message_at,
                session.message_count as message_count,
                session.importance_score as importance_score,
                r.created_at as creation_timestamp,
                r.confidence as confidence,
                r.creation_method as creation_method
            """

            result = session.run(query, {"entity_name": entity_name})

            origins = []
            for record in result:
                if record["conversation_id"]:  # Only include if conversation found
                    # Handle datetime conversion (Neo4j returns datetime objects or strings)
                    first_msg = record["first_message_at"]
                    if first_msg:
                        first_msg = first_msg.isoformat() if hasattr(first_msg, 'isoformat') else str(first_msg)

                    creation_ts = record["creation_timestamp"]
                    if creation_ts:
                        creation_ts = creation_ts.isoformat() if hasattr(creation_ts, 'isoformat') else str(creation_ts)

                    origins.append({
                        "conversation_id": record["conversation_id"],
                        "first_message_at": first_msg,
                        "message_count": record["message_count"],
                        "importance_score": record["importance_score"],
                        "creation_timestamp": creation_ts,
                        "confidence": record["confidence"],
                        "creation_method": record["creation_method"]
                    })

            return origins

    def get_temporal_context(
        self,
        date: str,
        window_days: int = 7
    ) -> List[Dict[str, Any]]:
        """
        Get conversations around a specific date

        Args:
            date: Center date in ISO format (YYYY-MM-DD)
            window_days: Days before/after to include

        Returns:
            List of conversations within the time window
        """
        with self.driver.session() as session:
            query = """
            WITH datetime($date) as center_date,
                 duration({days: $window_days}) as window
            MATCH (s:ConversationSession)
            WHERE s.first_message_at >= center_date - window
              AND s.first_message_at <= center_date + window
            RETURN
                s.conversation_id as conversation_id,
                s.first_message_at as first_message_at,
                s.message_count as message_count,
                s.entity_count as entity_count,
                s.importance_score as importance_score
            ORDER BY s.first_message_at ASC
            """

            result = session.run(query, {
                "date": date,
                "window_days": window_days
            })

            conversations = []
            for record in result:
                # Handle datetime conversion safely
                first_msg = record["first_message_at"]
                if first_msg:
                    first_msg = first_msg.isoformat() if hasattr(first_msg, 'isoformat') else str(first_msg)

                conversations.append({
                    "conversation_id": record["conversation_id"],
                    "first_message_at": first_msg,
                    "message_count": record["message_count"],
                    "entity_count": record["entity_count"],
                    "importance_score": record["importance_score"]
                })

            return conversations

    def get_breakthrough_sessions(
        self,
        min_importance: float = 0.5,
        max_results: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get high-importance conversations (breakthrough sessions)

        Args:
            min_importance: Minimum importance score threshold
            max_results: Maximum results to return

        Returns:
            List of breakthrough conversations
        """
        with self.driver.session() as session:
            query = """
            MATCH (s:ConversationSession)
            WHERE s.importance_score >= $min_importance
            RETURN
                s.conversation_id as conversation_id,
                s.first_message_at as first_message_at,
                s.message_count as message_count,
                s.entity_count as entity_count,
                s.chunk_count as chunk_count,
                s.importance_score as importance_score
            ORDER BY s.importance_score DESC
            LIMIT $max_results
            """

            result = session.run(query, {
                "min_importance": min_importance,
                "max_results": max_results
            })

            sessions = []
            for record in result:
                # Handle datetime conversion safely
                first_msg = record["first_message_at"]
                if first_msg:
                    first_msg = first_msg.isoformat() if hasattr(first_msg, 'isoformat') else str(first_msg)

                sessions.append({
                    "conversation_id": record["conversation_id"],
                    "first_message_at": first_msg,
                    "message_count": record["message_count"],
                    "entity_count": record["entity_count"],
                    "chunk_count": record["chunk_count"],
                    "importance_score": record["importance_score"]
                })

            return sessions
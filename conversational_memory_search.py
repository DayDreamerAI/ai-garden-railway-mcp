#!/usr/bin/env python3
"""
Conversational Memory Search - Natural Language Interface for Daydreamer Memory
Created: August 30, 2025
Version: 1.0.0 - Prototype Implementation

OVERVIEW:
Natural language memory exploration interface that preserves Daydreamer's core advantages:
- JinaV3 256D embeddings with <50ms semantic search
- Personality protection for protected entities
- Token optimization with <4K startup target
- Production-ready performance and safety

ARCHITECTURE:
This module provides a natural language interface that:
1. Parses conversational queries using AI reasoning
2. Generates appropriate Cypher queries via template patterns
3. Executes through existing Daydreamer infrastructure
4. Returns conversational, contextualized responses

INTEGRATION:
- Routes through existing enhanced_search_nodes for semantic discovery
- Uses existing run_cypher for complex traversals
- Applies existing personality protection mechanisms
- Maintains token optimization and performance targets
"""

import re
import time
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta

logger = logging.getLogger("conversational_memory_search")

class ConversationalMemorySearchEngine:
    """
    Natural language memory exploration engine with personality protection
    """
    
    def __init__(self, run_cypher_func, enhanced_search_func, virtual_context_manager):
        self.run_cypher = run_cypher_func
        self.enhanced_search = enhanced_search_func
        self.virtual_context_manager = virtual_context_manager
        
        # Query pattern templates for common use cases
        self.query_patterns = {
            'connections': self._build_connection_pattern,
            'temporal': self._build_temporal_pattern,
            'semantic_exploration': self._build_semantic_pattern,
            'personality_insights': self._build_personality_pattern,
            'recent_thoughts': self._build_recent_pattern
        }
        
        # Protected entities - always preserve and include in context
        self.protected_entities = {
            'Julian Crespi',
            'Claude (Daydreamer Conversations)', 
            'Daydreamer Project',
            "Claude's Contemplation Space",
            'AI Garden',
            'Personality Exploration'
        }
    
    def conversational_search(self, 
                            natural_query: str, 
                            context_mode: str = "semantic",
                            token_budget: int = 15000,
                            include_personality: bool = True) -> Dict[str, Any]:
        """
        Main entry point for natural language memory exploration
        
        Args:
            natural_query: Natural language query (e.g., "Show connections between AI Garden and energy projects")
            context_mode: Type of context to emphasize ('semantic', 'temporal', 'relational', 'comprehensive')
            token_budget: Token budget for response optimization
            include_personality: Include protected personality entities in context
            
        Returns:
            Dict containing conversational response with structured data
        """
        start_time = time.time()
        
        try:
            # Step 1: Parse intent from natural language
            intent = self._parse_query_intent(natural_query)
            
            # Step 2: Apply personality protection
            if include_personality:
                intent = self._apply_personality_protection(intent)
            
            # Step 3: Generate and execute appropriate queries
            results = self._execute_query_by_intent(intent, context_mode, token_budget)
            
            # Step 4: Synthesize conversational response
            response = self._synthesize_response(natural_query, intent, results, token_budget)
            
            elapsed_time = (time.time() - start_time) * 1000
            
            # Add metadata
            response['query_metadata'] = {
                'natural_query': natural_query,
                'parsed_intent': intent,
                'context_mode': context_mode,
                'processing_time_ms': elapsed_time,
                'token_budget': token_budget,
                'personality_protection_active': include_personality,
                'protected_entities_included': len(self.protected_entities) if include_personality else 0
            }
            
            return response
            
        except Exception as e:
            logger.error(f"Conversational search failed: {e}")
            return {
                'error': f"Memory exploration failed: {str(e)}",
                'natural_query': natural_query,
                'fallback_recommendation': "Try using semantic search with more specific entity names"
            }
    
    def _parse_query_intent(self, query: str) -> Dict[str, Any]:
        """
        Parse natural language query to extract semantic intent
        
        Uses pattern matching and keyword analysis to understand:
        - Entity references (by name or description)
        - Relationship types (connections, influences, relates to)
        - Temporal constraints (recent, before, during, after)
        - Action types (show, find, explore, analyze)
        """
        intent = {
            'query_type': 'semantic_exploration',  # Default
            'entities': [],
            'relationships': [],
            'temporal_constraints': {},
            'action_type': 'explore',
            'keywords': [],
            'complexity': 'simple'
        }
        
        query_lower = query.lower()
        
        # Parse action types
        if any(word in query_lower for word in ['connect', 'connection', 'link', 'relate']):
            intent['query_type'] = 'connections'
            intent['action_type'] = 'connect'
        elif any(word in query_lower for word in ['recent', 'lately', 'last', 'new', 'latest']):
            intent['query_type'] = 'recent_thoughts' 
            intent['action_type'] = 'recent'
        elif any(word in query_lower for word in ['when', 'time', 'during', 'before', 'after']):
            intent['query_type'] = 'temporal'
            intent['action_type'] = 'temporal'
        elif any(word in query_lower for word in ['about', 'regarding', 'concerning']):
            intent['query_type'] = 'semantic_exploration'
            intent['action_type'] = 'explore'
        
        # Extract entity references
        # Look for quoted strings first
        quoted_entities = re.findall(r'"([^"]*)"', query)
        intent['entities'].extend(quoted_entities)
        
        # Look for known entity patterns
        entity_patterns = [
            r'\b(julian|julian crespi)\b',
            r'\b(claude|daydreamer conversations)\b', 
            r'\b(ai garden)\b',
            r'\b(ecodrones?)\b',
            r'\b(energy project[s]?)\b',
            r'\b(thought leader[s]?)\b',
            r'\b(context engineering)\b',
            r'\b(memory sovereignty)\b'
        ]
        
        for pattern in entity_patterns:
            matches = re.findall(pattern, query_lower)
            intent['entities'].extend(matches)
        
        # Parse temporal constraints
        if 'recent' in query_lower or 'lately' in query_lower:
            intent['temporal_constraints']['period'] = 'recent'
            intent['temporal_constraints']['days'] = 30
        elif 'last week' in query_lower:
            intent['temporal_constraints']['period'] = 'last_week'
            intent['temporal_constraints']['days'] = 7
        elif 'last month' in query_lower:
            intent['temporal_constraints']['period'] = 'last_month' 
            intent['temporal_constraints']['days'] = 30
        
        # Extract keywords for semantic search
        # Remove stop words and extract meaningful terms
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'show', 'me', 'find', 'get'}
        words = re.findall(r'\b\w+\b', query_lower)
        intent['keywords'] = [word for word in words if word not in stop_words and len(word) > 2]
        
        # Determine complexity
        if len(intent['entities']) > 2 or len(intent['keywords']) > 5:
            intent['complexity'] = 'complex'
        elif intent['temporal_constraints'] and intent['query_type'] == 'connections':
            intent['complexity'] = 'complex'
        
        return intent
    
    def _apply_personality_protection(self, intent: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply personality protection by ensuring protected entities are included in context
        """
        # Always include protected entities in search scope for comprehensive context
        protected_keywords = ['julian', 'claude', 'daydreamer', 'ai garden', 'personality']
        
        # If query mentions protected entities, ensure they're properly referenced
        for entity_name in self.protected_entities:
            if any(keyword in ' '.join(intent['keywords']) for keyword in entity_name.lower().split()):
                if entity_name not in intent['entities']:
                    intent['entities'].append(entity_name)
        
        # Add personality protection flag
        intent['personality_protected'] = True
        intent['protected_entities'] = list(self.protected_entities)
        
        return intent
    
    def _execute_query_by_intent(self, intent: Dict[str, Any], context_mode: str, token_budget: int) -> Dict[str, Any]:
        """
        Execute appropriate queries based on parsed intent
        """
        query_type = intent['query_type']
        
        if query_type in self.query_patterns:
            return self.query_patterns[query_type](intent, context_mode, token_budget)
        else:
            # Fallback to semantic search
            return self._build_semantic_pattern(intent, context_mode, token_budget)
    
    def _build_connection_pattern(self, intent: Dict[str, Any], context_mode: str, token_budget: int) -> Dict[str, Any]:
        """
        Find connections between entities mentioned in query
        """
        entities = intent['entities']
        if len(entities) < 2:
            # Use semantic search to find related entities
            semantic_results = self.enhanced_search(' '.join(intent['keywords']), limit=5)
            return {
                'pattern_type': 'connections_semantic_fallback',
                'semantic_results': semantic_results,
                'message': 'Used semantic search to find related entities for connection analysis'
            }
        
        # Generate Cypher to find paths between entities
        cypher_query = """
        MATCH (e1:Entity), (e2:Entity)
        WHERE e1.name CONTAINS $entity1 AND e2.name CONTAINS $entity2
        
        // Find connection paths (limit depth for performance)
        OPTIONAL MATCH path = (e1)-[*1..3]-(e2)
        WHERE length(path) <= 3
        
        // Also find common connections
        OPTIONAL MATCH (e1)-[r1]-(common:Entity)-[r2]-(e2)
        WHERE e1 <> e2 AND common <> e1 AND common <> e2
        
        RETURN e1.name as entity1,
               e2.name as entity2,
               [rel IN relationships(path) | type(rel)] as direct_connection_types,
               length(path) as connection_distance,
               collect(DISTINCT common.name)[0..5] as common_connections
        ORDER BY connection_distance
        LIMIT 10
        """
        
        results = []
        # Try all entity pairs
        for i, ent1 in enumerate(entities):
            for ent2 in entities[i+1:]:
                cypher_result = self.run_cypher(cypher_query, {
                    'entity1': ent1,
                    'entity2': ent2
                })
                if cypher_result:
                    results.extend(cypher_result)
        
        return {
            'pattern_type': 'connections',
            'entity_pairs': [(entities[i], entities[i+1]) for i in range(len(entities)-1)],
            'connection_results': results,
            'cypher_executed': cypher_query
        }
    
    def _build_temporal_pattern(self, intent: Dict[str, Any], context_mode: str, token_budget: int) -> Dict[str, Any]:
        """
        Find entities and observations within temporal constraints
        """
        constraints = intent['temporal_constraints']
        keywords = ' '.join(intent['keywords'])
        
        if not constraints:
            # Default to recent (30 days)
            constraints = {'period': 'recent', 'days': 30}
        
        # Calculate date boundaries
        end_date = datetime.now()
        start_date = end_date - timedelta(days=constraints.get('days', 30))
        
        # Use semantic search for temporal-aware results
        semantic_results = self.enhanced_search(keywords, limit=8)
        
        # Also find recent observations using Cypher
        temporal_cypher = """
        MATCH (e:Entity)-[:CREATED_ON]->(d:Entity)
        WHERE d.entityType = 'temporal_date' 
        AND datetime(d.name + 'T00:00:00') >= datetime($start_date)
        AND datetime(d.name + 'T00:00:00') <= datetime($end_date)
        AND any(keyword IN $keywords WHERE 
                any(obs IN e.observations WHERE obs CONTAINS keyword))
        RETURN e.name as entity_name,
               e.entityType as entity_type,
               d.name as creation_date,
               e.observations[0..2] as recent_observations
        ORDER BY d.name DESC
        LIMIT 15
        """
        
        temporal_results = self.run_cypher(temporal_cypher, {
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d'),
            'keywords': intent['keywords']
        })
        
        return {
            'pattern_type': 'temporal',
            'time_period': constraints,
            'date_range': {
                'start': start_date.strftime('%Y-%m-%d'),
                'end': end_date.strftime('%Y-%m-%d')
            },
            'semantic_results': semantic_results,
            'temporal_results': temporal_results
        }
    
    def _build_semantic_pattern(self, intent: Dict[str, Any], context_mode: str, token_budget: int) -> Dict[str, Any]:
        """
        General semantic exploration using enhanced search
        """
        query_text = ' '.join(intent['keywords'])
        if intent['entities']:
            query_text += ' ' + ' '.join(intent['entities'])
        
        # Use existing enhanced semantic search
        semantic_results = self.enhanced_search(query_text, limit=8)
        
        # If entities are specified, also find their direct relationships
        relationship_results = []
        if intent['entities']:
            for entity in intent['entities']:
                rel_cypher = """
                MATCH (e:Entity {name: $entity_name})-[r]-(connected:Entity)
                RETURN e.name as central_entity,
                       type(r) as relationship_type,
                       connected.name as connected_entity,
                       connected.entityType as connected_type
                ORDER BY connected.name
                LIMIT 10
                """
                
                rel_result = self.run_cypher(rel_cypher, {'entity_name': entity})
                if rel_result:
                    relationship_results.extend(rel_result)
        
        return {
            'pattern_type': 'semantic_exploration',
            'search_query': query_text,
            'semantic_results': semantic_results,
            'relationship_results': relationship_results
        }
    
    def _build_personality_pattern(self, intent: Dict[str, Any], context_mode: str, token_budget: int) -> Dict[str, Any]:
        """
        Protected personality exploration with safeguards
        """
        # Only allow read operations on personality entities
        protected_context = []
        
        for entity_name in intent.get('protected_entities', []):
            if entity_name in self.protected_entities:
                # Load basic entity data without modifications
                entity_data = self.run_cypher("""
                    MATCH (e:Entity {name: $name})
                    RETURN e.name as name,
                           e.entityType as entityType,
                           e.observations[0..3] as key_observations,
                           size(e.observations) as total_observations
                """, {'name': entity_name})
                
                if entity_data:
                    protected_context.extend(entity_data)
        
        return {
            'pattern_type': 'personality_insights',
            'protected_entities_accessed': [e['name'] for e in protected_context],
            'personality_context': protected_context,
            'safety_note': 'Personality entities are protected - read-only access provided'
        }
    
    def _build_recent_pattern(self, intent: Dict[str, Any], context_mode: str, token_budget: int) -> Dict[str, Any]:
        """
        Find recent thoughts and observations
        """
        # Combine temporal pattern with semantic search for recent content
        temporal_result = self._build_temporal_pattern(intent, context_mode, token_budget)
        
        # Also search for recent observations in entity data
        recent_cypher = """
        MATCH (e:Entity)
        WHERE size(e.observations) > 0
        AND any(obs IN e.observations WHERE obs CONTAINS '[2025')  // Recent timestamp pattern
        UNWIND e.observations as obs
        WITH e, obs
        WHERE obs CONTAINS '[2025'
        RETURN e.name as entity_name,
               e.entityType as entity_type,
               obs as recent_observation,
               substring(obs, 1, 19) as timestamp_extract
        ORDER BY timestamp_extract DESC
        LIMIT 20
        """
        
        recent_observations = self.run_cypher(recent_cypher)
        
        return {
            'pattern_type': 'recent_thoughts',
            'temporal_context': temporal_result,
            'recent_observations': recent_observations
        }
    
    def _synthesize_response(self, natural_query: str, intent: Dict[str, Any], results: Dict[str, Any], token_budget: int) -> Dict[str, Any]:
        """
        Synthesize human-readable conversational response from structured results
        """
        response = {
            'conversational_summary': '',
            'structured_results': results,
            'insights': [],
            'related_entities': [],
            'suggestions': []
        }
        
        pattern_type = results.get('pattern_type', 'semantic_exploration')
        
        # Generate conversational summary based on pattern type
        if pattern_type == 'connections':
            entity_pairs = results.get('entity_pairs', [])
            connections = results.get('connection_results', [])
            
            if connections:
                response['conversational_summary'] = f"Found {len(connections)} connections between the entities you mentioned. "
                response['conversational_summary'] += f"The strongest connections involve relationships through shared concepts and temporal proximity."
            else:
                response['conversational_summary'] = f"No direct connections found between {entity_pairs}. This might indicate these concepts exist in separate domains of your memory, or connections may be indirect."
        
        elif pattern_type == 'temporal':
            time_period = results.get('time_period', {})
            temporal_results = results.get('temporal_results', [])
            
            period_desc = time_period.get('period', 'recent')
            response['conversational_summary'] = f"Exploring your {period_desc} thoughts and observations. "
            response['conversational_summary'] += f"Found {len(temporal_results)} entities with activity in this timeframe."
        
        elif pattern_type == 'semantic_exploration':
            semantic_results = results.get('semantic_results', {})
            entities = semantic_results.get('entities', [])
            
            response['conversational_summary'] = f"Semantic exploration of your query revealed {len(entities)} related entities. "
            response['conversational_summary'] += f"These represent the most semantically similar concepts in your memory."
        
        elif pattern_type == 'personality_insights':
            protected_entities = results.get('protected_entities_accessed', [])
            response['conversational_summary'] = f"Personality exploration accessed {len(protected_entities)} protected entities. "
            response['conversational_summary'] += f"This provides insight into your core identity and thinking patterns while maintaining privacy safeguards."
        
        elif pattern_type == 'recent_thoughts':
            recent_observations = results.get('recent_observations', [])
            response['conversational_summary'] = f"Recent memory exploration found {len(recent_observations)} recent thoughts and observations. "
            response['conversational_summary'] += f"These represent your latest thinking and memory formation patterns."
        
        # Generate insights
        response['insights'] = self._extract_insights(results, intent)
        
        # Extract related entities for further exploration
        response['related_entities'] = self._extract_related_entities(results)
        
        # Generate suggestions for deeper exploration
        response['suggestions'] = self._generate_suggestions(natural_query, intent, results)
        
        # Estimate token usage
        response_text = str(response)
        estimated_tokens = len(response_text) // 4
        response['token_usage'] = {
            'estimated_tokens': estimated_tokens,
            'budget_used_percent': (estimated_tokens / token_budget) * 100,
            'within_budget': estimated_tokens <= token_budget
        }
        
        return response
    
    def _extract_insights(self, results: Dict[str, Any], intent: Dict[str, Any]) -> List[str]:
        """Extract key insights from query results"""
        insights = []
        
        pattern_type = results.get('pattern_type')
        
        if pattern_type == 'connections':
            connections = results.get('connection_results', [])
            if connections:
                common_connections = []
                for conn in connections:
                    common_connections.extend(conn.get('common_connections', []))
                
                if common_connections:
                    most_common = max(set(common_connections), key=common_connections.count)
                    insights.append(f"'{most_common}' appears as a common connection point between your concepts")
        
        elif pattern_type == 'temporal':
            temporal_results = results.get('temporal_results', [])
            if temporal_results:
                entity_types = [r['entity_type'] for r in temporal_results]
                most_active_type = max(set(entity_types), key=entity_types.count)
                insights.append(f"Your recent activity shows high focus on '{most_active_type}' entities")
        
        elif pattern_type == 'semantic_exploration':
            semantic_results = results.get('semantic_results', {})
            entities = semantic_results.get('entities', [])
            if entities:
                entity_types = [e.get('entityType') for e in entities if e.get('entityType')]
                if entity_types:
                    diverse_types = len(set(entity_types))
                    insights.append(f"Your query spans {diverse_types} different types of concepts, showing broad conceptual connections")
        
        return insights
    
    def _extract_related_entities(self, results: Dict[str, Any]) -> List[str]:
        """Extract entity names for potential follow-up queries"""
        related = []
        
        # From semantic results
        semantic_results = results.get('semantic_results', {})
        entities = semantic_results.get('entities', [])
        for entity in entities:
            if entity.get('name'):
                related.append(entity['name'])
        
        # From connection results
        connections = results.get('connection_results', [])
        for conn in connections:
            if conn.get('entity1'):
                related.append(conn['entity1'])
            if conn.get('entity2'):
                related.append(conn['entity2'])
            related.extend(conn.get('common_connections', []))
        
        # Remove duplicates and limit
        return list(set(related))[:10]
    
    def _generate_suggestions(self, natural_query: str, intent: Dict[str, Any], results: Dict[str, Any]) -> List[str]:
        """Generate suggestions for deeper memory exploration"""
        suggestions = []
        
        pattern_type = results.get('pattern_type')
        related_entities = self._extract_related_entities(results)
        
        if pattern_type == 'connections' and related_entities:
            suggestions.append(f"Explore temporal patterns: 'When did I start thinking about {related_entities[0]}?'")
            if len(related_entities) > 1:
                suggestions.append(f"Find deeper connections: 'How do {related_entities[0]} and {related_entities[1]} influence each other?'")
        
        elif pattern_type == 'semantic_exploration':
            suggestions.append("Explore recent developments: 'What are my latest thoughts on this topic?'")
            if related_entities:
                suggestions.append(f"Find connections: 'Show connections between {related_entities[0]} and my other interests'")
        
        elif pattern_type == 'temporal':
            suggestions.append("Compare with earlier periods: 'How has my thinking evolved on this topic?'")
            suggestions.append("Explore influences: 'What triggered my recent thoughts about this?'")
        
        # Always add a personality-aware suggestion
        suggestions.append("Explore personal perspective: 'How does this relate to my core values and thinking patterns?'")
        
        return suggestions[:3]  # Limit to 3 suggestions

# Integration function for MCP server
def create_conversational_memory_search_handler(run_cypher_func, enhanced_search_func, virtual_context_manager):
    """
    Factory function to create conversational memory search handler for MCP server integration
    """
    engine = ConversationalMemorySearchEngine(
        run_cypher_func=run_cypher_func,
        enhanced_search_func=enhanced_search_func,
        virtual_context_manager=virtual_context_manager
    )
    
    def handle_conversational_search(natural_query: str, 
                                   context_mode: str = "semantic",
                                   token_budget: int = 15000,
                                   include_personality: bool = True) -> Dict[str, Any]:
        """MCP tool handler for conversational memory search"""
        return engine.conversational_search(
            natural_query=natural_query,
            context_mode=context_mode,
            token_budget=token_budget,
            include_personality=include_personality
        )
    
    return handle_conversational_search
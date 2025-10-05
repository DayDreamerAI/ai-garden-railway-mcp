#!/usr/bin/env python3
"""
AI Garden REST API Server for ChatGPT Custom Connector
Provides REST endpoints that connect to AuraDB for multi-agent federation
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from flask import Flask, jsonify, request, make_response
from flask_cors import CORS
from neo4j import GraphDatabase
from functools import wraps
import time

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
NEO4J_URI = os.environ.get('NEO4J_URI', 'bolt://localhost:7687')
NEO4J_USERNAME = os.environ.get('NEO4J_USERNAME', 'neo4j')
NEO4J_PASSWORD = os.environ.get('NEO4J_PASSWORD')
BEARER_TOKEN = os.environ.get('RAILWAY_BEARER_TOKEN', '')
REQUIRE_AUTH = os.environ.get('REQUIRE_AUTHENTICATION', 'true').lower() == 'true'
RATE_LIMIT = int(os.environ.get('RATE_LIMIT_PER_MINUTE', '60'))
PORT = int(os.environ.get('PORT', os.environ.get('MCP_PORT', '8080')))

# Rate limiting storage
request_counts = {}

class Neo4jConnection:
    """Manages Neo4j database connection"""
    
    def __init__(self):
        self.driver = None
        self.connect()
    
    def connect(self):
        """Establish connection to Neo4j"""
        try:
            self.driver = GraphDatabase.driver(
                NEO4J_URI,
                auth=(NEO4J_USERNAME, NEO4J_PASSWORD),
                max_connection_lifetime=3600
            )
            # Test connection
            with self.driver.session() as session:
                session.run("RETURN 1")
            logger.info(f"Connected to Neo4j at {NEO4J_URI}")
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {str(e)}")
            self.driver = None
    
    def get_session(self):
        """Get a Neo4j session"""
        if not self.driver:
            self.connect()
        return self.driver.session() if self.driver else None
    
    def close(self):
        """Close the driver connection"""
        if self.driver:
            self.driver.close()

# Initialize Neo4j connection
neo4j_conn = Neo4jConnection()

def require_auth(f):
    """Decorator for authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not REQUIRE_AUTH:
            return f(*args, **kwargs)
        
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Unauthorized'}), 401
        
        token = auth_header.split(' ')[1]
        if token != BEARER_TOKEN:
            return jsonify({'error': 'Invalid token'}), 401
        
        return f(*args, **kwargs)
    return decorated_function

def rate_limit(f):
    """Decorator for rate limiting"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        client_id = request.remote_addr
        current_minute = int(time.time() / 60)
        
        if client_id not in request_counts:
            request_counts[client_id] = {}
        
        if current_minute not in request_counts[client_id]:
            request_counts[client_id] = {current_minute: 0}
        
        request_counts[client_id][current_minute] += 1
        
        if request_counts[client_id][current_minute] > RATE_LIMIT:
            return jsonify({'error': 'Rate limit exceeded'}), 429
        
        return f(*args, **kwargs)
    return decorated_function

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return 'OK', 200

@app.route('/openapi.json', methods=['GET'])
def openapi_spec():
    """OpenAPI specification for ChatGPT Custom Connector"""
    spec = {
        "openapi": "3.0.0",
        "info": {
            "title": "AI Garden Knowledge Graph API",
            "version": "1.0.0",
            "description": "REST API for accessing AI Garden knowledge graph via AuraDB"
        },
        "servers": [
            {
                "url": f"https://ai-garden-railway-mcp.railway.app",
                "description": "Production server"
            }
        ],
        "security": [
            {
                "bearerAuth": []
            }
        ],
        "paths": {
            "/search": {
                "post": {
                    "summary": "Search entities in knowledge graph",
                    "operationId": "searchEntities",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "query": {
                                            "type": "string",
                                            "description": "Search query"
                                        },
                                        "limit": {
                                            "type": "integer",
                                            "default": 5
                                        }
                                    },
                                    "required": ["query"]
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {
                            "description": "Search results",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "entities": {
                                                "type": "array",
                                                "items": {
                                                    "type": "object"
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "/entities/{name}": {
                "get": {
                    "summary": "Get entity by name",
                    "operationId": "getEntity",
                    "parameters": [
                        {
                            "name": "name",
                            "in": "path",
                            "required": True,
                            "schema": {
                                "type": "string"
                            }
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Entity details"
                        }
                    }
                }
            }
        },
        "components": {
            "securitySchemes": {
                "bearerAuth": {
                    "type": "http",
                    "scheme": "bearer"
                }
            }
        }
    }
    return jsonify(spec)

@app.route('/search', methods=['POST'])
@require_auth
@rate_limit
def search_entities():
    """Search entities in the knowledge graph"""
    try:
        data = request.get_json()
        query = data.get('query', '')
        limit = data.get('limit', 5)
        
        if not query:
            return jsonify({'error': 'Query required'}), 400
        
        session = neo4j_conn.get_session()
        if not session:
            return jsonify({'error': 'Database connection failed'}), 503
        
        try:
            # Simple text search across entity names and properties
            result = session.run("""
                MATCH (n:Entity)
                WHERE toLower(n.name) CONTAINS toLower($query)
                   OR toLower(n.entityType) CONTAINS toLower($query)
                   OR ANY(obs IN n.observations WHERE toLower(obs) CONTAINS toLower($query))
                RETURN n
                LIMIT $limit
            """, query=query, limit=limit)
            
            entities = []
            for record in result:
                node = dict(record['n'])
                # Remove embeddings to reduce payload
                if 'embedding' in node:
                    del node['embedding']
                if 'jina_embedding_v3' in node:
                    del node['jina_embedding_v3']
                entities.append(node)
            
            return jsonify({
                'entities': entities,
                'count': len(entities),
                'query': query
            })
            
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/entities/<name>', methods=['GET'])
@require_auth
@rate_limit
def get_entity(name):
    """Get a specific entity by name"""
    try:
        session = neo4j_conn.get_session()
        if not session:
            return jsonify({'error': 'Database connection failed'}), 503
        
        try:
            # Get entity and its relationships
            result = session.run("""
                MATCH (n:Entity {name: $name})
                OPTIONAL MATCH (n)-[r]-(related)
                RETURN n, 
                       collect(DISTINCT {
                           type: type(r),
                           direction: CASE WHEN startNode(r) = n THEN 'outgoing' ELSE 'incoming' END,
                           related: related.name
                       }) as relationships
            """, name=name)
            
            record = result.single()
            if not record:
                return jsonify({'error': 'Entity not found'}), 404
            
            entity = dict(record['n'])
            # Remove embeddings
            if 'embedding' in entity:
                del entity['embedding']
            if 'jina_embedding_v3' in entity:
                del entity['jina_embedding_v3']
            
            entity['relationships'] = [r for r in record['relationships'] if r['related']]
            
            return jsonify(entity)
            
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"Get entity error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/stats', methods=['GET'])
@require_auth
def get_stats():
    """Get database statistics"""
    try:
        session = neo4j_conn.get_session()
        if not session:
            return jsonify({'error': 'Database connection failed'}), 503
        
        try:
            # Get counts
            stats = {}
            
            # Entity count
            result = session.run("MATCH (n:Entity) RETURN count(n) as count")
            stats['entities'] = result.single()['count']
            
            # Relationship count
            result = session.run("MATCH ()-[r]->() RETURN count(r) as count")
            stats['relationships'] = result.single()['count']
            
            # Entity types
            result = session.run("""
                MATCH (n:Entity)
                RETURN n.entityType as type, count(n) as count
                ORDER BY count DESC
            """)
            stats['entity_types'] = [dict(record) for record in result]
            
            return jsonify(stats)
            
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"Stats error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/sync', methods=['POST'])
@require_auth
@rate_limit
def sync_agent():
    """Multi-agent synchronization endpoint"""
    try:
        data = request.get_json()
        agent_id = data.get('agent_id')
        operation = data.get('operation')
        
        # Log sync request
        logger.info(f"Sync request from {agent_id}: {operation}")
        
        # For now, just acknowledge the sync
        return jsonify({
            'status': 'acknowledged',
            'agent_id': agent_id,
            'operation': operation,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Sync error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.errorhandler(404)
def not_found(e):
    """Handle 404 errors"""
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def server_error(e):
    """Handle 500 errors"""
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    logger.info(f"Starting AI Garden REST API Server on port {PORT}")
    logger.info(f"Neo4j URI: {NEO4J_URI}")
    logger.info(f"Authentication: {'enabled' if REQUIRE_AUTH else 'disabled'}")
    logger.info(f"Rate limit: {RATE_LIMIT} requests/minute")
    
    app.run(host='0.0.0.0', port=PORT, debug=False)
#!/usr/bin/env python3
"""
Flask API server for AI Garden - Railway deployment
"""

import os
import json
from datetime import datetime
from flask import Flask, jsonify, request
from flask_cors import CORS
from neo4j import GraphDatabase

app = Flask(__name__)
CORS(app)

# Configuration
NEO4J_URI = os.environ.get('NEO4J_URI')
NEO4J_USERNAME = os.environ.get('NEO4J_USERNAME', 'neo4j')
NEO4J_PASSWORD = os.environ.get('NEO4J_PASSWORD')
BEARER_TOKEN = os.environ.get('RAILWAY_BEARER_TOKEN', '')
PORT = int(os.environ.get('PORT', 8080))

# Neo4j connection
driver = None
try:
    if NEO4J_URI and NEO4J_PASSWORD:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))
        with driver.session() as session:
            session.run("RETURN 1")
        print(f"Connected to Neo4j at {NEO4J_URI}")
        NEO4J_CONNECTED = True
    else:
        print("Neo4j credentials not configured")
        NEO4J_CONNECTED = False
except Exception as e:
    print(f"Neo4j connection failed: {e}")
    NEO4J_CONNECTED = False

@app.route('/health')
def health():
    return 'OK', 200

@app.route('/')
def index():
    return jsonify({
        "service": "AI Garden REST API",
        "status": "operational",
        "neo4j": "connected" if NEO4J_CONNECTED else "disconnected",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "endpoints": ["/", "/health", "/openapi.json", "/search", "/entities/<name>"]
    })

@app.route('/openapi.json')
def openapi():
    return jsonify({
        "openapi": "3.0.0",
        "info": {
            "title": "AI Garden Knowledge Graph API",
            "version": "1.0.0",
            "description": "REST API for AI Garden via Neo4j"
        },
        "servers": [
            {
                "url": "https://ai-garden-railway-mcp.railway.app",
                "description": "Production server"
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
                                        }
                                    },
                                    "required": ["query"]
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {
                            "description": "Search results"
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
    })

@app.route('/search', methods=['POST'])
def search():
    # Check authorization if configured
    if BEARER_TOKEN:
        auth = request.headers.get('Authorization', '')
        if not auth.startswith(f'Bearer {BEARER_TOKEN}'):
            return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json()
    query = data.get('query', '') if data else ''

    if NEO4J_CONNECTED and driver:
        try:
            with driver.session() as session:
                result = session.run("""
                    MATCH (n:Entity)
                    WHERE toLower(n.name) CONTAINS toLower($search_term)
                    RETURN n.name as name, n.entityType as type
                    LIMIT 5
                """, search_term=query)

                entities = [dict(record) for record in result]
        except Exception as e:
            entities = []
            print(f"Search error: {e}")
    else:
        # Mock data if Neo4j not connected
        entities = [
            {"name": "AI Garden", "type": "concept"},
            {"name": "Claude (Daydreamer Conversations)", "type": "ai_agent"}
        ] if "ai" in query.lower() or "garden" in query.lower() else []

    return jsonify({
        "entities": entities,
        "query": query,
        "neo4j": NEO4J_CONNECTED
    })

@app.route('/entities/<name>')
def get_entity(name):
    # Check authorization if configured
    if BEARER_TOKEN:
        auth = request.headers.get('Authorization', '')
        if not auth.startswith(f'Bearer {BEARER_TOKEN}'):
            return jsonify({'error': 'Unauthorized'}), 401

    if NEO4J_CONNECTED and driver:
        try:
            with driver.session() as session:
                result = session.run("""
                    MATCH (n:Entity {name: $entity_name})
                    RETURN n.name as name, n.entityType as type
                """, entity_name=name)
                record = result.single()

                if record:
                    return jsonify(dict(record))
                else:
                    return jsonify({"error": "Entity not found"}), 404
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    else:
        # Mock response if Neo4j not connected
        return jsonify({
            "name": name,
            "type": "mock",
            "neo4j": "disconnected"
        })

if __name__ == '__main__':
    print(f"Starting Flask API server on port {PORT}")
    print(f"Neo4j connected: {NEO4J_CONNECTED}")
    app.run(host='0.0.0.0', port=PORT)
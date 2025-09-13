#!/usr/bin/env python3
"""
Simplified REST API Server for Railway Deployment
Minimal dependencies for successful deployment
"""

import os
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import logging
from neo4j import GraphDatabase

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration from environment
PORT = int(os.environ.get('PORT', os.environ.get('MCP_PORT', '8080')))
NEO4J_URI = os.environ.get('NEO4J_URI', 'bolt://localhost:7687')
NEO4J_USERNAME = os.environ.get('NEO4J_USERNAME', 'neo4j')
NEO4J_PASSWORD = os.environ.get('NEO4J_PASSWORD', 'password')
BEARER_TOKEN = os.environ.get('RAILWAY_BEARER_TOKEN', '')

class Neo4jConnection:
    """Simple Neo4j connection manager"""
    
    def __init__(self):
        self.driver = None
        try:
            self.driver = GraphDatabase.driver(
                NEO4J_URI,
                auth=(NEO4J_USERNAME, NEO4J_PASSWORD)
            )
            logger.info(f"Connected to Neo4j at {NEO4J_URI}")
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {str(e)}")
    
    def search(self, query, limit=5):
        """Search entities"""
        if not self.driver:
            return []
        
        try:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (n:Entity)
                    WHERE toLower(n.name) CONTAINS toLower($query)
                    RETURN n.name as name, n.entityType as type
                    LIMIT $limit
                """, query=query, limit=limit)
                
                return [dict(record) for record in result]
        except Exception as e:
            logger.error(f"Search error: {str(e)}")
            return []
    
    def get_entity(self, name):
        """Get entity by name"""
        if not self.driver:
            return None
        
        try:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (n:Entity {name: $name})
                    RETURN n.name as name, n.entityType as type, n.observations as observations
                """, name=name)
                
                record = result.single()
                if record:
                    return dict(record)
                return None
        except Exception as e:
            logger.error(f"Get entity error: {str(e)}")
            return None

# Initialize Neo4j
neo4j = Neo4jConnection()

class SimpleAPIHandler(BaseHTTPRequestHandler):
    """Simple HTTP request handler"""
    
    def do_GET(self):
        """Handle GET requests"""
        parsed = urlparse(self.path)
        
        if parsed.path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'OK')
            
        elif parsed.path == '/openapi.json':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            spec = {
                "openapi": "3.0.0",
                "info": {
                    "title": "AI Garden Knowledge Graph API",
                    "version": "1.0.0",
                    "description": "REST API for AI Garden via AuraDB"
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
                            "summary": "Search entities",
                            "operationId": "searchEntities",
                            "requestBody": {
                                "required": True,
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "properties": {
                                                "query": {"type": "string"}
                                            }
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
            
            self.wfile.write(json.dumps(spec).encode())
            
        elif parsed.path.startswith('/entities/'):
            # Check authorization
            auth = self.headers.get('Authorization', '')
            if BEARER_TOKEN and not auth.startswith(f'Bearer {BEARER_TOKEN}'):
                self.send_response(401)
                self.end_headers()
                return
            
            entity_name = parsed.path.replace('/entities/', '')
            entity = neo4j.get_entity(entity_name)
            
            if entity:
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(entity).encode())
            else:
                self.send_response(404)
                self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_POST(self):
        """Handle POST requests"""
        parsed = urlparse(self.path)
        
        if parsed.path == '/search':
            # Check authorization
            auth = self.headers.get('Authorization', '')
            if BEARER_TOKEN and not auth.startswith(f'Bearer {BEARER_TOKEN}'):
                self.send_response(401)
                self.end_headers()
                return
            
            # Read body
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            
            try:
                data = json.loads(body)
                query = data.get('query', '')
                results = neo4j.search(query)
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'entities': results,
                    'query': query
                }).encode())
            except Exception as e:
                self.send_response(400)
                self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_OPTIONS(self):
        """Handle CORS preflight"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()
    
    def log_message(self, format, *args):
        """Override to use logger"""
        logger.info(f"{self.address_string()} - {format % args}")

def run_server():
    """Run the HTTP server"""
    server = HTTPServer(('0.0.0.0', PORT), SimpleAPIHandler)
    logger.info(f"AI Garden Simple API Server running on port {PORT}")
    logger.info(f"Neo4j: {NEO4J_URI}")
    logger.info(f"Auth: {'enabled' if BEARER_TOKEN else 'disabled'}")
    server.serve_forever()

if __name__ == '__main__':
    run_server()
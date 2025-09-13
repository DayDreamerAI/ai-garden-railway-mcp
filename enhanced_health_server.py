#!/usr/bin/env python3
"""
Enhanced Health Server with REST API for ChatGPT
Combines health check with AI Garden API endpoints
"""

import os
import sys
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime
from urllib.parse import urlparse

# Immediate startup confirmation
print(f"[STARTUP] Enhanced health server initializing...", file=sys.stderr, flush=True)

PORT = int(os.environ.get("PORT", os.environ.get("MCP_PORT", 8080)))
BEARER_TOKEN = os.environ.get("RAILWAY_BEARER_TOKEN", "c457969f6d9c3716ac9352e564c35d75d3952aa746982bea91ec5d23df73b827")

# Try to import neo4j, but don't fail if not available
try:
    from neo4j import GraphDatabase
    # AuraDB instance credentials
    NEO4J_URI = os.environ.get("NEO4J_URI", "neo4j+s://09a0c1c3.databases.neo4j.io")
    NEO4J_USERNAME = os.environ.get("NEO4J_USERNAME", "09a0c1c3")
    NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "03rTiZq13BJted_9S8PzDgl6Bx1L2lIFk4t3XyMBFn4")
    
    # Try to connect to Neo4j
    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))
        with driver.session() as session:
            session.run("RETURN 1")
        NEO4J_AVAILABLE = True
        print(f"[STARTUP] Connected to Neo4j at {NEO4J_URI}", file=sys.stderr, flush=True)
    except Exception as e:
        NEO4J_AVAILABLE = False
        driver = None
        print(f"[STARTUP] Neo4j connection failed: {e}", file=sys.stderr, flush=True)
except ImportError:
    NEO4J_AVAILABLE = False
    driver = None
    print("[STARTUP] Neo4j driver not available", file=sys.stderr, flush=True)

class EnhancedHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        
        if parsed.path == "/health":
            self.send_response(200)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            self.wfile.write(b"OK")
            
        elif parsed.path == "/":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            response = {
                "service": "AI Garden Railway API Server",
                "status": "operational",
                "neo4j": "connected" if NEO4J_AVAILABLE else "disconnected",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "version": "3.0.0",
                "endpoints": ["/health", "/openapi.json", "/search", "/entities/{name}"]
            }
            self.wfile.write(json.dumps(response).encode())
            
        elif parsed.path == "/openapi.json":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
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
            }
            
            self.wfile.write(json.dumps(spec).encode())
            
        elif parsed.path.startswith("/entities/"):
            # Check authorization
            auth = self.headers.get("Authorization", "")
            if not auth.startswith(f"Bearer {BEARER_TOKEN}"):
                self.send_response(401)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Unauthorized"}).encode())
                return
            
            entity_name = parsed.path.replace("/entities/", "")
            
            if NEO4J_AVAILABLE and driver:
                try:
                    with driver.session() as session:
                        result = session.run("""
                            MATCH (n:Entity {name: $name})
                            RETURN n.name as name, n.entityType as type
                        """, name=entity_name)
                        record = result.single()
                        
                        if record:
                            self.send_response(200)
                            self.send_header("Content-type", "application/json")
                            self.send_header("Access-Control-Allow-Origin", "*")
                            self.end_headers()
                            self.wfile.write(json.dumps(dict(record)).encode())
                        else:
                            self.send_response(404)
                            self.send_header("Content-type", "application/json")
                            self.end_headers()
                            self.wfile.write(json.dumps({"error": "Entity not found"}).encode())
                except Exception as e:
                    self.send_response(500)
                    self.send_header("Content-type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": str(e)}).encode())
            else:
                # Return mock data if Neo4j not available
                self.send_response(200)
                self.send_header("Content-type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "name": entity_name,
                    "type": "mock",
                    "neo4j": "disconnected"
                }).encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_POST(self):
        parsed = urlparse(self.path)
        
        if parsed.path == "/search":
            # Check authorization
            auth = self.headers.get("Authorization", "")
            if not auth.startswith(f"Bearer {BEARER_TOKEN}"):
                self.send_response(401)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Unauthorized"}).encode())
                return
            
            # Read body
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            
            try:
                data = json.loads(body)
                query = data.get("query", "")
                
                if NEO4J_AVAILABLE and driver:
                    with driver.session() as session:
                        result = session.run("""
                            MATCH (n:Entity)
                            WHERE toLower(n.name) CONTAINS toLower($query)
                            RETURN n.name as name, n.entityType as type
                            LIMIT 5
                        """, query=query)
                        
                        entities = [dict(record) for record in result]
                else:
                    # Mock data if Neo4j not available
                    entities = [
                        {"name": "AI Garden", "type": "concept"},
                        {"name": "Claude (Daydreamer Conversations)", "type": "ai_agent"},
                        {"name": "Julian Crespi", "type": "person"}
                    ] if "garden" in query.lower() or "ai" in query.lower() else []
                
                self.send_response(200)
                self.send_header("Content-type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "entities": entities,
                    "query": query,
                    "neo4j": NEO4J_AVAILABLE
                }).encode())
                
            except Exception as e:
                self.send_response(400)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_OPTIONS(self):
        """Handle CORS preflight"""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()
    
    def log_message(self, format, *args):
        # Log to stderr for Railway logs
        print(f"{datetime.utcnow().isoformat()} - {format % args}", file=sys.stderr)

def main():
    print(f"[STARTUP] Starting Enhanced Health Server on port {PORT}", flush=True)
    print(f"[STARTUP] Neo4j available: {NEO4J_AVAILABLE}", flush=True)
    server = HTTPServer(("0.0.0.0", PORT), EnhancedHandler)
    print(f"[STARTUP] Server listening on http://0.0.0.0:{PORT}", flush=True)
    print(f"[STARTUP] Endpoints: /health, /openapi.json, /search, /entities/{{name}}", flush=True)
    print("[STARTUP] Ready to accept connections!", flush=True)
    server.serve_forever()

if __name__ == "__main__":
    main()
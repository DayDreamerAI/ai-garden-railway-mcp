#!/usr/bin/env python3
"""
Simple diagnostic server for Railway debugging
Tests basic connectivity without Neo4j dependencies
"""

import os
import sys
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime

PORT = int(os.environ.get("PORT", 8080))

print(f"[DIAGNOSTIC] Starting on port {PORT}", file=sys.stderr, flush=True)
print(f"[DIAGNOSTIC] Environment variables:", file=sys.stderr, flush=True)
print(f"  NEO4J_URI: {os.environ.get('NEO4J_URI', 'NOT_SET')}", file=sys.stderr, flush=True)
print(f"  NEO4J_USERNAME: {os.environ.get('NEO4J_USERNAME', 'NOT_SET')}", file=sys.stderr, flush=True)
print(f"  NEO4J_PASSWORD: {'SET' if os.environ.get('NEO4J_PASSWORD') else 'NOT_SET'}", file=sys.stderr, flush=True)

class DiagnosticHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        print(f"[REQUEST] GET {self.path}", file=sys.stderr, flush=True)

        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            self.wfile.write(b"OK")

        elif self.path == "/":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

            response = {
                "service": "AI Garden Diagnostic Server",
                "status": "operational",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "endpoints": ["/", "/health", "/test", "/openapi.json"],
                "environment": {
                    "PORT": PORT,
                    "NEO4J_URI": os.environ.get('NEO4J_URI', 'NOT_SET'),
                    "NEO4J_USERNAME": os.environ.get('NEO4J_USERNAME', 'NOT_SET'),
                    "NEO4J_PASSWORD": 'SET' if os.environ.get('NEO4J_PASSWORD') else 'NOT_SET'
                }
            }

            self.wfile.write(json.dumps(response, indent=2).encode())

        elif self.path == "/test":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

            response = {
                "message": "Test endpoint working",
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }

            self.wfile.write(json.dumps(response).encode())

        elif self.path == "/openapi.json":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

            spec = {
                "openapi": "3.0.0",
                "info": {
                    "title": "AI Garden Diagnostic API",
                    "version": "1.0.0",
                    "description": "Diagnostic REST API for Railway deployment"
                },
                "servers": [
                    {
                        "url": "https://ai-garden-railway-mcp.railway.app",
                        "description": "Production server"
                    }
                ],
                "paths": {
                    "/": {
                        "get": {
                            "summary": "Service status",
                            "operationId": "getStatus",
                            "responses": {
                                "200": {
                                    "description": "Service status and environment"
                                }
                            }
                        }
                    },
                    "/test": {
                        "get": {
                            "summary": "Test endpoint",
                            "operationId": "testEndpoint",
                            "responses": {
                                "200": {
                                    "description": "Test response"
                                }
                            }
                        }
                    }
                }
            }

            self.wfile.write(json.dumps(spec, indent=2).encode())

        else:
            self.send_response(404)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            self.wfile.write(f"Not Found: {self.path}".encode())

    def do_POST(self):
        print(f"[REQUEST] POST {self.path}", file=sys.stderr, flush=True)

        if self.path == "/search":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)

            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

            response = {
                "message": "Search endpoint working",
                "received": json.loads(body) if body else {},
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }

            self.wfile.write(json.dumps(response).encode())
        else:
            self.send_response(404)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            self.wfile.write(f"Not Found: {self.path}".encode())

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def log_message(self, format, *args):
        print(f"{datetime.utcnow().isoformat()} - {format % args}", file=sys.stderr)

def main():
    try:
        server = HTTPServer(("0.0.0.0", PORT), DiagnosticHandler)
        print(f"[DIAGNOSTIC] Server listening on http://0.0.0.0:{PORT}", file=sys.stderr, flush=True)
        print(f"[DIAGNOSTIC] Endpoints: /, /health, /test, /openapi.json, /search", file=sys.stderr, flush=True)
        print("[DIAGNOSTIC] Ready!", file=sys.stderr, flush=True)
        server.serve_forever()
    except Exception as e:
        print(f"[ERROR] Server failed: {e}", file=sys.stderr, flush=True)
        raise

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Simple Health Server for AI Garden Railway Deployment
Provides a minimal /health endpoint that Railway can check
"""

import os
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime

PORT = int(os.environ.get("PORT", 8080))
BEARER_TOKEN = os.environ.get("RAILWAY_BEARER_TOKEN", "c457969f6d9c3716ac9352e564c35d75d3952aa746982bea91ec5d23df73b827")

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            self.wfile.write(b"OK")
        elif self.path == "/":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            response = {
                "service": "AI Garden Railway MCP Server",
                "status": "operational",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "version": "2.3.0",
                "endpoints": ["/health", "/", "/sse"]
            }
            self.wfile.write(json.dumps(response).encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_POST(self):
        # Handle POST requests for MCP endpoints
        if self.path in ["/search_nodes", "/open_nodes", "/create_entities"]:
            # Check authorization
            auth = self.headers.get("Authorization")
            if auth != f"Bearer {BEARER_TOKEN}":
                self.send_response(401)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Unauthorized"}).encode())
                return
            
            # Return mock response
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            response = {
                "status": "success",
                "message": f"Endpoint {self.path} operational",
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            self.wfile.write(json.dumps(response).encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        # Log to stdout for Railway logs
        print(f"{datetime.utcnow().isoformat()} - {format % args}")

def main():
    print(f"Starting AI Garden Health Server on port {PORT}")
    server = HTTPServer(("0.0.0.0", PORT), HealthHandler)
    print(f"Server listening on http://0.0.0.0:{PORT}")
    print(f"Health endpoint: http://0.0.0.0:{PORT}/health")
    server.serve_forever()

if __name__ == "__main__":
    main()
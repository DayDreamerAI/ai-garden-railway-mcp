#!/usr/bin/env python3
"""Debug server to check Railway environment"""

import os
import sys
import json
from http.server import HTTPServer, BaseHTTPRequestHandler

PORT = int(os.environ.get("PORT", 8080))

class DebugHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            self.wfile.write(b"OK")

        elif self.path == "/env":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()

            # Get all environment variables
            env_vars = {}
            for key, value in os.environ.items():
                # Hide sensitive values but show they exist
                if any(x in key.upper() for x in ['PASSWORD', 'TOKEN', 'SECRET', 'KEY']):
                    env_vars[key] = f"[SET - {len(value)} chars]" if value else "NOT SET"
                elif key.startswith('NEO4J'):
                    env_vars[key] = value if value else "NOT SET"
                elif key in ['PORT', 'RAILWAY_ENVIRONMENT', 'RAILWAY_PROJECT_ID']:
                    env_vars[key] = value

            response = {
                "neo4j_specific": {
                    "NEO4J_URI": os.environ.get('NEO4J_URI', 'NOT SET'),
                    "NEO4J_USERNAME": os.environ.get('NEO4J_USERNAME', 'NOT SET'),
                    "NEO4J_PASSWORD": "SET" if os.environ.get('NEO4J_PASSWORD') else "NOT SET"
                },
                "all_env_vars": sorted(env_vars.keys()),
                "railway_vars": {k: v for k, v in env_vars.items() if k.startswith('RAILWAY')}
            }

            self.wfile.write(json.dumps(response, indent=2).encode())

        else:
            self.send_response(200)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Debug Server - Try /env to see environment variables")

print(f"Starting debug server on port {PORT}")
print(f"Quick check - NEO4J_URI: {os.environ.get('NEO4J_URI', 'NOT SET')}")
print(f"Quick check - NEO4J_PASSWORD: {'SET' if os.environ.get('NEO4J_PASSWORD') else 'NOT SET'}")
print(f"Total env vars: {len(os.environ)}")

server = HTTPServer(("0.0.0.0", PORT), DebugHandler)
print(f"Debug server listening on http://0.0.0.0:{PORT}")
print("Endpoints: /health, /env")
server.serve_forever()
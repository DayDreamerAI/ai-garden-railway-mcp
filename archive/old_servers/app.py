#!/usr/bin/env python3
"""
Railway app.py entry point - runs the enhanced health server with REST API
"""

import sys
import os

# Import and run the enhanced health server
from enhanced_health_server import main

if __name__ == "__main__":
    print("[APP] Starting enhanced health server from app.py", file=sys.stderr, flush=True)
    main()
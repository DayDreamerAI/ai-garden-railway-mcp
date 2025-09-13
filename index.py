#!/usr/bin/env python3
"""
Railway entry point - runs the enhanced health server with REST API
"""

import sys
import os

# Import and run the enhanced health server
from enhanced_health_server import main

if __name__ == "__main__":
    print("[INDEX] Starting enhanced health server from index.py", file=sys.stderr, flush=True)
    main()
#!/usr/bin/env python3
"""Test environment variables"""

import os
import sys

print("Environment Variables Check")
print("=" * 50)

vars_to_check = [
    'NEO4J_URI',
    'NEO4J_USERNAME',
    'NEO4J_PASSWORD',
    'RAILWAY_BEARER_TOKEN',
    'PORT'
]

for var in vars_to_check:
    value = os.environ.get(var)
    if value:
        if 'PASSWORD' in var or 'TOKEN' in var:
            print(f"{var}: [SET - {len(value)} chars]")
        else:
            print(f"{var}: {value}")
    else:
        print(f"{var}: NOT SET")

print("=" * 50)

# Test Neo4j connection if variables are present
if os.environ.get('NEO4J_URI') and os.environ.get('NEO4J_PASSWORD'):
    print("\nTesting Neo4j connection...")
    from neo4j import GraphDatabase

    try:
        driver = GraphDatabase.driver(
            os.environ.get('NEO4J_URI'),
            auth=(os.environ.get('NEO4J_USERNAME', 'neo4j'), os.environ.get('NEO4J_PASSWORD'))
        )
        with driver.session() as session:
            result = session.run("RETURN 1 as test")
            record = result.single()
            print(f"✅ Neo4j connection successful! Test query returned: {record['test']}")
        driver.close()
    except Exception as e:
        print(f"❌ Neo4j connection failed: {e}")
else:
    print("\n⚠️  Neo4j credentials not configured - cannot test connection")
#!/usr/bin/env python3
"""Test Neo4j connection and check what's in the database"""

import os
from neo4j import GraphDatabase

# Get credentials from environment or use test values
NEO4J_URI = os.environ.get('NEO4J_URI', 'neo4j+s://52214062.databases.neo4j.io')
NEO4J_USERNAME = os.environ.get('NEO4J_USERNAME', 'neo4j')
NEO4J_PASSWORD = os.environ.get('NEO4J_PASSWORD')

if not NEO4J_PASSWORD:
    print("Please set NEO4J_PASSWORD environment variable")
    exit(1)

print(f"Connecting to: {NEO4J_URI}")
print(f"Username: {NEO4J_USERNAME}")

try:
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))

    with driver.session() as session:
        # Test connection
        result = session.run("RETURN 1 as test")
        print("✅ Connected successfully!")

        # Count all nodes
        result = session.run("MATCH (n) RETURN count(n) as total")
        total = result.single()['total']
        print(f"\nTotal nodes in database: {total}")

        # Get node labels
        result = session.run("CALL db.labels() YIELD label RETURN label")
        labels = [record['label'] for record in result]
        print(f"\nNode labels: {labels}")

        # Count nodes by label
        for label in labels:
            result = session.run(f"MATCH (n:`{label}`) RETURN count(n) as count")
            count = result.single()['count']
            print(f"  {label}: {count} nodes")

        # Sample some entities
        print("\nSample nodes:")
        result = session.run("""
            MATCH (n)
            RETURN labels(n) as labels, n.name as name
            LIMIT 10
        """)
        for record in result:
            print(f"  {record['labels']}: {record['name']}")

    driver.close()

except Exception as e:
    print(f"❌ Error: {e}")
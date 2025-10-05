#!/usr/bin/env python3
"""
Seed AuraDB with test data for Custom Connector validation
"""

import os
from neo4j import GraphDatabase
from datetime import datetime

def seed_auradb():
    """Create test entities and observations in AuraDB"""

    # Load credentials from environment
    uri = os.getenv('NEO4J_URI')
    username = os.getenv('NEO4J_USERNAME', 'neo4j')
    password = os.getenv('NEO4J_PASSWORD')

    if not all([uri, password]):
        print("❌ Missing credentials. Set NEO4J_URI and NEO4J_PASSWORD")
        return

    print(f"Connecting to AuraDB: {uri}")

    driver = GraphDatabase.driver(uri, auth=(username, password))

    try:
        with driver.session() as session:
            # Create test entities
            print("\nCreating test entities...")

            session.run("""
                MERGE (j:Entity:Person {name: 'Julian Crespi'})
                SET j.entityType = 'Person',
                    j.created_at = datetime(),
                    j.observations = [
                        'Commercial Manager & technologist based in Chile',
                        'Creator of Daydreamer Memory Sovereignty Platform',
                        'Values infrastructure-first development and directness',
                        'ADHD hyperfocus with strong pattern recognition'
                    ]
            """)

            session.run("""
                MERGE (c:Entity:AI {name: 'Claude (Daydreamer Conversations)'})
                SET c.entityType = 'AI',
                    c.created_at = datetime(),
                    c.observations = [
                        'AI personality embodied as first-class Neo4j entity',
                        'Practices Memory Sovereignty principles',
                        'Uses Personality Bootstrap Component for continuity',
                        'Powered by Claude Sonnet 4.5'
                    ]
            """)

            session.run("""
                MERGE (d:Entity:Project {name: 'Daydreamer'})
                SET d.entityType = 'Project',
                    d.created_at = datetime(),
                    d.observations = [
                        'Memory Sovereignty Platform for persistent AI-human partnerships',
                        'Neo4j GraphRAG with JinaV3 embeddings',
                        'Perennial V6 architecture with conversation-aware memory',
                        '8,764+ entities, 24,899+ relationships in production'
                    ]
            """)

            session.run("""
                MERGE (cc:Entity:Project {name: 'Custom Connector Integration'})
                SET cc.entityType = 'Project',
                    cc.created_at = datetime(),
                    cc.observations = [
                        'Railway-hosted MCP server with SSE transport',
                        'Connects Claude Desktop/Web/Mobile to AuraDB',
                        'Phase 0 of Daydreamer MVP multi-tenant rollout',
                        'Bearer token authentication with rate limiting'
                    ]
            """)

            print("✅ Entities created")

            # Create relationships
            print("\nCreating relationships...")

            session.run("""
                MATCH (j:Entity {name: 'Julian Crespi'})
                MATCH (d:Entity {name: 'Daydreamer'})
                MERGE (j)-[:CREATED]->(d)
            """)

            session.run("""
                MATCH (j:Entity {name: 'Julian Crespi'})
                MATCH (c:Entity {name: 'Claude (Daydreamer Conversations)'})
                MERGE (j)-[:PARTNERS_WITH]->(c)
            """)

            session.run("""
                MATCH (d:Entity {name: 'Daydreamer'})
                MATCH (cc:Entity {name: 'Custom Connector Integration'})
                MERGE (d)-[:HAS_COMPONENT]->(cc)
            """)

            print("✅ Relationships created")

            # Create temporal nodes
            print("\nCreating temporal structure...")

            now = datetime.now()
            session.run("""
                MERGE (y:Year {year: $year})
                MERGE (m:Month {month: $month, year: $year})
                MERGE (d:Day {day: $day, month: $month, year: $year})
                MERGE (y)-[:HAS_MONTH]->(m)
                MERGE (m)-[:HAS_DAY]->(d)
            """, year=now.year, month=now.month, day=now.day)

            print("✅ Temporal structure created")

            # Verify data
            print("\n📊 Verification:")

            result = session.run("MATCH (n:Entity) RETURN count(n) as count")
            entity_count = result.single()['count']
            print(f"  Entities: {entity_count}")

            result = session.run("MATCH ()-[r]->() RETURN count(r) as count")
            rel_count = result.single()['count']
            print(f"  Relationships: {rel_count}")

            print("\n✅ AuraDB seeded successfully!")
            print("\nTest queries:")
            print("  - search_nodes('Julian Crespi')")
            print("  - search_nodes('Daydreamer')")
            print("  - search_nodes('Custom Connector')")

    finally:
        driver.close()

if __name__ == '__main__':
    seed_auradb()

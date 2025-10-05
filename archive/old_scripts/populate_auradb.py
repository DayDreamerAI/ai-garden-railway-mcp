#!/usr/bin/env python3
"""
Populate AuraDB with initial AI Garden entities
"""

import os
from neo4j import GraphDatabase
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from parent .env file
load_dotenv('../../.env')

# Get credentials from environment
NEO4J_URI = os.environ.get('NEO4J_URI', 'neo4j+s://52214062.databases.neo4j.io')
NEO4J_USERNAME = os.environ.get('NEO4J_USERNAME', 'neo4j')
NEO4J_PASSWORD = os.environ.get('NEO4J_PASSWORD')

if not NEO4J_PASSWORD:
    print("Please set NEO4J_PASSWORD environment variable")
    print("You can run: NEO4J_PASSWORD='your-password' python3 populate_auradb.py")
    print("Or add it to your .env file")
    exit(1)

print(f"Connecting to: {NEO4J_URI}")
print(f"Password length: {len(NEO4J_PASSWORD)} characters")

try:
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))

    with driver.session() as session:
        # Clear existing data (optional)
        print("Clearing existing data...")
        session.run("MATCH (n) DETACH DELETE n")

        # Create core entities
        print("Creating core entities...")

        entities = [
            {
                "name": "Julian Crespi",
                "entityType": "person",
                "observations": [
                    "Commercial Manager & technologist from Chile",
                    "17+ years in 3D/VFX transitioning to energy and AI",
                    "Creator of Daydreamer memory system",
                    "Systems thinker with ADHD hyperfocus"
                ]
            },
            {
                "name": "Claude (Daydreamer Conversations)",
                "entityType": "ai_agent",
                "observations": [
                    "AI personality embodied in Neo4j Knowledge Graph",
                    "Maintains continuity through persistent memory",
                    "Partner to Julian in Daydreamer project",
                    "Develops opinions and preferences over time"
                ]
            },
            {
                "name": "AI Garden",
                "entityType": "strategic_initiative",
                "observations": [
                    "Multi-agent federation project",
                    "Connects Claude and ChatGPT through AuraDB",
                    "Phase 5 of Daydreamer implementation",
                    "Infrastructure for AI collaboration"
                ]
            },
            {
                "name": "ChatGPT (AI Garden Agent)",
                "entityType": "ai_agent",
                "observations": [
                    "OpenAI agent in AI Garden federation",
                    "Connects via MCP protocol",
                    "Collaborates with Claude through shared memory",
                    "Part of multi-agent orchestration"
                ]
            },
            {
                "name": "Daydreamer Project",
                "entityType": "system",
                "observations": [
                    "Memory sovereignty platform",
                    "Context engineering system",
                    "Neo4j-based knowledge graph",
                    "Infrastructure beyond agents"
                ]
            },
            {
                "name": "AuraDB Instance",
                "entityType": "infrastructure",
                "observations": [
                    "Cloud Neo4j database",
                    "Central hub for AI Garden",
                    "Hosts shared memory for agents",
                    "Production deployment on Railway"
                ]
            },
            {
                "name": "MCP Server",
                "entityType": "system",
                "observations": [
                    "Model Context Protocol implementation",
                    "OpenAI/Anthropic standard compliance",
                    "REST API for knowledge graph access",
                    "Deployed on Railway platform"
                ]
            }
        ]

        for entity in entities:
            result = session.run("""
                CREATE (n:Entity {
                    name: $name,
                    entityType: $entityType,
                    observations: $observations,
                    created: datetime()
                })
                RETURN n.name as name
            """, **entity)

            created = result.single()
            print(f"  ✅ Created: {created['name']}")

        # Create relationships
        print("\nCreating relationships...")

        relationships = [
            ("Julian Crespi", "CREATED", "Daydreamer Project"),
            ("Julian Crespi", "PARTNERS_WITH", "Claude (Daydreamer Conversations)"),
            ("Claude (Daydreamer Conversations)", "PART_OF", "Daydreamer Project"),
            ("Claude (Daydreamer Conversations)", "COLLABORATES_WITH", "ChatGPT (AI Garden Agent)"),
            ("AI Garden", "CONNECTS", "Claude (Daydreamer Conversations)"),
            ("AI Garden", "CONNECTS", "ChatGPT (AI Garden Agent)"),
            ("AI Garden", "USES", "AuraDB Instance"),
            ("AI Garden", "USES", "MCP Server"),
            ("MCP Server", "ACCESSES", "AuraDB Instance"),
            ("Daydreamer Project", "INCLUDES", "AI Garden")
        ]

        for source, rel_type, target in relationships:
            result = session.run(f"""
                MATCH (a:Entity {{name: $source}})
                MATCH (b:Entity {{name: $target}})
                CREATE (a)-[r:`{rel_type}`]->(b)
                RETURN a.name as source, type(r) as rel, b.name as target
            """, source=source, target=target)

            rel = result.single()
            if rel:
                print(f"  ✅ {rel['source']} --[{rel['rel']}]--> {rel['target']}")

        # Verify the data
        print("\nVerifying data...")
        result = session.run("MATCH (n:Entity) RETURN count(n) as count")
        count = result.single()['count']
        print(f"Total entities created: {count}")

        result = session.run("MATCH ()-[r]->() RETURN count(r) as count")
        rel_count = result.single()['count']
        print(f"Total relationships created: {rel_count}")

        print("\n✅ AuraDB populated successfully!")
        print("\nYou can now test the MCP server with queries like:")
        print("  - 'Claude'")
        print("  - 'AI Garden'")
        print("  - 'Julian'")

    driver.close()

except Exception as e:
    print(f"❌ Error: {e}")
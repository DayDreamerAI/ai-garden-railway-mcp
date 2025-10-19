#!/usr/bin/env python3
"""
V5 Chunk Migration to V6 Observation Schema
Migrates legacy Chunk and MacroChunk nodes to V6 compliance.

Created: October 19, 2025
Issue: Audit found 3,427 Chunk nodes and MacroChunk nodes missing V6 labels
Target: Add :Observation:Perennial:Entity labels to legacy chunks

Usage:
    python migrate_v5_chunks_to_v6.py --dry-run  # Preview changes
    python migrate_v5_chunks_to_v6.py            # Execute migration
"""

import os
import sys
import argparse
import logging
from datetime import datetime, UTC
from neo4j import GraphDatabase
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment
load_dotenv()

# Neo4j Configuration
NEO4J_URI = os.environ.get('NEO4J_URI')
NEO4J_USERNAME = os.environ.get('NEO4J_USERNAME', 'neo4j')
NEO4J_PASSWORD = os.environ.get('NEO4J_PASSWORD')


def validate_chunk_node(tx, chunk_id: str) -> dict:
    """Validate a single chunk node before migration"""
    query = """
    MATCH (c) WHERE elementId(c) = $chunk_id
    RETURN
        labels(c) as current_labels,
        c.content IS NOT NULL as has_content,
        c.created_at IS NOT NULL as has_created_at,
        c.jina_vec_v3 IS NOT NULL as has_embedding,
        c.timestamp IS NOT NULL as has_v5_timestamp
    """
    result = tx.run(query, chunk_id=chunk_id)
    record = result.single()
    return dict(record) if record else None


def migrate_chunk_node(tx, chunk_id: str, dry_run: bool = False) -> dict:
    """
    Migrate a single Chunk node to V6 schema

    Steps:
    1. Add missing V6 labels (:Observation:Perennial:Entity)
    2. Keep existing content, embeddings, temporal binding
    3. No data loss - purely additive
    """

    if dry_run:
        # Preview what would change
        query = """
        MATCH (c) WHERE elementId(c) = $chunk_id
        RETURN
            elementId(c) as id,
            labels(c) as current_labels,
            c.content[0..100] as content_preview
        """
        result = tx.run(query, chunk_id=chunk_id)
        record = result.single()
        return {
            'id': record['id'],
            'current_labels': record['current_labels'],
            'content_preview': record['content_preview'],
            'would_add_labels': ['Observation', 'Perennial', 'Entity']
        }

    # Execute migration
    query = """
    MATCH (c) WHERE elementId(c) = $chunk_id
    SET c:Observation:Perennial:Entity
    SET c.v6_migrated = true
    SET c.v6_migration_date = $migration_date
    RETURN
        elementId(c) as id,
        labels(c) as new_labels
    """

    result = tx.run(query,
                    chunk_id=chunk_id,
                    migration_date=datetime.now(UTC).isoformat())
    record = result.single()

    return {
        'id': record['id'],
        'new_labels': record['new_labels'],
        'status': 'migrated'
    }


def find_legacy_chunks(tx) -> list:
    """Find all Chunk nodes missing V6 labels"""

    query = """
    MATCH (c:Chunk)
    WHERE NOT c:Observation
    RETURN
        elementId(c) as id,
        labels(c) as labels,
        c.content[0..100] as content_preview,
        c.created_at as created_at
    ORDER BY c.created_at DESC
    LIMIT 5000
    """

    result = tx.run(query)
    return [dict(record) for record in result]


def find_macro_chunks(tx) -> list:
    """Find MacroChunk nodes for analysis"""

    query = """
    MATCH (mc:MacroChunk)
    RETURN
        elementId(mc) as id,
        labels(mc) as labels,
        size((mc)-[]->()) as relationship_count,
        mc.created_at as created_at
    LIMIT 100
    """

    result = tx.run(query)
    return [dict(record) for record in result]


def get_migration_stats(driver) -> dict:
    """Get current migration status"""

    with driver.session() as session:
        # Count legacy chunks
        legacy_chunks = session.run("""
            MATCH (c:Chunk)
            WHERE NOT c:Observation
            RETURN count(c) as count
        """).single()['count']

        # Count macro chunks
        macro_chunks = session.run("""
            MATCH (mc:MacroChunk)
            RETURN count(mc) as count
        """).single()['count']

        # Count already migrated
        migrated_chunks = session.run("""
            MATCH (c:Chunk:Observation)
            RETURN count(c) as count
        """).single()['count']

        return {
            'legacy_chunks': legacy_chunks,
            'macro_chunks': macro_chunks,
            'migrated_chunks': migrated_chunks,
            'total_chunks': legacy_chunks + migrated_chunks
        }


def migrate_chunks(driver, dry_run: bool = False, limit: int = None):
    """Main migration function"""

    logger.info("=" * 60)
    logger.info("V5 Chunk Migration to V6 Observation Schema")
    logger.info("=" * 60)

    # Get initial stats
    stats = get_migration_stats(driver)
    logger.info(f"📊 Pre-migration stats:")
    logger.info(f"   Legacy Chunks (missing V6 labels): {stats['legacy_chunks']}")
    logger.info(f"   Already Migrated: {stats['migrated_chunks']}")
    logger.info(f"   MacroChunks (analysis needed): {stats['macro_chunks']}")
    logger.info("")

    if dry_run:
        logger.info("🧪 DRY RUN MODE - No changes will be made")
        logger.info("")

    # Find legacy chunks
    with driver.session() as session:
        legacy_chunks = session.execute_read(find_legacy_chunks)

        if not legacy_chunks:
            logger.info("✅ No legacy chunks found - migration complete!")
            return

        logger.info(f"🔍 Found {len(legacy_chunks)} legacy chunks to migrate")

        if limit:
            legacy_chunks = legacy_chunks[:limit]
            logger.info(f"⚠️  Limited to first {limit} chunks")

        # Migrate each chunk
        migrated = 0
        failed = 0

        for i, chunk in enumerate(legacy_chunks, 1):
            try:
                result = session.execute_write(
                    migrate_chunk_node,
                    chunk['id'],
                    dry_run
                )

                if dry_run:
                    logger.info(f"[{i}/{len(legacy_chunks)}] Would migrate: {chunk['id']}")
                    logger.info(f"   Current: {chunk['labels']}")
                    logger.info(f"   Would add: {result['would_add_labels']}")
                else:
                    logger.info(f"[{i}/{len(legacy_chunks)}] ✅ Migrated: {result['id']}")
                    migrated += 1

                if i % 100 == 0:
                    logger.info(f"Progress: {i}/{len(legacy_chunks)} ({i/len(legacy_chunks)*100:.1f}%)")

            except Exception as e:
                logger.error(f"❌ Failed to migrate chunk {chunk['id']}: {e}")
                failed += 1

        # Final stats
        logger.info("")
        logger.info("=" * 60)
        if dry_run:
            logger.info(f"🧪 DRY RUN COMPLETE - {len(legacy_chunks)} chunks would be migrated")
        else:
            logger.info(f"✅ MIGRATION COMPLETE")
            logger.info(f"   Migrated: {migrated}")
            logger.info(f"   Failed: {failed}")

            # Get updated stats
            final_stats = get_migration_stats(driver)
            logger.info(f"   Remaining legacy chunks: {final_stats['legacy_chunks']}")


def analyze_macro_chunks(driver):
    """Analyze MacroChunk nodes to determine action"""

    logger.info("")
    logger.info("=" * 60)
    logger.info("MacroChunk Analysis")
    logger.info("=" * 60)

    with driver.session() as session:
        macro_chunks = session.execute_read(find_macro_chunks)

        if not macro_chunks:
            logger.info("✅ No MacroChunk nodes found")
            return

        logger.info(f"Found {len(macro_chunks)} MacroChunk nodes")
        logger.info("")
        logger.info("Sample MacroChunks:")
        for i, mc in enumerate(macro_chunks[:5], 1):
            logger.info(f"{i}. ID: {mc['id']}")
            logger.info(f"   Labels: {mc['labels']}")
            logger.info(f"   Relationships: {mc['relationship_count']}")
            logger.info(f"   Created: {mc['created_at']}")

        logger.info("")
        logger.info("⚠️  MacroChunk nodes require manual analysis:")
        logger.info("   1. Determine if they should be migrated to V6 Observation schema")
        logger.info("   2. Or archived if they're deprecated V5 artifacts")
        logger.info("   3. Check if any code still creates MacroChunk nodes")


def main():
    parser = argparse.ArgumentParser(description='Migrate V5 Chunks to V6 Observation Schema')
    parser.add_argument('--dry-run', action='store_true', help='Preview changes without executing')
    parser.add_argument('--limit', type=int, help='Limit number of chunks to migrate (for testing)')
    parser.add_argument('--analyze-macro', action='store_true', help='Analyze MacroChunk nodes')

    args = parser.parse_args()

    # Validate environment
    if not NEO4J_URI or not NEO4J_PASSWORD:
        logger.error("❌ NEO4J_URI or NEO4J_PASSWORD not set")
        sys.exit(1)

    # Connect to Neo4j
    driver = GraphDatabase.driver(
        NEO4J_URI,
        auth=(NEO4J_USERNAME, NEO4J_PASSWORD)
    )

    try:
        driver.verify_connectivity()
        logger.info(f"✅ Connected to Neo4j: {NEO4J_URI}")
        logger.info("")

        # Run migration
        migrate_chunks(driver, dry_run=args.dry_run, limit=args.limit)

        # Analyze MacroChunks if requested
        if args.analyze_macro:
            analyze_macro_chunks(driver)

    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        sys.exit(1)
    finally:
        driver.close()


if __name__ == "__main__":
    main()

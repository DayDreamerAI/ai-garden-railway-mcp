#!/usr/bin/env python3
"""
Observation Reclassification Script
Reclassifies 18,878 legacy "general" observations using semantic_classifier

Created: October 19, 2025
Issue: Audit found 97.5% observations misclassified as "general" (legacy pre-v6.3.2 data)
Target: Reclassify all observations with semantic_theme = "general" using proper classifier

Usage:
    python reclassify_observations.py --dry-run  # Preview changes
    python reclassify_observations.py --batch 100  # Reclassify in batches of 100
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

# Import semantic classifier
try:
    from semantic_classifier import SemanticThemeClassifier
    classifier = SemanticThemeClassifier()
    logger.info("✅ Semantic classifier loaded")
except ImportError as e:
    logger.error(f"❌ Failed to import semantic_classifier: {e}")
    sys.exit(1)

# Neo4j Configuration
NEO4J_URI = os.environ.get('NEO4J_URI')
NEO4J_USERNAME = os.environ.get('NEO4J_USERNAME', 'neo4j')
NEO4J_PASSWORD = os.environ.get('NEO4J_PASSWORD')


def get_classification_stats(driver) -> dict:
    """Get current theme distribution"""
    with driver.session() as session:
        result = session.run("""
            MATCH (o:Observation)
            WHERE o.semantic_theme IS NOT NULL
            RETURN o.semantic_theme as theme, count(*) as count
            ORDER BY count DESC
        """)

        stats = {}
        total = 0
        for record in result:
            theme = record['theme']
            count = record['count']
            stats[theme] = count
            total += count

        return {
            'distribution': stats,
            'total': total,
            'general_count': stats.get('general', 0),
            'general_percent': (stats.get('general', 0) / total * 100) if total > 0 else 0
        }


def find_misclassified_observations(tx, limit: int = 100) -> list:
    """Find observations classified as 'general' for reclassification"""
    query = """
    MATCH (o:Observation)
    WHERE o.semantic_theme = 'general'
      AND o.content IS NOT NULL
    RETURN
        elementId(o) as id,
        o.content as content,
        o.created_at as created_at
    ORDER BY o.created_at DESC
    LIMIT $limit
    """

    result = tx.run(query, limit=limit)
    return [dict(record) for record in result]


def reclassify_observation(tx, obs_id: str, new_theme: str, dry_run: bool = False) -> dict:
    """Reclassify a single observation"""

    if dry_run:
        # Preview only
        query = """
        MATCH (o) WHERE elementId(o) = $obs_id
        RETURN
            elementId(o) as id,
            o.semantic_theme as old_theme,
            o.content[0..100] as content_preview
        """
        result = tx.run(query, obs_id=obs_id)
        record = result.single()

        return {
            'id': record['id'],
            'old_theme': record['old_theme'],
            'new_theme': new_theme,
            'content_preview': record['content_preview'],
            'status': 'preview'
        }

    # Execute reclassification
    query = """
    MATCH (o) WHERE elementId(o) = $obs_id
    SET o.semantic_theme = $new_theme
    SET o.reclassified_at = $timestamp
    SET o.reclassification_version = 'v6.3.5'
    RETURN
        elementId(o) as id,
        o.semantic_theme as new_theme
    """

    result = tx.run(query,
                    obs_id=obs_id,
                    new_theme=new_theme,
                    timestamp=datetime.now(UTC).isoformat())
    record = result.single()

    return {
        'id': record['id'],
        'new_theme': record['new_theme'],
        'status': 'reclassified'
    }


def reclassify_batch(driver, batch_size: int = 100, dry_run: bool = False, max_batches: int = None):
    """Main reclassification function"""

    logger.info("=" * 60)
    logger.info("Observation Reclassification - Semantic Theme Correction")
    logger.info("=" * 60)

    # Get initial stats
    stats = get_classification_stats(driver)
    logger.info(f"📊 Pre-reclassification stats:")
    logger.info(f"   Total observations: {stats['total']}")
    logger.info(f"   'general' theme: {stats['general_count']} ({stats['general_percent']:.1f}%)")
    logger.info("")

    logger.info(f"Theme distribution:")
    for theme, count in sorted(stats['distribution'].items(), key=lambda x: x[1], reverse=True):
        pct = count / stats['total'] * 100
        logger.info(f"   {theme:15s}: {count:5d} ({pct:5.1f}%)")
    logger.info("")

    if stats['general_count'] == 0:
        logger.info("✅ No observations need reclassification!")
        return

    if dry_run:
        logger.info("🧪 DRY RUN MODE - No changes will be made")
        logger.info("")

    # Reclassify in batches
    total_reclassified = 0
    total_failed = 0
    batch_num = 0
    theme_changes = {}

    while True:
        batch_num += 1

        if max_batches and batch_num > max_batches:
            logger.info(f"⏹️  Reached max batches limit: {max_batches}")
            break

        # Find next batch
        with driver.session() as session:
            observations = session.execute_read(find_misclassified_observations, batch_size)

            if not observations:
                logger.info("✅ No more observations to reclassify")
                break

            logger.info(f"📦 Batch {batch_num}: Processing {len(observations)} observations...")

            # Reclassify each observation
            batch_success = 0
            batch_failed = 0

            for i, obs in enumerate(observations, 1):
                try:
                    # Classify using semantic classifier
                    new_theme = classifier.classify(obs['content'])

                    # Update database
                    result = session.execute_write(
                        reclassify_observation,
                        obs['id'],
                        new_theme,
                        dry_run
                    )

                    if dry_run:
                        if i <= 5:  # Show first 5 previews per batch
                            logger.info(f"   [{i}] Would change: general → {new_theme}")
                            logger.info(f"       Content: {result['content_preview']}")
                    else:
                        # Track theme changes
                        theme_changes[new_theme] = theme_changes.get(new_theme, 0) + 1
                        batch_success += 1

                        if i % 10 == 0:
                            logger.info(f"   Progress: {i}/{len(observations)} in batch {batch_num}")

                except Exception as e:
                    logger.error(f"❌ Failed to reclassify {obs['id']}: {e}")
                    batch_failed += 1

            total_reclassified += batch_success
            total_failed += batch_failed

            if dry_run:
                logger.info(f"✅ Batch {batch_num}: Would reclassify {len(observations)} observations")
            else:
                logger.info(f"✅ Batch {batch_num}: Reclassified {batch_success}, Failed {batch_failed}")
                logger.info(f"   Cumulative: {total_reclassified} reclassified, {total_failed} failed")
                logger.info("")

    # Final stats
    logger.info("")
    logger.info("=" * 60)

    if dry_run:
        logger.info(f"🧪 DRY RUN COMPLETE")
        logger.info(f"   Would process {batch_num} batches")
        logger.info(f"   Would reclassify ~{stats['general_count']} observations")
    else:
        logger.info(f"✅ RECLASSIFICATION COMPLETE")
        logger.info(f"   Processed {batch_num} batches")
        logger.info(f"   Reclassified: {total_reclassified}")
        logger.info(f"   Failed: {total_failed}")
        logger.info("")

        logger.info(f"Theme changes:")
        for theme, count in sorted(theme_changes.items(), key=lambda x: x[1], reverse=True):
            logger.info(f"   general → {theme:15s}: {count:5d}")

        # Get updated stats
        logger.info("")
        final_stats = get_classification_stats(driver)
        logger.info(f"📊 Post-reclassification stats:")
        logger.info(f"   'general' theme: {final_stats['general_count']} ({final_stats['general_percent']:.1f}%)")
        logger.info("")
        logger.info(f"Final distribution:")
        for theme, count in sorted(final_stats['distribution'].items(), key=lambda x: x[1], reverse=True):
            pct = count / final_stats['total'] * 100
            logger.info(f"   {theme:15s}: {count:5d} ({pct:5.1f}%)")


def main():
    parser = argparse.ArgumentParser(description='Reclassify observations from "general" to proper themes')
    parser.add_argument('--dry-run', action='store_true', help='Preview changes without executing')
    parser.add_argument('--batch', type=int, default=100, help='Batch size (default: 100)')
    parser.add_argument('--max-batches', type=int, help='Maximum batches to process (for testing)')

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

        # Run reclassification
        reclassify_batch(
            driver,
            batch_size=args.batch,
            dry_run=args.dry_run,
            max_batches=args.max_batches
        )

    except Exception as e:
        logger.error(f"❌ Reclassification failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        driver.close()


if __name__ == "__main__":
    main()

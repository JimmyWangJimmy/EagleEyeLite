#!/usr/bin/env python
"""
Index Rules Script - Index audit rules into ChromaDB for RAG retrieval.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger
from config.settings import settings
from eagleeye.rag.indexer import RuleIndexer


def main():
    """Index all rules from master rulebook."""
    logger.info("=" * 60)
    logger.info("EagleEye Lite - Rule Indexing")
    logger.info("=" * 60)

    # Initialize indexer
    indexer = RuleIndexer()

    # Check rulebook exists
    rulebook_path = settings.rulebook_path
    if not rulebook_path.exists():
        logger.error(f"Rulebook not found: {rulebook_path}")
        sys.exit(1)

    logger.info(f"Rulebook: {rulebook_path}")
    logger.info(f"ChromaDB: {settings.rag.persist_directory}")
    logger.info(f"Embedding: {settings.rag.embedding_model}")

    # Index rules
    try:
        count = indexer.index_from_file(
            jsonl_path=rulebook_path,
            clear_existing=True
        )

        logger.info(f"Successfully indexed {count} rules")

        # Print stats
        stats = indexer.get_collection_stats()
        logger.info(f"Collection stats: {stats}")

        # Verify by retrieving all rules
        all_rules = indexer.get_all_rules()
        logger.info(f"Verification: {len(all_rules)} rules in collection")

        # Print rule distribution
        categories = {}
        priorities = {}
        for rule in all_rules:
            cat = rule["metadata"].get("category", "Unknown")
            pri = rule["metadata"].get("priority", "Unknown")
            categories[cat] = categories.get(cat, 0) + 1
            priorities[pri] = priorities.get(pri, 0) + 1

        logger.info("Rule distribution by category:")
        for cat, count in sorted(categories.items()):
            logger.info(f"  {cat}: {count}")

        logger.info("Rule distribution by priority:")
        for pri, count in sorted(priorities.items()):
            logger.info(f"  {pri}: {count}")

    except Exception as e:
        logger.error(f"Indexing failed: {e}")
        sys.exit(1)

    logger.info("=" * 60)
    logger.info("Indexing complete!")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()

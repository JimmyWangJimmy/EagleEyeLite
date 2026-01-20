"""
Rule Retriever - Hybrid retrieval with semantic similarity and keyword boosting.
"""

import json
from pathlib import Path
from typing import Optional
from loguru import logger

import sys
sys.path.insert(0, str(__file__).rsplit("\\", 3)[0])

from config.settings import settings
from eagleeye.rag.indexer import RuleIndexer
from eagleeye.models.rule import Rule


class RuleRetriever:
    """
    Hybrid rule retriever combining semantic search with keyword matching.
    Supports filtering by category and priority.
    """

    def __init__(
        self,
        indexer: RuleIndexer = None,
        similarity_threshold: float = None,
        top_k: int = None
    ):
        """
        Initialize retriever.

        Args:
            indexer: RuleIndexer instance (creates new if not provided)
            similarity_threshold: Minimum similarity score (0-1)
            top_k: Maximum number of results to return
        """
        self.indexer = indexer or RuleIndexer()
        self.similarity_threshold = similarity_threshold or settings.rag.similarity_threshold
        self.top_k = top_k or settings.rag.top_k

        # Cache for loaded rules
        self._rules_cache: dict[str, Rule] = {}

    def load_rules_to_cache(self, jsonl_path: str | Path = None):
        """Load all rules into memory cache for quick access."""
        jsonl_path = jsonl_path or settings.rulebook_path
        rules = self.indexer.load_rules_from_jsonl(jsonl_path)

        for rule in rules:
            self._rules_cache[rule.rule_id] = rule

        logger.info(f"Loaded {len(rules)} rules to cache")

    def get_rule(self, rule_id: str) -> Optional[Rule]:
        """Get rule by ID from cache or file."""
        if rule_id in self._rules_cache:
            return self._rules_cache[rule_id]

        # Try to load from file if not in cache
        if not self._rules_cache:
            self.load_rules_to_cache()

        return self._rules_cache.get(rule_id)

    def retrieve_by_query(
        self,
        query: str,
        top_k: int = None,
        category_filter: list[str] = None,
        priority_filter: list[str] = None
    ) -> list[tuple[Rule, float]]:
        """
        Retrieve rules by semantic similarity to query.

        Args:
            query: Search query text
            top_k: Override default top_k
            category_filter: Filter by categories (e.g., ["CL", "FM"])
            priority_filter: Filter by priorities (e.g., ["Critical", "High"])

        Returns:
            List of (Rule, similarity_score) tuples
        """
        top_k = top_k or self.top_k

        # Build where clause for filtering
        where_clause = None
        if category_filter or priority_filter:
            conditions = []
            if category_filter:
                conditions.append({"category": {"$in": category_filter}})
            if priority_filter:
                conditions.append({"priority": {"$in": priority_filter}})

            if len(conditions) == 1:
                where_clause = conditions[0]
            else:
                where_clause = {"$and": conditions}

        # Query ChromaDB
        try:
            results = self.indexer.collection.query(
                query_texts=[query],
                n_results=top_k * 2,  # Get more to filter by threshold
                where=where_clause,
                include=["documents", "metadatas", "distances"]
            )
        except Exception as e:
            logger.error(f"Query error: {e}")
            return []

        # Process results
        retrieved = []
        if results["ids"] and results["ids"][0]:
            for i, rule_id in enumerate(results["ids"][0]):
                # Convert distance to similarity (cosine distance -> similarity)
                distance = results["distances"][0][i] if results["distances"] else 0
                similarity = 1 - distance

                if similarity >= self.similarity_threshold:
                    rule = self.get_rule(rule_id)
                    if rule:
                        retrieved.append((rule, similarity))

        # Sort by similarity and limit
        retrieved.sort(key=lambda x: x[1], reverse=True)
        return retrieved[:top_k]

    def retrieve_by_keywords(
        self,
        keywords: list[str],
        top_k: int = None
    ) -> list[tuple[Rule, float]]:
        """
        Retrieve rules by keyword matching.

        Args:
            keywords: List of keywords to match
            top_k: Maximum results

        Returns:
            List of (Rule, match_score) tuples
        """
        top_k = top_k or self.top_k

        # Ensure rules are loaded
        if not self._rules_cache:
            self.load_rules_to_cache()

        # Score rules by keyword overlap
        scored_rules = []
        for rule in self._rules_cache.values():
            rule_keywords = set(rule.trigger_keywords)
            query_keywords = set(keywords)

            # Calculate Jaccard similarity
            intersection = len(rule_keywords & query_keywords)
            if intersection > 0:
                union = len(rule_keywords | query_keywords)
                score = intersection / union
                scored_rules.append((rule, score))

        # Sort by score
        scored_rules.sort(key=lambda x: x[1], reverse=True)
        return scored_rules[:top_k]

    def retrieve_hybrid(
        self,
        query: str,
        keywords: list[str] = None,
        top_k: int = None,
        semantic_weight: float = 0.7,
        keyword_weight: float = 0.3,
        category_filter: list[str] = None,
        priority_filter: list[str] = None
    ) -> list[tuple[Rule, float]]:
        """
        Hybrid retrieval combining semantic similarity and keyword matching.

        Args:
            query: Search query text
            keywords: Optional additional keywords
            top_k: Maximum results
            semantic_weight: Weight for semantic similarity
            keyword_weight: Weight for keyword matching
            category_filter: Filter by categories
            priority_filter: Filter by priorities

        Returns:
            List of (Rule, combined_score) tuples
        """
        top_k = top_k or self.top_k

        # Get semantic results
        semantic_results = self.retrieve_by_query(
            query, top_k=top_k * 2,
            category_filter=category_filter,
            priority_filter=priority_filter
        )

        # Get keyword results if keywords provided
        keyword_results = []
        if keywords:
            keyword_results = self.retrieve_by_keywords(keywords, top_k=top_k * 2)

        # Combine scores
        combined_scores: dict[str, tuple[Rule, float]] = {}

        for rule, score in semantic_results:
            combined_scores[rule.rule_id] = (rule, score * semantic_weight)

        for rule, score in keyword_results:
            if rule.rule_id in combined_scores:
                existing_rule, existing_score = combined_scores[rule.rule_id]
                combined_scores[rule.rule_id] = (
                    existing_rule,
                    existing_score + score * keyword_weight
                )
            else:
                combined_scores[rule.rule_id] = (rule, score * keyword_weight)

        # Sort and filter
        results = list(combined_scores.values())
        results.sort(key=lambda x: x[1], reverse=True)

        # Apply filters if not already done in semantic search
        if category_filter:
            results = [(r, s) for r, s in results if r.category in category_filter]
        if priority_filter:
            results = [(r, s) for r, s in results if r.priority in priority_filter]

        return results[:top_k]

    def retrieve_for_document(
        self,
        document_text: str,
        extracted_keywords: list[str] = None,
        top_k: int = None
    ) -> list[tuple[Rule, float]]:
        """
        Retrieve relevant rules for a document.

        Args:
            document_text: Document text content
            extracted_keywords: Keywords extracted from document
            top_k: Maximum results

        Returns:
            List of (Rule, relevance_score) tuples
        """
        # Use first 1000 chars as query to avoid token limits
        query_text = document_text[:1000]

        return self.retrieve_hybrid(
            query=query_text,
            keywords=extracted_keywords,
            top_k=top_k
        )

    def retrieve_all_rules(self) -> list[Rule]:
        """Get all rules for exhaustive checking."""
        if not self._rules_cache:
            self.load_rules_to_cache()
        return list(self._rules_cache.values())

    def retrieve_by_category(self, category: str) -> list[Rule]:
        """Get all rules in a specific category."""
        if not self._rules_cache:
            self.load_rules_to_cache()

        return [
            rule for rule in self._rules_cache.values()
            if rule.category == category
        ]

    def retrieve_critical_rules(self) -> list[Rule]:
        """Get all critical priority rules."""
        if not self._rules_cache:
            self.load_rules_to_cache()

        return [
            rule for rule in self._rules_cache.values()
            if rule.priority == "Critical"
        ]

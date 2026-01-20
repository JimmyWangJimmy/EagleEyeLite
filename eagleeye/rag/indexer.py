"""
Rule Indexer - ChromaDB-based indexing for audit rules.
"""

import json
from pathlib import Path
from typing import Optional
from loguru import logger
import chromadb
from chromadb.config import Settings as ChromaSettings

import sys
sys.path.insert(0, str(__file__).rsplit("\\", 3)[0])

from config.settings import settings
from eagleeye.models.rule import Rule


class RuleIndexer:
    """
    ChromaDB indexer for audit rules.
    Indexes rules by trigger_keywords + subject + description.
    Uses bge-small-zh-v1.5 for memory-efficient Chinese embeddings.
    """

    def __init__(
        self,
        collection_name: str = None,
        persist_directory: str = None,
        embedding_model: str = None
    ):
        """
        Initialize rule indexer.

        Args:
            collection_name: ChromaDB collection name
            persist_directory: Directory for persistent storage
            embedding_model: Sentence transformer model name
        """
        self.collection_name = collection_name or settings.rag.collection_name
        self.persist_directory = persist_directory or settings.rag.persist_directory
        self.embedding_model = embedding_model or settings.rag.embedding_model

        self._client: Optional[chromadb.Client] = None
        self._collection = None
        self._embedding_function = None

    @property
    def client(self) -> chromadb.Client:
        """Lazy initialization of ChromaDB client."""
        if self._client is None:
            logger.info(f"Initializing ChromaDB at {self.persist_directory}")
            self._client = chromadb.PersistentClient(
                path=self.persist_directory,
                settings=ChromaSettings(anonymized_telemetry=False)
            )
        return self._client

    @property
    def embedding_function(self):
        """Lazy load embedding function."""
        if self._embedding_function is None:
            from chromadb.utils import embedding_functions
            logger.info(f"Loading embedding model: {self.embedding_model}")
            self._embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name=self.embedding_model
            )
        return self._embedding_function

    @property
    def collection(self):
        """Get or create collection."""
        if self._collection is None:
            self._collection = self.client.get_or_create_collection(
                name=self.collection_name,
                embedding_function=self.embedding_function,
                metadata={"hnsw:space": "cosine"}
            )
        return self._collection

    def load_rules_from_jsonl(self, jsonl_path: str | Path) -> list[Rule]:
        """
        Load rules from JSONL file.

        Args:
            jsonl_path: Path to JSONL file

        Returns:
            List of Rule objects
        """
        jsonl_path = Path(jsonl_path)
        rules = []

        logger.info(f"Loading rules from {jsonl_path}")

        with open(jsonl_path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue

                rule = Rule.from_jsonl_line(line)
                if rule:
                    rules.append(rule)
                else:
                    logger.warning(f"Failed to parse rule at line {line_num}")

        logger.info(f"Loaded {len(rules)} rules")
        return rules

    def index_rules(self, rules: list[Rule], clear_existing: bool = False) -> int:
        """
        Index rules into ChromaDB.

        Args:
            rules: List of Rule objects to index
            clear_existing: Whether to clear existing collection

        Returns:
            Number of rules indexed
        """
        if clear_existing:
            logger.info("Clearing existing collection")
            try:
                self.client.delete_collection(self.collection_name)
                self._collection = None
            except Exception:
                pass

        # Prepare documents for indexing
        ids = []
        documents = []
        metadatas = []

        for rule in rules:
            index_doc = rule.to_index_document()
            ids.append(index_doc["id"])
            documents.append(index_doc["document"])
            metadatas.append(index_doc["metadata"])

        # Batch insert
        logger.info(f"Indexing {len(rules)} rules...")
        self.collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas
        )

        logger.info(f"Successfully indexed {len(rules)} rules")
        return len(rules)

    def index_from_file(
        self,
        jsonl_path: str | Path = None,
        clear_existing: bool = True
    ) -> int:
        """
        Load and index rules from JSONL file.

        Args:
            jsonl_path: Path to JSONL file (default: settings.rulebook_path)
            clear_existing: Whether to clear existing index

        Returns:
            Number of rules indexed
        """
        jsonl_path = jsonl_path or settings.rulebook_path
        rules = self.load_rules_from_jsonl(jsonl_path)
        return self.index_rules(rules, clear_existing)

    def get_rule_by_id(self, rule_id: str) -> Optional[dict]:
        """
        Retrieve a rule by its ID.

        Args:
            rule_id: Rule identifier (e.g., "CL-001")

        Returns:
            Rule metadata dict or None
        """
        try:
            result = self.collection.get(ids=[rule_id])
            if result["ids"]:
                return {
                    "id": result["ids"][0],
                    "document": result["documents"][0] if result["documents"] else "",
                    "metadata": result["metadatas"][0] if result["metadatas"] else {}
                }
        except Exception as e:
            logger.error(f"Error retrieving rule {rule_id}: {e}")

        return None

    def get_all_rules(self) -> list[dict]:
        """
        Retrieve all indexed rules.

        Returns:
            List of rule dicts
        """
        try:
            result = self.collection.get()
            rules = []
            for i in range(len(result["ids"])):
                rules.append({
                    "id": result["ids"][i],
                    "document": result["documents"][i] if result["documents"] else "",
                    "metadata": result["metadatas"][i] if result["metadatas"] else {}
                })
            return rules
        except Exception as e:
            logger.error(f"Error retrieving all rules: {e}")
            return []

    def get_collection_stats(self) -> dict:
        """Get collection statistics."""
        try:
            count = self.collection.count()
            return {
                "collection_name": self.collection_name,
                "rule_count": count,
                "embedding_model": self.embedding_model,
                "persist_directory": self.persist_directory
            }
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {}

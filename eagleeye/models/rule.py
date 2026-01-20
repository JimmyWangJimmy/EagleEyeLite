"""
Rule data model for audit rules.
"""

from typing import Optional
from pydantic import BaseModel, Field


class Rule(BaseModel):
    """Represents an audit rule from the rulebook."""

    rule_id: str = Field(..., description="Unique rule identifier (e.g., CL-001)")
    category: str = Field(..., description="Rule category: CL/FM/LC/OP")
    subject: str = Field(..., description="Rule subject/title in Chinese")
    trigger_keywords: list[str] = Field(default_factory=list, description="Keywords that trigger this rule")
    logic_schema: str = Field(..., description="Logic expression for evaluation")
    priority: str = Field(..., description="Priority level: Critical/High/Medium")
    description: str = Field(..., description="Detailed rule description")
    source: str = Field(default="", description="Reference source")
    linked_models: list[str] = Field(default_factory=list, description="Related rule IDs")
    audit_procedures: list[str] = Field(default_factory=list, description="Audit procedure steps")

    @property
    def is_critical(self) -> bool:
        """Check if rule is critical priority."""
        return self.priority == "Critical"

    @property
    def searchable_text(self) -> str:
        """Generate text for embedding and search."""
        keywords = " ".join(self.trigger_keywords)
        return f"{self.subject} {keywords} {self.description}"

    def to_index_document(self) -> dict:
        """Convert to document format for ChromaDB indexing."""
        return {
            "id": self.rule_id,
            "document": self.searchable_text,
            "metadata": {
                "rule_id": self.rule_id,
                "category": self.category,
                "subject": self.subject,
                "priority": self.priority,
                "keywords": ",".join(self.trigger_keywords),
            }
        }

    @classmethod
    def from_jsonl_line(cls, line: str) -> Optional["Rule"]:
        """Parse a rule from JSONL line."""
        import json
        try:
            data = json.loads(line.strip())
            return cls(**data)
        except (json.JSONDecodeError, ValueError):
            return None

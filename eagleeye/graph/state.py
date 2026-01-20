"""
Audit State - TypedDict definition for LangGraph workflow.
"""

from typing import TypedDict, Optional, Annotated
from operator import add

from eagleeye.models.document import Document, FinancialData
from eagleeye.models.rule import Rule
from eagleeye.models.finding import Finding, AuditReport


class AuditState(TypedDict, total=False):
    """
    State container for the audit workflow.
    All fields are optional to support incremental state updates.
    """

    # Input
    pdf_path: str
    check_all_rules: bool  # Whether to check all rules or use RAG retrieval

    # Document parsing
    document: Optional[Document]
    raw_text: str
    financial_data: Optional[FinancialData]
    extracted_keywords: list[str]
    parse_error: Optional[str]

    # Rule retrieval
    retrieved_rules: list[Rule]
    all_rules: list[Rule]
    current_rule_index: int
    current_rule: Optional[Rule]

    # Audit evaluation
    findings: Annotated[list[Finding], add]  # Accumulate findings
    rules_checked: int
    rules_with_violations: int

    # Report
    report: Optional[AuditReport]
    report_markdown: str
    report_json: dict

    # Workflow control
    should_continue: bool
    error_message: Optional[str]

    # Timing
    start_time: float
    end_time: float


def create_initial_state(
    pdf_path: str,
    check_all_rules: bool = True
) -> AuditState:
    """
    Create initial state for audit workflow.

    Args:
        pdf_path: Path to PDF file to audit
        check_all_rules: Whether to check all rules or use retrieval

    Returns:
        Initial AuditState
    """
    import time

    return AuditState(
        pdf_path=pdf_path,
        check_all_rules=check_all_rules,
        document=None,
        raw_text="",
        financial_data=None,
        extracted_keywords=[],
        parse_error=None,
        retrieved_rules=[],
        all_rules=[],
        current_rule_index=0,
        current_rule=None,
        findings=[],
        rules_checked=0,
        rules_with_violations=0,
        report=None,
        report_markdown="",
        report_json={},
        should_continue=True,
        error_message=None,
        start_time=time.time(),
        end_time=0.0
    )

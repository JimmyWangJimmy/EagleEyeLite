"""
Audit Workflow - LangGraph state machine for audit orchestration.
"""

from typing import Optional
from loguru import logger
from langgraph.graph import StateGraph, END

import sys
sys.path.insert(0, str(__file__).rsplit("\\", 3)[0])

from eagleeye.graph.state import AuditState, create_initial_state
from eagleeye.graph.nodes import (
    parse_node,
    retrieve_node,
    audit_node,
    report_node,
    should_continue_audit
)


def build_audit_workflow() -> StateGraph:
    """
    Build the LangGraph workflow for financial document auditing.

    Flow:
        parse -> retrieve -> audit (loop) -> report

    Returns:
        Compiled StateGraph
    """
    logger.info("Building audit workflow graph")

    # Create graph with AuditState
    workflow = StateGraph(AuditState)

    # Add nodes
    workflow.add_node("parse", parse_node)
    workflow.add_node("retrieve", retrieve_node)
    workflow.add_node("audit", audit_node)
    workflow.add_node("report", report_node)

    # Set entry point
    workflow.set_entry_point("parse")

    # Add edges
    # parse -> retrieve
    workflow.add_edge("parse", "retrieve")

    # retrieve -> audit
    workflow.add_edge("retrieve", "audit")

    # audit -> conditional (audit or report)
    workflow.add_conditional_edges(
        "audit",
        should_continue_audit,
        {
            "audit": "audit",
            "report": "report"
        }
    )

    # report -> END
    workflow.add_edge("report", END)

    # Compile the graph
    compiled = workflow.compile()

    logger.info("Workflow graph compiled successfully")
    return compiled


class AuditWorkflowRunner:
    """
    Runner class for executing audit workflows.
    """

    def __init__(self):
        """Initialize workflow runner."""
        self._workflow = None

    @property
    def workflow(self):
        """Lazy load workflow."""
        if self._workflow is None:
            self._workflow = build_audit_workflow()
        return self._workflow

    def run(
        self,
        pdf_path: str,
        check_all_rules: bool = True,
        stream: bool = False
    ) -> AuditState:
        """
        Run audit workflow on a PDF document.

        Args:
            pdf_path: Path to PDF file
            check_all_rules: Whether to check all rules or use RAG
            stream: Whether to stream intermediate states

        Returns:
            Final AuditState with results
        """
        logger.info(f"Starting audit workflow for: {pdf_path}")

        # Create initial state
        initial_state = create_initial_state(
            pdf_path=pdf_path,
            check_all_rules=check_all_rules
        )

        if stream:
            # Stream mode - yield intermediate states
            final_state = None
            for state in self.workflow.stream(initial_state):
                final_state = state
                # Log progress
                if "audit" in state:
                    audit_state = state["audit"]
                    if "current_rule_index" in audit_state:
                        idx = audit_state["current_rule_index"]
                        total = len(audit_state.get("retrieved_rules", []))
                        logger.info(f"Progress: {idx}/{total} rules checked")
            return final_state
        else:
            # Invoke mode - run to completion
            final_state = self.workflow.invoke(initial_state)
            return final_state

    def run_with_callbacks(
        self,
        pdf_path: str,
        on_parse: callable = None,
        on_retrieve: callable = None,
        on_audit: callable = None,
        on_report: callable = None,
        check_all_rules: bool = True
    ) -> AuditState:
        """
        Run workflow with callbacks for progress tracking.

        Args:
            pdf_path: Path to PDF file
            on_parse: Callback after parsing
            on_retrieve: Callback after retrieval
            on_audit: Callback after each rule audit
            on_report: Callback after report generation
            check_all_rules: Whether to check all rules

        Returns:
            Final AuditState
        """
        initial_state = create_initial_state(
            pdf_path=pdf_path,
            check_all_rules=check_all_rules
        )

        final_state = None
        for event in self.workflow.stream(initial_state):
            for node_name, node_state in event.items():
                if node_name == "parse" and on_parse:
                    on_parse(node_state)
                elif node_name == "retrieve" and on_retrieve:
                    on_retrieve(node_state)
                elif node_name == "audit" and on_audit:
                    on_audit(node_state)
                elif node_name == "report" and on_report:
                    on_report(node_state)

                final_state = node_state

        return final_state


def run_audit(
    pdf_path: str,
    check_all_rules: bool = True,
    output_path: Optional[str] = None
) -> dict:
    """
    Convenience function to run a complete audit.

    Args:
        pdf_path: Path to PDF file
        check_all_rules: Whether to check all rules
        output_path: Optional path to save report

    Returns:
        Audit results dict
    """
    runner = AuditWorkflowRunner()
    result = runner.run(pdf_path, check_all_rules=check_all_rules)

    # Save report if output path provided
    if output_path and "report_markdown" in result:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(result["report_markdown"])
        logger.info(f"Report saved to: {output_path}")

    return {
        "success": result.get("error_message") is None,
        "rules_checked": result.get("rules_checked", 0),
        "violations_found": result.get("rules_with_violations", 0),
        "findings": result.get("findings", []),
        "report": result.get("report"),
        "markdown": result.get("report_markdown", ""),
        "json": result.get("report_json", {}),
        "error": result.get("error_message")
    }

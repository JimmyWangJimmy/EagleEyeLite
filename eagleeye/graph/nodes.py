"""
Audit Nodes - LangGraph node functions for the audit workflow.
"""

import time
from loguru import logger

import sys
sys.path.insert(0, str(__file__).rsplit("\\", 3)[0])

from eagleeye.graph.state import AuditState
from eagleeye.tools.pdf_parser import PDFParser
from eagleeye.rag.retriever import RuleRetriever
from eagleeye.audit.evaluator import LogicEvaluator
from eagleeye.audit.reporter import AuditReporter
from eagleeye.models.finding import Finding, AuditReport, ViolationSeverity
from eagleeye.models.rule import Rule


def parse_node(state: AuditState) -> dict:
    """
    Parse PDF document and extract financial data.

    Args:
        state: Current workflow state

    Returns:
        State updates with parsed document
    """
    logger.info(f"[PARSE] Starting PDF parsing: {state['pdf_path']}")

    try:
        parser = PDFParser()
        document = parser.parse(state["pdf_path"])

        logger.info(f"[PARSE] Parsed {document.total_pages} pages using {document.parse_method}")
        logger.info(f"[PARSE] Found {len(document.tables)} tables")

        keywords = document.extract_keywords()
        logger.info(f"[PARSE] Extracted keywords: {keywords}")

        return {
            "document": document,
            "raw_text": document.raw_text,
            "financial_data": document.financial_data,
            "extracted_keywords": keywords,
            "parse_error": None
        }

    except Exception as e:
        logger.error(f"[PARSE] Error: {e}")
        return {
            "parse_error": str(e),
            "should_continue": False,
            "error_message": f"PDF parsing failed: {e}"
        }


def retrieve_node(state: AuditState) -> dict:
    """
    Retrieve relevant rules using RAG or load all rules.

    Args:
        state: Current workflow state

    Returns:
        State updates with retrieved rules
    """
    logger.info("[RETRIEVE] Starting rule retrieval")

    try:
        retriever = RuleRetriever()
        retriever.load_rules_to_cache()

        if state.get("check_all_rules", True):
            # Get all rules for exhaustive checking
            all_rules = retriever.retrieve_all_rules()
            logger.info(f"[RETRIEVE] Loaded all {len(all_rules)} rules")

            return {
                "all_rules": all_rules,
                "retrieved_rules": all_rules,
                "current_rule_index": 0
            }
        else:
            # Use RAG retrieval based on document content
            raw_text = state.get("raw_text", "")
            keywords = state.get("extracted_keywords", [])

            retrieved = retriever.retrieve_for_document(
                document_text=raw_text,
                extracted_keywords=keywords,
                top_k=20  # Get top 20 relevant rules
            )

            rules = [rule for rule, score in retrieved]
            logger.info(f"[RETRIEVE] Retrieved {len(rules)} relevant rules")

            return {
                "retrieved_rules": rules,
                "all_rules": retriever.retrieve_all_rules(),
                "current_rule_index": 0
            }

    except Exception as e:
        logger.error(f"[RETRIEVE] Error: {e}")
        return {
            "error_message": f"Rule retrieval failed: {e}",
            "should_continue": False
        }


def audit_node(state: AuditState) -> dict:
    """
    Evaluate current rule against financial data.
    Processes one rule at a time for memory efficiency.

    Args:
        state: Current workflow state

    Returns:
        State updates with evaluation results
    """
    rules = state.get("retrieved_rules", [])
    current_index = state.get("current_rule_index", 0)

    if current_index >= len(rules):
        logger.info("[AUDIT] All rules checked")
        return {"should_continue": False}

    rule = rules[current_index]
    logger.info(f"[AUDIT] Evaluating rule {current_index + 1}/{len(rules)}: {rule.rule_id} - {rule.subject}")

    try:
        evaluator = LogicEvaluator()
        financial_data = state.get("financial_data")

        if financial_data is None:
            logger.warning(f"[AUDIT] No financial data available for {rule.rule_id}")
            return {
                "current_rule_index": current_index + 1,
                "rules_checked": state.get("rules_checked", 0) + 1
            }

        # Convert financial data to evaluation dict
        eval_dict = financial_data.to_eval_dict()

        # Evaluate the rule
        result = evaluator.evaluate(rule.logic_schema, eval_dict)

        findings = []
        rules_with_violations = state.get("rules_with_violations", 0)

        if result["violation"]:
            logger.warning(f"[AUDIT] Violation detected: {rule.rule_id}")

            # Map priority to severity
            severity_map = {
                "Critical": ViolationSeverity.CRITICAL,
                "High": ViolationSeverity.HIGH,
                "Medium": ViolationSeverity.MEDIUM,
                "Low": ViolationSeverity.LOW
            }

            finding = Finding(
                rule_id=rule.rule_id,
                rule_subject=rule.subject,
                category=rule.category,
                severity=severity_map.get(rule.priority, ViolationSeverity.MEDIUM),
                logic_schema=rule.logic_schema,
                evaluation_result=True,
                evidence=result.get("evidence", {}),
                calculated_value=result.get("calculated_value"),
                threshold_value=result.get("threshold_value"),
                description=rule.description,
                audit_procedures=rule.audit_procedures
            )
            findings.append(finding)
            rules_with_violations += 1
        else:
            logger.debug(f"[AUDIT] No violation for {rule.rule_id}")

        return {
            "current_rule_index": current_index + 1,
            "current_rule": rule,
            "rules_checked": state.get("rules_checked", 0) + 1,
            "rules_with_violations": rules_with_violations,
            "findings": findings,  # Will be accumulated via Annotated[list, add]
            "should_continue": current_index + 1 < len(rules)
        }

    except Exception as e:
        logger.error(f"[AUDIT] Error evaluating {rule.rule_id}: {e}")
        # Continue to next rule even on error
        return {
            "current_rule_index": current_index + 1,
            "rules_checked": state.get("rules_checked", 0) + 1
        }


def report_node(state: AuditState) -> dict:
    """
    Generate final audit report.

    Args:
        state: Current workflow state

    Returns:
        State updates with generated report
    """
    logger.info("[REPORT] Generating audit report")

    try:
        document = state.get("document")
        findings = state.get("findings", [])

        reporter = AuditReporter()

        report = reporter.create_report(
            document_name=document.file_name if document else "Unknown",
            document_path=state.get("pdf_path", ""),
            findings=findings,
            total_rules_checked=state.get("rules_checked", 0)
        )

        # Calculate execution time
        start_time = state.get("start_time", time.time())
        end_time = time.time()
        report.execution_time_seconds = end_time - start_time

        # Generate outputs
        markdown_report = report.to_markdown()
        json_report = report.to_json()

        logger.info(f"[REPORT] Generated report: {report.total_violations} violations found")

        return {
            "report": report,
            "report_markdown": markdown_report,
            "report_json": json_report,
            "end_time": end_time
        }

    except Exception as e:
        logger.error(f"[REPORT] Error: {e}")
        return {
            "error_message": f"Report generation failed: {e}"
        }


def should_continue_audit(state: AuditState) -> str:
    """
    Conditional edge function to determine if audit should continue.

    Args:
        state: Current workflow state

    Returns:
        Next node name: "audit" or "report"
    """
    if state.get("error_message"):
        return "report"

    if state.get("should_continue", False):
        return "audit"

    return "report"

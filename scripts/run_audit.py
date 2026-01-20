#!/usr/bin/env python
"""
Run Audit Script - Execute audit workflow on a PDF document.
"""

import sys
import argparse
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger
from config.settings import settings
from eagleeye.graph.workflow import run_audit, AuditWorkflowRunner
from eagleeye.audit.reporter import AuditReporter


def setup_logging(verbose: bool = False):
    """Configure logging."""
    logger.remove()
    level = "DEBUG" if verbose else "INFO"
    logger.add(sys.stderr, level=level, format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}")


def main():
    """Run audit on specified PDF."""
    parser = argparse.ArgumentParser(
        description="EagleEye Lite - Financial Document Audit"
    )
    parser.add_argument(
        "pdf_path",
        type=str,
        help="Path to PDF file to audit"
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        default=None,
        help="Output report path (default: auto-generated)"
    )
    parser.add_argument(
        "--all-rules",
        action="store_true",
        default=True,
        help="Check all rules (default: True)"
    )
    parser.add_argument(
        "--rag-only",
        action="store_true",
        help="Use RAG retrieval instead of checking all rules"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Also output JSON report"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output"
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging(args.verbose)

    # Validate input
    pdf_path = Path(args.pdf_path)
    if not pdf_path.exists():
        logger.error(f"PDF file not found: {pdf_path}")
        sys.exit(1)

    logger.info("=" * 60)
    logger.info("EagleEye Lite - Financial Document Audit")
    logger.info("=" * 60)
    logger.info(f"Input: {pdf_path}")

    # Determine check mode
    check_all = not args.rag_only

    # Run audit
    try:
        result = run_audit(
            pdf_path=str(pdf_path),
            check_all_rules=check_all
        )

        if not result["success"]:
            logger.error(f"Audit failed: {result['error']}")
            sys.exit(1)

        # Print summary
        logger.info("")
        logger.info("=" * 60)
        logger.info("AUDIT RESULTS")
        logger.info("=" * 60)
        logger.info(f"Rules checked: {result['rules_checked']}")
        logger.info(f"Violations found: {result['violations_found']}")

        if result['findings']:
            logger.info("")
            logger.info("Violations by severity:")
            report = result['report']
            if report:
                logger.info(f"  Critical: {report.critical_count}")
                logger.info(f"  High: {report.high_count}")
                logger.info(f"  Medium: {report.medium_count}")
                logger.info(f"  Low: {report.low_count}")

        # Save reports
        reporter = AuditReporter()

        if args.output:
            output_path = Path(args.output)
            if output_path.suffix == ".json":
                reporter.save_json(report, output_path.name)
            else:
                reporter.save_markdown(report, output_path.name)
            logger.info(f"Report saved: {args.output}")
        else:
            # Auto-generate filenames
            if result['report']:
                md_path, json_path = reporter.save_both(result['report'])
                logger.info(f"Markdown report: {md_path}")
                if args.json:
                    logger.info(f"JSON report: {json_path}")

        # Print markdown to console if verbose
        if args.verbose and result['markdown']:
            logger.info("")
            logger.info("=" * 60)
            logger.info("FULL REPORT")
            logger.info("=" * 60)
            # Handle Windows console encoding
            try:
                print(result['markdown'])
            except UnicodeEncodeError:
                # Remove emojis for Windows console compatibility
                clean_markdown = result['markdown']
                for emoji in ['🔴', '🟠', '🟡', '🟢', '⚪', '📈', '📉', '➡️', '✅', '⚠️']:
                    clean_markdown = clean_markdown.replace(emoji, '*')
                print(clean_markdown)

    except Exception as e:
        logger.error(f"Audit error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)

    logger.info("")
    logger.info("Audit complete!")


def run_mock_audit():
    """
    Run audit with mock data for testing without PDF.
    """
    import json
    from eagleeye.models.document import FinancialData
    from eagleeye.rag.retriever import RuleRetriever
    from eagleeye.audit.evaluator import LogicEvaluator
    from eagleeye.models.finding import Finding, ViolationSeverity

    logger.info("Running mock audit with test data...")

    # Load mock data
    mock_data_path = project_root / "tests" / "fixtures" / "mock_financial_data.json"
    if not mock_data_path.exists():
        logger.error(f"Mock data not found: {mock_data_path}")
        return

    with open(mock_data_path, "r", encoding="utf-8") as f:
        mock_data = json.load(f)

    financial_data = mock_data["scenarios"]["violations"]["financial_data"]

    # Load rules
    retriever = RuleRetriever()
    retriever.load_rules_to_cache()
    rules = retriever.retrieve_all_rules()

    # Evaluate rules
    evaluator = LogicEvaluator()
    findings = []

    for rule in rules:
        result = evaluator.evaluate(rule.logic_schema, financial_data)

        if result["violation"]:
            severity_map = {
                "Critical": ViolationSeverity.CRITICAL,
                "High": ViolationSeverity.HIGH,
                "Medium": ViolationSeverity.MEDIUM,
            }

            finding = Finding(
                rule_id=rule.rule_id,
                rule_subject=rule.subject,
                category=rule.category,
                severity=severity_map.get(rule.priority, ViolationSeverity.MEDIUM),
                logic_schema=rule.logic_schema,
                evaluation_result=True,
                evidence=result.get("evidence", {}),
                description=rule.description,
                audit_procedures=rule.audit_procedures
            )
            findings.append(finding)
            logger.warning(f"Violation: {rule.rule_id} - {rule.subject}")

    # Generate report
    reporter = AuditReporter()
    report = reporter.create_report(
        document_name="mock_financial_data.json",
        document_path=str(mock_data_path),
        findings=findings,
        total_rules_checked=len(rules)
    )

    md_path, json_path = reporter.save_both(report)

    logger.info(f"Found {len(findings)} violations out of {len(rules)} rules")
    logger.info(f"Report saved to: {md_path}")

    return report


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--mock":
        setup_logging(verbose=True)
        run_mock_audit()
    else:
        main()

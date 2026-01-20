"""
Test Pipeline - Integration tests for EagleEye Lite audit workflow.
"""

import json
import pytest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import settings
from eagleeye.models.rule import Rule
from eagleeye.models.document import FinancialData, Document
from eagleeye.models.finding import Finding, AuditReport, ViolationSeverity
from eagleeye.rag.indexer import RuleIndexer
from eagleeye.rag.retriever import RuleRetriever
from eagleeye.audit.evaluator import LogicEvaluator
from eagleeye.audit.reporter import AuditReporter


# Fixtures path
FIXTURES_PATH = Path(__file__).parent / "fixtures"


@pytest.fixture
def mock_financial_data():
    """Load mock financial data from fixtures."""
    with open(FIXTURES_PATH / "mock_financial_data.json", "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def violation_data(mock_financial_data):
    """Get violation scenario data."""
    return mock_financial_data["scenarios"]["violations"]["financial_data"]


@pytest.fixture
def clean_data(mock_financial_data):
    """Get clean scenario data."""
    return mock_financial_data["scenarios"]["clean"]["financial_data"]


@pytest.fixture
def rule_indexer():
    """Create rule indexer instance."""
    return RuleIndexer()


@pytest.fixture
def rule_retriever():
    """Create rule retriever instance."""
    return RuleRetriever()


@pytest.fixture
def logic_evaluator():
    """Create logic evaluator instance."""
    return LogicEvaluator()


class TestRuleLoading:
    """Test rule loading from JSONL."""

    def test_load_rules_from_jsonl(self, rule_indexer):
        """Test loading rules from master rulebook."""
        rules = rule_indexer.load_rules_from_jsonl(settings.rulebook_path)

        assert len(rules) == 34, f"Expected 34 rules, got {len(rules)}"

        # Verify rule structure
        for rule in rules:
            assert rule.rule_id is not None
            assert rule.category in ["CL", "FM", "LC", "OP"]
            assert rule.priority in ["Critical", "High", "Medium"]
            assert len(rule.logic_schema) > 0

    def test_rule_categories(self, rule_indexer):
        """Test rule categories distribution."""
        rules = rule_indexer.load_rules_from_jsonl(settings.rulebook_path)

        categories = {}
        for rule in rules:
            categories[rule.category] = categories.get(rule.category, 0) + 1

        assert "CL" in categories  # Cross-Ledger
        assert "FM" in categories  # Financial Manipulation
        assert "LC" in categories  # Legal Compliance
        assert "OP" in categories  # Operational Risk


class TestLogicEvaluator:
    """Test logic schema evaluation."""

    def test_simple_comparison(self, logic_evaluator):
        """Test simple comparison evaluation."""
        schema = "资产负债率 > 0.7"
        data = {"资产负债率": 0.77}

        result = logic_evaluator.evaluate(schema, data)

        assert result["violation"] is True
        assert "资产负债率" in result["evidence"]

    def test_complex_expression(self, logic_evaluator):
        """Test complex expression with multiple operators."""
        schema = "(货币资金 / (短期借款 + 一年内到期的非流动负债)) < 0.5"
        data = {
            "货币资金": 50000000,
            "短期借款": 200000000,
            "一年内到期的非流动负债": 150000000
        }

        result = logic_evaluator.evaluate(schema, data)

        # 50M / 350M = 0.143 < 0.5 -> violation
        assert result["violation"] is True

    def test_and_condition(self, logic_evaluator):
        """Test AND logical operator."""
        schema = "(营业收入_贸易业务占比 > 0.3) AND (销售毛利率_贸易业务 < 0.02)"
        data = {
            "营业收入_贸易业务占比": 0.4,
            "销售毛利率_贸易业务": 0.015
        }

        result = logic_evaluator.evaluate(schema, data)

        assert result["violation"] is True

    def test_missing_data_handling(self, logic_evaluator):
        """Test handling of missing data fields."""
        schema = "不存在的字段 > 100"
        data = {"其他字段": 50}

        result = logic_evaluator.evaluate(schema, data)

        assert result["violation"] is False
        assert "error" in result or "missing_fields" in result

    def test_abs_function(self, logic_evaluator):
        """Test abs() function evaluation."""
        schema = "abs(现金流量表_补充资料_存货的减少 - (资产负债表_存货_期初余额 - 资产负债表_存货_期末余额)) > 1000000"
        data = {
            "现金流量表_补充资料_存货的减少": -15000000,
            "资产负债表_存货_期初余额": 480000000,
            "资产负债表_存货_期末余额": 500000000
        }

        result = logic_evaluator.evaluate(schema, data)

        # abs(-15M - (-20M)) = abs(5M) = 5M > 1M -> violation
        assert result["violation"] is True


class TestRuleRetrieval:
    """Test RAG-based rule retrieval."""

    def test_retrieve_by_keywords(self, rule_retriever):
        """Test keyword-based retrieval."""
        rule_retriever.load_rules_to_cache()

        results = rule_retriever.retrieve_by_keywords(
            ["政府补助", "营业外收入"]
        )

        assert len(results) > 0
        # CL-001 should be in results (matches these keywords)
        rule_ids = [r.rule_id for r, _ in results]
        assert "CL-001" in rule_ids

    def test_retrieve_by_category(self, rule_retriever):
        """Test category filtering."""
        rule_retriever.load_rules_to_cache()

        cl_rules = rule_retriever.retrieve_by_category("CL")
        fm_rules = rule_retriever.retrieve_by_category("FM")

        assert len(cl_rules) > 0
        assert len(fm_rules) > 0
        assert all(r.category == "CL" for r in cl_rules)
        assert all(r.category == "FM" for r in fm_rules)

    def test_retrieve_critical_rules(self, rule_retriever):
        """Test critical priority filtering."""
        rule_retriever.load_rules_to_cache()

        critical_rules = rule_retriever.retrieve_critical_rules()

        assert len(critical_rules) > 0
        assert all(r.priority == "Critical" for r in critical_rules)


class TestAuditReport:
    """Test audit report generation."""

    def test_create_report(self):
        """Test report creation from findings."""
        findings = [
            Finding(
                rule_id="CL-001",
                rule_subject="政府补助真实性",
                category="CL",
                severity=ViolationSeverity.HIGH,
                logic_schema="test > 0",
                evaluation_result=True,
                description="Test description"
            ),
            Finding(
                rule_id="FM-001",
                rule_subject="融资性贸易识别",
                category="FM",
                severity=ViolationSeverity.CRITICAL,
                logic_schema="test > 0",
                evaluation_result=True,
                description="Test description"
            )
        ]

        reporter = AuditReporter()
        report = reporter.create_report(
            document_name="test.pdf",
            document_path="/path/to/test.pdf",
            findings=findings,
            total_rules_checked=10
        )

        assert report.total_violations == 2
        assert report.critical_count == 1
        assert report.high_count == 1
        assert "CL" in report.category_summary
        assert "FM" in report.category_summary

    def test_markdown_generation(self):
        """Test markdown report generation."""
        findings = [
            Finding(
                rule_id="CL-001",
                rule_subject="测试规则",
                category="CL",
                severity=ViolationSeverity.HIGH,
                logic_schema="test > 0",
                evaluation_result=True,
                description="测试描述"
            )
        ]

        reporter = AuditReporter()
        report = reporter.create_report(
            document_name="test.pdf",
            document_path="/path/to/test.pdf",
            findings=findings,
            total_rules_checked=5
        )

        markdown = report.to_markdown()

        assert "# EagleEye Lite 审计报告" in markdown
        assert "CL-001" in markdown
        assert "测试规则" in markdown


class TestIntegration:
    """Integration tests with mock data."""

    def test_violation_detection(self, violation_data, rule_retriever, logic_evaluator):
        """Test that expected violations are detected."""
        rule_retriever.load_rules_to_cache()
        all_rules = rule_retriever.retrieve_all_rules()

        detected_violations = []

        for rule in all_rules:
            result = logic_evaluator.evaluate(rule.logic_schema, violation_data)
            if result["violation"]:
                detected_violations.append(rule.rule_id)

        # Check for expected violations (based on mock data)
        # OP-004 should definitely trigger (cash ratio < 0.5)
        assert "OP-004" in detected_violations, "OP-004 (cash coverage) should be detected"

    def test_clean_data_no_violations(self, clean_data, rule_retriever, logic_evaluator):
        """Test that clean data produces fewer violations."""
        rule_retriever.load_rules_to_cache()
        all_rules = rule_retriever.retrieve_all_rules()

        violation_count = 0

        for rule in all_rules:
            result = logic_evaluator.evaluate(rule.logic_schema, clean_data)
            if result["violation"]:
                violation_count += 1

        # Clean data should have significantly fewer violations
        # (some rules may still trigger based on thresholds)
        assert violation_count < 10, f"Clean data should have few violations, got {violation_count}"


class TestFinancialDataModel:
    """Test FinancialData model."""

    def test_from_dict(self, violation_data):
        """Test creating FinancialData from dict."""
        financial = FinancialData(**{
            k.replace("_", "_"): v
            for k, v in violation_data.items()
            if hasattr(FinancialData, k.replace("_", "_"))
        })

        assert financial.货币资金 == 50000000
        assert financial.资产负债率 == 0.77

    def test_to_eval_dict(self):
        """Test converting to evaluation dict."""
        financial = FinancialData(
            货币资金=100000,
            短期借款=200000
        )

        eval_dict = financial.to_eval_dict()

        assert "货币资金" in eval_dict
        assert eval_dict["货币资金"] == 100000


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

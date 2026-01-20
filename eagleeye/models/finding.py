"""
Finding data models for audit results.
"""

from typing import Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class ViolationSeverity(str, Enum):
    """Severity levels for violations."""
    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class Finding(BaseModel):
    """Represents a single audit finding/violation."""

    rule_id: str = Field(..., description="Rule that was violated")
    rule_subject: str = Field(..., description="Rule subject/title")
    category: str = Field(..., description="Rule category")
    severity: ViolationSeverity = Field(..., description="Finding severity")

    logic_schema: str = Field(..., description="Logic expression that was evaluated")
    evaluation_result: bool = Field(..., description="True if violation detected")

    evidence: dict[str, Any] = Field(default_factory=dict, description="Financial data used in evaluation")
    calculated_value: Optional[float] = Field(None, description="Calculated value from logic schema")
    threshold_value: Optional[float] = Field(None, description="Threshold that was exceeded")

    description: str = Field(..., description="Rule description")
    recommendation: str = Field(default="", description="Audit recommendation")
    audit_procedures: list[str] = Field(default_factory=list, description="Recommended audit procedures")

    detected_at: datetime = Field(default_factory=datetime.now)

    def to_markdown(self) -> str:
        """Generate markdown summary of finding."""
        severity_emoji = {
            ViolationSeverity.CRITICAL: "🔴",
            ViolationSeverity.HIGH: "🟠",
            ViolationSeverity.MEDIUM: "🟡",
            ViolationSeverity.LOW: "🟢"
        }

        lines = [
            f"### {severity_emoji.get(self.severity, '⚪')} {self.rule_id}: {self.rule_subject}",
            "",
            f"**严重程度**: {self.severity.value}",
            f"**类别**: {self.category}",
            "",
            f"**描述**: {self.description}",
            "",
            "**检测逻辑**:",
            f"```",
            f"{self.logic_schema}",
            f"```",
            "",
        ]

        if self.evidence:
            lines.append("**相关数据**:")
            for key, value in self.evidence.items():
                if isinstance(value, float):
                    lines.append(f"- {key}: {value:,.2f}")
                else:
                    lines.append(f"- {key}: {value}")
            lines.append("")

        if self.audit_procedures:
            lines.append("**建议审计程序**:")
            for i, proc in enumerate(self.audit_procedures, 1):
                lines.append(f"{i}. {proc}")
            lines.append("")

        return "\n".join(lines)


class AuditReport(BaseModel):
    """Complete audit report for a document."""

    document_name: str
    document_path: str
    audit_timestamp: datetime = Field(default_factory=datetime.now)

    total_rules_checked: int = 0
    total_violations: int = 0

    findings: list[Finding] = Field(default_factory=list)

    # Summary by severity
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0

    # Summary by category
    category_summary: dict[str, int] = Field(default_factory=dict)

    execution_time_seconds: float = 0.0

    def add_finding(self, finding: Finding):
        """Add a finding and update counts."""
        self.findings.append(finding)
        self.total_violations += 1

        # Update severity counts
        if finding.severity == ViolationSeverity.CRITICAL:
            self.critical_count += 1
        elif finding.severity == ViolationSeverity.HIGH:
            self.high_count += 1
        elif finding.severity == ViolationSeverity.MEDIUM:
            self.medium_count += 1
        else:
            self.low_count += 1

        # Update category summary
        self.category_summary[finding.category] = self.category_summary.get(finding.category, 0) + 1

    def to_markdown(self) -> str:
        """Generate full markdown report."""
        lines = [
            "# EagleEye Lite 审计报告",
            "",
            f"**文档**: {self.document_name}",
            f"**审计时间**: {self.audit_timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
            f"**执行耗时**: {self.execution_time_seconds:.2f}秒",
            "",
            "---",
            "",
            "## 摘要",
            "",
            f"- 检查规则数: {self.total_rules_checked}",
            f"- 发现违规数: {self.total_violations}",
            "",
            "### 按严重程度分布",
            "",
            f"| 严重程度 | 数量 |",
            f"|---------|------|",
            f"| 🔴 Critical | {self.critical_count} |",
            f"| 🟠 High | {self.high_count} |",
            f"| 🟡 Medium | {self.medium_count} |",
            f"| 🟢 Low | {self.low_count} |",
            "",
        ]

        if self.category_summary:
            lines.extend([
                "### 按类别分布",
                "",
                "| 类别 | 数量 |",
                "|------|------|",
            ])
            category_names = {
                "CL": "交叉勾稽 (Cross-Ledger)",
                "FM": "财务造假 (Financial Manipulation)",
                "LC": "合规监管 (Legal Compliance)",
                "OP": "经营风险 (Operational Risk)"
            }
            for cat, count in sorted(self.category_summary.items()):
                cat_name = category_names.get(cat, cat)
                lines.append(f"| {cat_name} | {count} |")
            lines.append("")

        lines.extend([
            "---",
            "",
            "## 详细发现",
            "",
        ])

        # Group findings by severity
        severity_order = [
            ViolationSeverity.CRITICAL,
            ViolationSeverity.HIGH,
            ViolationSeverity.MEDIUM,
            ViolationSeverity.LOW
        ]

        for severity in severity_order:
            severity_findings = [f for f in self.findings if f.severity == severity]
            if severity_findings:
                lines.append(f"## {severity.value} 级别发现 ({len(severity_findings)})")
                lines.append("")
                for finding in severity_findings:
                    lines.append(finding.to_markdown())
                    lines.append("---")
                    lines.append("")

        if not self.findings:
            lines.append("*未发现违规项*")

        return "\n".join(lines)

    def to_json(self) -> dict:
        """Export report as JSON-serializable dict."""
        return {
            "document_name": self.document_name,
            "document_path": self.document_path,
            "audit_timestamp": self.audit_timestamp.isoformat(),
            "summary": {
                "total_rules_checked": self.total_rules_checked,
                "total_violations": self.total_violations,
                "by_severity": {
                    "critical": self.critical_count,
                    "high": self.high_count,
                    "medium": self.medium_count,
                    "low": self.low_count
                },
                "by_category": self.category_summary
            },
            "findings": [f.model_dump() for f in self.findings],
            "execution_time_seconds": self.execution_time_seconds
        }

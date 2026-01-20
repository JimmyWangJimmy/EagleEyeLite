"""
Audit Reporter - Generate audit reports in various formats.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional
from loguru import logger

import sys
sys.path.insert(0, str(__file__).rsplit("\\", 3)[0])

from config.settings import settings
from eagleeye.models.finding import Finding, AuditReport, ViolationSeverity


class AuditReporter:
    """
    Generates audit reports from findings.
    Supports Markdown and JSON output formats.
    """

    def __init__(self, output_dir: str | Path = None):
        """
        Initialize reporter.

        Args:
            output_dir: Directory for saving reports
        """
        self.output_dir = Path(output_dir) if output_dir else settings.output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def create_report(
        self,
        document_name: str,
        document_path: str,
        findings: list[Finding],
        total_rules_checked: int,
        execution_time: float = 0.0
    ) -> AuditReport:
        """
        Create an audit report from findings.

        Args:
            document_name: Name of audited document
            document_path: Path to audited document
            findings: List of audit findings
            total_rules_checked: Number of rules evaluated
            execution_time: Execution time in seconds

        Returns:
            AuditReport object
        """
        report = AuditReport(
            document_name=document_name,
            document_path=document_path,
            total_rules_checked=total_rules_checked,
            execution_time_seconds=execution_time
        )

        # Add each finding
        for finding in findings:
            report.add_finding(finding)

        return report

    def save_markdown(
        self,
        report: AuditReport,
        filename: str = None
    ) -> Path:
        """
        Save report as Markdown file.

        Args:
            report: AuditReport to save
            filename: Optional custom filename

        Returns:
            Path to saved file
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            doc_name = Path(report.document_name).stem
            filename = f"audit_report_{doc_name}_{timestamp}.md"

        output_path = self.output_dir / filename
        markdown_content = report.to_markdown()

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(markdown_content)

        logger.info(f"Markdown report saved: {output_path}")
        return output_path

    def save_json(
        self,
        report: AuditReport,
        filename: str = None
    ) -> Path:
        """
        Save report as JSON file.

        Args:
            report: AuditReport to save
            filename: Optional custom filename

        Returns:
            Path to saved file
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            doc_name = Path(report.document_name).stem
            filename = f"audit_report_{doc_name}_{timestamp}.json"

        output_path = self.output_dir / filename
        json_content = report.to_json()

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(json_content, f, ensure_ascii=False, indent=2, default=str)

        logger.info(f"JSON report saved: {output_path}")
        return output_path

    def save_both(
        self,
        report: AuditReport,
        base_filename: str = None
    ) -> tuple[Path, Path]:
        """
        Save report in both Markdown and JSON formats.

        Args:
            report: AuditReport to save
            base_filename: Base filename (without extension)

        Returns:
            Tuple of (markdown_path, json_path)
        """
        if base_filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            doc_name = Path(report.document_name).stem
            base_filename = f"audit_report_{doc_name}_{timestamp}"

        md_path = self.save_markdown(report, f"{base_filename}.md")
        json_path = self.save_json(report, f"{base_filename}.json")

        return md_path, json_path

    def generate_summary(self, report: AuditReport) -> str:
        """
        Generate a brief text summary of the report.

        Args:
            report: AuditReport to summarize

        Returns:
            Summary text string
        """
        lines = [
            f"审计摘要 - {report.document_name}",
            "=" * 50,
            f"检查规则数: {report.total_rules_checked}",
            f"发现违规数: {report.total_violations}",
            "",
            "按严重程度:",
            f"  - Critical: {report.critical_count}",
            f"  - High: {report.high_count}",
            f"  - Medium: {report.medium_count}",
            f"  - Low: {report.low_count}",
            "",
        ]

        if report.category_summary:
            lines.append("按类别:")
            for cat, count in sorted(report.category_summary.items()):
                lines.append(f"  - {cat}: {count}")

        if report.findings:
            lines.extend([
                "",
                "主要发现:",
            ])
            # Show top 5 critical/high findings
            top_findings = [
                f for f in report.findings
                if f.severity in [ViolationSeverity.CRITICAL, ViolationSeverity.HIGH]
            ][:5]
            for finding in top_findings:
                lines.append(f"  • [{finding.rule_id}] {finding.rule_subject}")

        return "\n".join(lines)

    def generate_executive_summary(self, report: AuditReport) -> str:
        """
        Generate an executive summary suitable for management.

        Args:
            report: AuditReport to summarize

        Returns:
            Executive summary markdown
        """
        # Calculate risk score
        risk_score = (
            report.critical_count * 10 +
            report.high_count * 5 +
            report.medium_count * 2 +
            report.low_count * 1
        )

        if risk_score == 0:
            risk_level = "低"
            risk_color = "🟢"
        elif risk_score < 20:
            risk_level = "中"
            risk_color = "🟡"
        elif risk_score < 50:
            risk_level = "高"
            risk_color = "🟠"
        else:
            risk_level = "极高"
            risk_color = "🔴"

        lines = [
            "# 执行摘要",
            "",
            f"**审计对象**: {report.document_name}",
            f"**审计日期**: {report.audit_timestamp.strftime('%Y年%m月%d日')}",
            "",
            f"## 风险评级: {risk_color} {risk_level}",
            "",
            f"本次审计共检查 **{report.total_rules_checked}** 条规则，发现 **{report.total_violations}** 项违规。",
            "",
        ]

        if report.critical_count > 0:
            lines.extend([
                "### ⚠️ 紧急关注事项",
                "",
            ])
            critical_findings = [
                f for f in report.findings
                if f.severity == ViolationSeverity.CRITICAL
            ]
            for finding in critical_findings[:3]:
                lines.append(f"- **{finding.rule_id}**: {finding.rule_subject}")
            lines.append("")

        if report.high_count > 0:
            lines.extend([
                "### 高风险事项",
                "",
            ])
            high_findings = [
                f for f in report.findings
                if f.severity == ViolationSeverity.HIGH
            ]
            for finding in high_findings[:3]:
                lines.append(f"- **{finding.rule_id}**: {finding.rule_subject}")
            lines.append("")

        lines.extend([
            "### 建议措施",
            "",
            "1. 立即审查所有Critical级别发现",
            "2. 制定High级别问题整改计划",
            "3. 定期复核Medium/Low级别风险点",
            "",
            "---",
            f"*报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*",
        ])

        return "\n".join(lines)

    def compare_reports(
        self,
        current: AuditReport,
        previous: AuditReport
    ) -> str:
        """
        Generate comparison between two audit reports.

        Args:
            current: Current audit report
            previous: Previous audit report

        Returns:
            Comparison summary markdown
        """
        lines = [
            "# 审计对比报告",
            "",
            f"**当前审计**: {current.audit_timestamp.strftime('%Y-%m-%d')}",
            f"**对比审计**: {previous.audit_timestamp.strftime('%Y-%m-%d')}",
            "",
            "## 变化概览",
            "",
            "| 指标 | 当前 | 之前 | 变化 |",
            "|------|------|------|------|",
        ]

        # Compare metrics
        metrics = [
            ("总违规数", current.total_violations, previous.total_violations),
            ("Critical", current.critical_count, previous.critical_count),
            ("High", current.high_count, previous.high_count),
            ("Medium", current.medium_count, previous.medium_count),
        ]

        for name, curr, prev in metrics:
            diff = curr - prev
            diff_str = f"+{diff}" if diff > 0 else str(diff)
            emoji = "📈" if diff > 0 else ("📉" if diff < 0 else "➡️")
            lines.append(f"| {name} | {curr} | {prev} | {emoji} {diff_str} |")

        # New findings
        current_rule_ids = {f.rule_id for f in current.findings}
        previous_rule_ids = {f.rule_id for f in previous.findings}

        new_violations = current_rule_ids - previous_rule_ids
        resolved = previous_rule_ids - current_rule_ids

        if new_violations:
            lines.extend([
                "",
                "## 新增违规",
                "",
            ])
            for finding in current.findings:
                if finding.rule_id in new_violations:
                    lines.append(f"- [{finding.rule_id}] {finding.rule_subject}")

        if resolved:
            lines.extend([
                "",
                "## 已解决问题",
                "",
            ])
            for finding in previous.findings:
                if finding.rule_id in resolved:
                    lines.append(f"- ✅ [{finding.rule_id}] {finding.rule_subject}")

        return "\n".join(lines)

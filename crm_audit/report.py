"""Audit report generation and formatting."""

import html as html_lib
from datetime import datetime


class AuditReport:
    """Container for CRM audit results with formatting and export capabilities."""

    def __init__(self, results: dict, deals_count: int, total_pipeline: float,
                 period_start: str = None, period_end: str = None):
        self.results = results
        self.deals_count = deals_count
        self.total_pipeline = total_pipeline
        self.period_start = period_start or "N/A"
        self.period_end = period_end or datetime.now().strftime("%Y-%m-%d")
        self.generated_at = datetime.now()

    def print_summary(self):
        """Print a formatted text summary of the audit."""
        print(self._build_text_summary())

    def _build_text_summary(self) -> str:
        lines = [
            "=" * 43,
            "         CRM AUDIT REPORT SUMMARY",
            "=" * 43,
            "",
            f"Period: {self.period_start} to {self.period_end}",
            f"Total Deals Analyzed: {self.deals_count:,}",
            f"Total Pipeline Value: ${self.total_pipeline:,.0f}",
        ]

        if "dead_deals" in self.results:
            dd = self.results["dead_deals"]
            lines += [
                "",
                f"--- DEAD DEALS {'─' * 28}",
                f"Dead deals found: {dd['count']} ({dd['pct']:.1f}% of pipeline)",
                f"Revenue at risk: ${dd['revenue_at_risk']:,.0f}",
            ]

        if "speed_to_lead" in self.results:
            stl = self.results["speed_to_lead"]
            lines += [
                "",
                f"--- SPEED TO LEAD {'─' * 25}",
                f"Average response time: {stl['avg_hours']:.1f} hours",
            ]
            if stl.get("best_rep"):
                lines.append(f"Best rep: {stl['best_rep']} ({stl['best_hours']:.1f} hours avg)")
            if stl.get("worst_rep"):
                lines.append(f"Needs improvement: {stl['worst_rep']} ({stl['worst_hours']:.1f} hours avg)")

        if "funnel" in self.results:
            f = self.results["funnel"]
            lines += [
                "",
                f"--- FUNNEL BOTTLENECK {'─' * 22}",
            ]
            if f.get("biggest_dropoff"):
                lines.append(f"Biggest drop-off: {f['biggest_dropoff']}")

        if "data_quality" in self.results:
            dq = self.results["data_quality"]
            lines += [
                "",
                f"--- DATA QUALITY {'─' * 26}",
                f"Overall score: {dq['score']}/100",
            ]
            for issue in dq.get("top_issues", []):
                lines.append(f"  - {issue}")

        lines += ["", "=" * 43]
        return "\n".join(lines)

    def to_html(self, output_path: str):
        """Export audit report as an HTML file."""
        summary_text = html_lib.escape(self._build_text_summary())
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>CRM Audit Report</title>
    <style>
        body {{ font-family: monospace; padding: 2em; background: #f9f9f9; }}
        pre {{ background: #fff; padding: 2em; border: 1px solid #ddd; border-radius: 4px; }}
        h1 {{ color: #333; }}
        .meta {{ color: #666; font-size: 0.9em; }}
    </style>
</head>
<body>
    <h1>CRM Audit Report</h1>
    <p class="meta">Generated: {self.generated_at.strftime("%Y-%m-%d %H:%M")}</p>
    <pre>{summary_text}</pre>
</body>
</html>"""
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)

    def to_dict(self) -> dict:
        """Return the full results as a dictionary."""
        return {
            "meta": {
                "deals_count": self.deals_count,
                "total_pipeline": self.total_pipeline,
                "period_start": self.period_start,
                "period_end": self.period_end,
                "generated_at": self.generated_at.isoformat(),
            },
            "results": self.results,
        }

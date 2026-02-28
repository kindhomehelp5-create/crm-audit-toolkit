"""CRM Audit Toolkit — analyze CRM data and find revenue leaks."""

import pandas as pd
import yaml

from .report import AuditReport
from .modules.dead_deal_finder import DeadDealFinder
from .modules.speed_to_lead import SpeedToLead
from .modules.funnel_analyzer import FunnelAnalyzer
from .modules.rep_performance import RepPerformance
from .modules.data_quality import DataQuality

__version__ = "0.1.0"


class CRMAudit:
    """Main entry point for running CRM audits.

    Usage:
        audit = CRMAudit("deals_export.csv")
        report = audit.run_full_audit()
        report.print_summary()
    """

    def __init__(self, deals_path: str, activities_path: str = None,
                 contacts_path: str = None, config_path: str = None):
        """Initialize CRM audit with data files.

        Args:
            deals_path: Path to deals CSV file.
            activities_path: Optional path to activities CSV.
            contacts_path: Optional path to contacts CSV.
            config_path: Optional path to config.yaml for column mappings.
        """
        self.config = self._load_config(config_path) if config_path else {}
        col_map = self.config.get("columns", {})

        self.deals = pd.read_csv(deals_path)
        if col_map:
            reverse_map = {v: k for k, v in col_map.items()}
            self.deals = self.deals.rename(columns=reverse_map)

        self.activities = pd.read_csv(activities_path) if activities_path else None
        self.contacts = pd.read_csv(contacts_path) if contacts_path else None

    @staticmethod
    def _load_config(path: str) -> dict:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    def run_full_audit(self, stale_threshold_days: int = None,
                       stages: list = None) -> AuditReport:
        """Run all audit modules and return a consolidated report.

        Args:
            stale_threshold_days: Override for dead deal threshold.
            stages: Override for funnel stages.

        Returns:
            AuditReport with all results.
        """
        thresholds = self.config.get("thresholds", {})
        stale_days = stale_threshold_days or thresholds.get("stale_deal_days", 30)
        stages = stages or self.config.get("stages")

        results = {}

        # Dead Deals
        dd = DeadDealFinder(self.deals)
        results["dead_deals"] = dd.summary(stale_threshold_days=stale_days)

        # Speed to Lead
        try:
            stl = SpeedToLead(self.deals, self.activities)
            stl_results = stl.analyze()
            results["speed_to_lead"] = stl_results.summary()
        except (ValueError, KeyError):
            pass

        # Funnel Analysis
        try:
            funnel = FunnelAnalyzer(self.deals)
            funnel_results = funnel.analyze(stages=stages)
            results["funnel"] = funnel_results.summary()
        except (ValueError, KeyError):
            pass

        # Rep Performance
        try:
            perf = RepPerformance(self.deals, self.activities)
            perf_results = perf.compare()
            results["rep_performance"] = perf_results.to_dict()
        except (ValueError, KeyError):
            pass

        # Data Quality
        dq = DataQuality(self.deals, self.contacts)
        dq_result = dq.check(
            required_fields=["email", "company", "phone"] if self.contacts is not None else [],
            check_duplicates=True,
            check_formatting=True,
        )
        results["data_quality"] = dq_result.summary()

        # Build report
        total_pipeline = self.deals["amount"].sum() if "amount" in self.deals.columns else 0
        period_start = None
        if "created_at" in self.deals.columns:
            period_start = pd.to_datetime(self.deals["created_at"]).min().strftime("%Y-%m-%d")

        return AuditReport(
            results=results,
            deals_count=len(self.deals),
            total_pipeline=total_pipeline,
            period_start=period_start,
        )

"""Dead Deal Finder — identifies stale opportunities with no recent activity."""

import pandas as pd
from datetime import datetime, timedelta


class DeadDealFinder:
    """Finds deals that have gone stale based on last activity date."""

    def __init__(self, deals_df: pd.DataFrame, updated_col: str = "updated_at",
                 amount_col: str = "amount", status_col: str = "status"):
        self.deals = deals_df.copy()
        self.updated_col = updated_col
        self.amount_col = amount_col
        self.status_col = status_col
        self.deals[self.updated_col] = pd.to_datetime(self.deals[self.updated_col])

    def find(self, stale_threshold_days: int = 30, min_amount: float = 0,
             reference_date: datetime = None) -> pd.DataFrame:
        """Find dead deals that have not been updated within the threshold.

        Args:
            stale_threshold_days: Number of days without activity to consider a deal dead.
            min_amount: Minimum deal value to include.
            reference_date: Date to measure staleness from (defaults to now).

        Returns:
            DataFrame of dead deals.
        """
        ref = reference_date or datetime.now()
        cutoff = ref - timedelta(days=stale_threshold_days)

        mask = (
            (self.deals[self.updated_col] < cutoff)
            & (self.deals[self.amount_col] >= min_amount)
        )

        # Only consider open deals
        if self.status_col in self.deals.columns:
            mask = mask & (~self.deals[self.status_col].str.lower().isin(["won", "lost", "closed won", "closed lost"]))

        dead = self.deals[mask].copy()
        dead["days_stale"] = (ref - dead[self.updated_col]).dt.days
        return dead.sort_values("days_stale", ascending=False)

    def summary(self, stale_threshold_days: int = 30, min_amount: float = 0) -> dict:
        """Return a summary dict for the audit report."""
        dead = self.find(stale_threshold_days=stale_threshold_days, min_amount=min_amount)
        total_open = self.deals[
            ~self.deals[self.status_col].str.lower().isin(["won", "lost", "closed won", "closed lost"])
        ] if self.status_col in self.deals.columns else self.deals

        count = len(dead)
        pct = (count / len(total_open) * 100) if len(total_open) > 0 else 0
        revenue = dead[self.amount_col].sum() if count > 0 else 0

        return {
            "count": count,
            "pct": pct,
            "revenue_at_risk": revenue,
            "avg_days_stale": dead["days_stale"].mean() if count > 0 else 0,
        }

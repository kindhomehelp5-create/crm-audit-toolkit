"""Rep Performance Comparison — compares key metrics across sales reps."""

import pandas as pd
import numpy as np


class RepPerformance:
    """Compares sales rep metrics to identify coaching opportunities."""

    def __init__(self, deals_df: pd.DataFrame, activities_df: pd.DataFrame = None,
                 owner_col: str = "owner", amount_col: str = "amount",
                 status_col: str = "status", created_col: str = "created_at",
                 closed_col: str = "closed_at"):
        self.deals = deals_df.copy()
        self.activities = activities_df
        self.owner_col = owner_col
        self.amount_col = amount_col
        self.status_col = status_col
        self.created_col = created_col
        self.closed_col = closed_col

        for col in [self.created_col, self.closed_col]:
            if col in self.deals.columns:
                self.deals[col] = pd.to_datetime(self.deals[col], errors="coerce")

    def compare(self, metrics: list = None, normalize_by: str = None) -> "RepComparisonResults":
        """Compare reps across specified metrics.

        Args:
            metrics: List of metric names. Supported: 'conversion_rate', 'avg_deal_size',
                     'cycle_time', 'activity_count', 'total_revenue'.
            normalize_by: Column to normalize by (e.g., 'lead_quality') for fairer comparison.

        Returns:
            RepComparisonResults object.
        """
        metrics = metrics or ["conversion_rate", "avg_deal_size", "cycle_time", "total_revenue"]
        reps = self.deals[self.owner_col].unique()
        rows = []

        for rep in reps:
            rep_deals = self.deals[self.deals[self.owner_col] == rep]
            row = {"rep": rep, "total_deals": len(rep_deals)}

            if "conversion_rate" in metrics and self.status_col in rep_deals.columns:
                won = rep_deals[self.status_col].str.lower().isin(["won", "closed won"]).sum()
                closed = rep_deals[self.status_col].str.lower().isin(
                    ["won", "lost", "closed won", "closed lost"]
                ).sum()
                row["conversion_rate"] = (won / closed * 100) if closed > 0 else 0

            if "avg_deal_size" in metrics and self.amount_col in rep_deals.columns:
                won_deals = rep_deals[rep_deals[self.status_col].str.lower().isin(["won", "closed won"])]
                row["avg_deal_size"] = won_deals[self.amount_col].mean() if len(won_deals) > 0 else 0

            if "total_revenue" in metrics and self.amount_col in rep_deals.columns:
                won_deals = rep_deals[rep_deals[self.status_col].str.lower().isin(["won", "closed won"])]
                row["total_revenue"] = won_deals[self.amount_col].sum()

            if "cycle_time" in metrics and self.closed_col in rep_deals.columns:
                closed_deals = rep_deals.dropna(subset=[self.closed_col])
                if len(closed_deals) > 0:
                    cycle = (closed_deals[self.closed_col] - closed_deals[self.created_col]).dt.days
                    row["avg_cycle_days"] = cycle.mean()
                else:
                    row["avg_cycle_days"] = np.nan

            if "activity_count" in metrics and self.activities is not None:
                rep_activities = self.activities[
                    self.activities.get("deal_id", pd.Series()).isin(rep_deals.get("deal_id", []))
                ] if "deal_id" in self.activities.columns else pd.DataFrame()
                row["activity_count"] = len(rep_activities)

            rows.append(row)

        return RepComparisonResults(pd.DataFrame(rows))


class RepComparisonResults:
    """Results container for rep comparison."""

    def __init__(self, data: pd.DataFrame):
        self.data = data

    def summary(self) -> pd.DataFrame:
        """Full comparison table sorted by conversion rate."""
        sort_col = "conversion_rate" if "conversion_rate" in self.data.columns else "total_deals"
        return self.data.sort_values(sort_col, ascending=False)

    def coaching_recommendations(self) -> list:
        """Generate simple coaching recommendations based on metrics."""
        recs = []
        if "conversion_rate" in self.data.columns and len(self.data) > 1:
            avg_rate = self.data["conversion_rate"].mean()
            below = self.data[self.data["conversion_rate"] < avg_rate * 0.8]
            for _, rep in below.iterrows():
                recs.append(
                    f"{rep['rep']}: conversion rate ({rep['conversion_rate']:.1f}%) is "
                    f"significantly below team average ({avg_rate:.1f}%). "
                    f"Review deal qualification process."
                )

        if "avg_cycle_days" in self.data.columns and len(self.data) > 1:
            avg_cycle = self.data["avg_cycle_days"].mean()
            slow = self.data[self.data["avg_cycle_days"] > avg_cycle * 1.3]
            for _, rep in slow.dropna(subset=["avg_cycle_days"]).iterrows():
                recs.append(
                    f"{rep['rep']}: avg cycle time ({rep['avg_cycle_days']:.0f} days) is "
                    f"above team average ({avg_cycle:.0f} days). "
                    f"Check for stalled deals or slow follow-up."
                )

        return recs if recs else ["All reps are performing within expected ranges."]

    def to_dict(self) -> dict:
        return {
            "comparison": self.data.to_dict("records"),
            "recommendations": self.coaching_recommendations(),
        }

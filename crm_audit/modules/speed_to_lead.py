"""Speed-to-Lead Analyzer — measures response time to new leads."""

import pandas as pd
import numpy as np


class SpeedToLead:
    """Measures how quickly sales reps respond to new leads."""

    def __init__(self, deals_df: pd.DataFrame, activities_df: pd.DataFrame = None,
                 created_col: str = "created_at", owner_col: str = "owner",
                 activity_time_col: str = "activity_time",
                 activity_deal_col: str = "deal_id"):
        self.deals = deals_df.copy()
        self.activities = activities_df.copy() if activities_df is not None else None
        self.created_col = created_col
        self.owner_col = owner_col
        self.activity_time_col = activity_time_col
        self.activity_deal_col = activity_deal_col

        self.deals[self.created_col] = pd.to_datetime(self.deals[self.created_col])

    def analyze(self, business_hours_only: bool = False,
                exclude_weekends: bool = False) -> "SpeedToLeadResults":
        """Analyze speed-to-lead metrics.

        Args:
            business_hours_only: Only count business hours (9-17).
            exclude_weekends: Exclude weekend hours from calculations.

        Returns:
            SpeedToLeadResults object.
        """
        if self.activities is None:
            # Fall back to using updated_at - created_at as proxy
            if "updated_at" in self.deals.columns:
                self.deals["_first_response"] = pd.to_datetime(self.deals["updated_at"])
            else:
                raise ValueError("No activities DataFrame and no 'updated_at' column to use as proxy.")
        else:
            self.activities[self.activity_time_col] = pd.to_datetime(
                self.activities[self.activity_time_col]
            )
            first_activity = (
                self.activities
                .sort_values(self.activity_time_col)
                .groupby(self.activity_deal_col)
                .first()[[self.activity_time_col]]
                .rename(columns={self.activity_time_col: "_first_response"})
            )
            self.deals = self.deals.merge(
                first_activity, left_on="deal_id", right_index=True, how="left"
            )

        delta = self.deals["_first_response"] - self.deals[self.created_col]
        hours = delta.dt.total_seconds() / 3600

        if exclude_weekends:
            # Approximate: remove 48h per full week in the delta
            weeks = delta.dt.days // 7
            hours = hours - (weeks * 48)

        if business_hours_only:
            # Approximate: keep only 8h per business day
            hours = hours * (8 / 24)

        self.deals["response_hours"] = hours.clip(lower=0)

        return SpeedToLeadResults(self.deals, self.owner_col)


class SpeedToLeadResults:
    """Results container for speed-to-lead analysis."""

    def __init__(self, deals: pd.DataFrame, owner_col: str):
        self.deals = deals
        self.owner_col = owner_col

    def by_rep(self) -> pd.DataFrame:
        """Average response time broken down by sales rep."""
        return (
            self.deals.groupby(self.owner_col)["response_hours"]
            .agg(["mean", "median", "count"])
            .rename(columns={"mean": "avg_hours", "median": "median_hours", "count": "deals"})
            .sort_values("avg_hours")
        )

    def conversion_correlation(self) -> float:
        """Correlation between response time and conversion (win) rate."""
        if "status" not in self.deals.columns:
            return np.nan
        df = self.deals.dropna(subset=["response_hours"])
        df = df.copy()
        df["is_won"] = df["status"].str.lower().isin(["won", "closed won"]).astype(int)
        if df["response_hours"].std() == 0 or df["is_won"].std() == 0:
            return 0.0
        return df["response_hours"].corr(df["is_won"])

    def summary(self) -> dict:
        """Summary dict for the audit report."""
        valid = self.deals.dropna(subset=["response_hours"])
        avg = valid["response_hours"].mean() if len(valid) > 0 else 0

        rep_stats = self.by_rep()
        best_rep = rep_stats.index[0] if len(rep_stats) > 0 else None
        best_hours = rep_stats.iloc[0]["avg_hours"] if len(rep_stats) > 0 else 0
        worst_rep = rep_stats.index[-1] if len(rep_stats) > 1 else None
        worst_hours = rep_stats.iloc[-1]["avg_hours"] if len(rep_stats) > 1 else 0

        return {
            "avg_hours": avg,
            "best_rep": best_rep,
            "best_hours": best_hours,
            "worst_rep": worst_rep,
            "worst_hours": worst_hours,
        }

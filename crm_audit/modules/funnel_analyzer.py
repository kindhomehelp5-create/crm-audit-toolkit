"""Funnel Analysis — stage-by-stage conversion rates and bottleneck detection."""

import pandas as pd
from datetime import datetime


class FunnelAnalyzer:
    """Analyzes pipeline funnel conversion rates and identifies bottlenecks."""

    DEFAULT_STAGES = [
        "Lead", "Qualified", "Demo", "Proposal", "Negotiation", "Closed Won"
    ]

    def __init__(self, deals_df: pd.DataFrame, stage_col: str = "stage",
                 created_col: str = "created_at", status_col: str = "status"):
        self.deals = deals_df.copy()
        self.stage_col = stage_col
        self.created_col = created_col
        self.status_col = status_col
        self.deals[self.created_col] = pd.to_datetime(self.deals[self.created_col])

    def analyze(self, stages: list = None, period: str = None,
                start_date: str = None, end_date: str = None) -> "FunnelResults":
        """Analyze funnel conversion rates.

        Args:
            stages: Ordered list of pipeline stages. Defaults to common stages.
            period: Shorthand like 'last_6_months', 'last_year'.
            start_date: Filter deals created after this date.
            end_date: Filter deals created before this date.

        Returns:
            FunnelResults object.
        """
        stages = stages or self.DEFAULT_STAGES
        df = self.deals.copy()

        # Apply date filters
        if period:
            end = datetime.now()
            months = {"last_3_months": 3, "last_6_months": 6, "last_year": 12}.get(period, 6)
            start = end - pd.DateOffset(months=months)
            df = df[(df[self.created_col] >= start) & (df[self.created_col] <= end)]
        elif start_date or end_date:
            if start_date:
                df = df[df[self.created_col] >= pd.to_datetime(start_date)]
            if end_date:
                df = df[df[self.created_col] <= pd.to_datetime(end_date)]

        # Build stage index for each deal: the furthest stage it reached
        stage_order = {s: i for i, s in enumerate(stages)}
        df = df[df[self.stage_col].isin(stage_order)]

        # For won deals, they've passed through all stages up to Closed Won
        # For others, they reached their current stage
        if self.status_col in df.columns:
            won_mask = df[self.status_col].str.lower().isin(["won", "closed won"])
            max_stage_idx = stages.index(stages[-1]) if stages else 0
            df.loc[won_mask, "_stage_idx"] = max_stage_idx
            df.loc[~won_mask, "_stage_idx"] = df.loc[~won_mask, self.stage_col].map(stage_order)
        else:
            df["_stage_idx"] = df[self.stage_col].map(stage_order)

        # Count deals that reached each stage
        stage_counts = []
        for i, stage in enumerate(stages):
            count = (df["_stage_idx"] >= i).sum()
            stage_counts.append({"stage": stage, "count": int(count)})

        return FunnelResults(pd.DataFrame(stage_counts), stages)


class FunnelResults:
    """Results container for funnel analysis."""

    def __init__(self, stage_data: pd.DataFrame, stages: list):
        self.stage_data = stage_data
        self.stages = stages

    def conversion_rates(self) -> pd.DataFrame:
        """Stage-to-stage conversion rates."""
        df = self.stage_data.copy()
        df["conversion_pct"] = None
        for i in range(1, len(df)):
            prev = df.iloc[i - 1]["count"]
            if prev > 0:
                df.loc[df.index[i], "conversion_pct"] = round(
                    df.iloc[i]["count"] / prev * 100, 1
                )
        return df

    def bottlenecks(self, expected_min_conversion: float = 50.0) -> pd.DataFrame:
        """Identify stages with conversion below the expected minimum."""
        rates = self.conversion_rates()
        return rates[
            rates["conversion_pct"].notna()
            & (rates["conversion_pct"] < expected_min_conversion)
        ]

    def stage_duration(self) -> pd.DataFrame:
        """Placeholder for average time spent in each stage.

        Requires deal history/activity data to compute accurately.
        Returns the stage data with a note.
        """
        return self.stage_data.copy()

    def summary(self) -> dict:
        """Summary dict for the audit report."""
        rates = self.conversion_rates()
        bottleneck_rows = rates[rates["conversion_pct"].notna()].sort_values("conversion_pct")
        biggest = None
        if len(bottleneck_rows) > 0:
            worst_idx = bottleneck_rows.index[0]
            if worst_idx > 0:
                from_stage = rates.iloc[worst_idx - 1]["stage"]
                to_stage = rates.iloc[worst_idx]["stage"]
                loss = 100 - rates.iloc[worst_idx]["conversion_pct"]
                biggest = f"{from_stage} -> {to_stage} ({loss:.0f}% loss)"

        return {
            "biggest_dropoff": biggest,
            "conversion_rates": rates.to_dict("records"),
        }

"""Data Quality Check — scores CRM data quality and identifies hygiene issues."""

import pandas as pd


class DataQuality:
    """Checks CRM data quality and produces a hygiene score."""

    def __init__(self, deals_df: pd.DataFrame, contacts_df: pd.DataFrame = None):
        self.deals = deals_df.copy()
        self.contacts = contacts_df.copy() if contacts_df is not None else None

    def check(self, required_fields: list = None, check_duplicates: bool = True,
              check_formatting: bool = True) -> "DataQualityScore":
        """Run data quality checks.

        Args:
            required_fields: List of field names that should not be empty.
            check_duplicates: Whether to check for duplicate contacts/deals.
            check_formatting: Whether to check for common formatting issues.

        Returns:
            DataQualityScore object.
        """
        required_fields = required_fields or []
        issues = []
        penalties = 0

        # Check required fields on deals
        for field in required_fields:
            if field in self.deals.columns:
                missing = self.deals[field].isna().sum() + (self.deals[field] == "").sum()
                total = len(self.deals)
                if missing > 0:
                    pct = missing / total * 100
                    issues.append(f"Missing '{field}': {missing} records ({pct:.0f}%)")
                    penalties += min(pct / 2, 10)  # up to 10 points per field

        # Check required fields on contacts
        if self.contacts is not None:
            for field in required_fields:
                if field in self.contacts.columns:
                    missing = self.contacts[field].isna().sum() + (self.contacts[field] == "").sum()
                    total = len(self.contacts)
                    if missing > 0:
                        pct = missing / total * 100
                        issues.append(f"Missing '{field}' in contacts: {missing} ({pct:.0f}%)")
                        penalties += min(pct / 2, 10)

        # Check duplicates
        duplicate_count = 0
        if check_duplicates:
            if self.contacts is not None and "email" in self.contacts.columns:
                emails = self.contacts["email"].dropna()
                dupes = emails[emails.duplicated()].nunique()
                if dupes > 0:
                    duplicate_count = dupes
                    issues.append(f"Duplicate contacts (by email): {dupes} found")
                    penalties += min(dupes / 5, 15)

            if "deal_id" in self.deals.columns:
                deal_dupes = self.deals["deal_id"].duplicated().sum()
                if deal_dupes > 0:
                    issues.append(f"Duplicate deal IDs: {deal_dupes}")
                    penalties += min(deal_dupes, 10)

        # Check formatting
        empty_required = 0
        if check_formatting:
            if "email" in (self.contacts.columns if self.contacts is not None else []):
                bad_emails = self.contacts["email"].dropna()
                bad_emails = bad_emails[~bad_emails.str.contains(r"@.+\..+", na=False)]
                if len(bad_emails) > 0:
                    issues.append(f"Malformed email addresses: {len(bad_emails)}")
                    penalties += min(len(bad_emails) / 3, 10)

            # Count total empty required fields
            for field in required_fields:
                if field in self.deals.columns:
                    empty_required += self.deals[field].isna().sum()
            if self.contacts is not None:
                for field in required_fields:
                    if field in self.contacts.columns:
                        empty_required += self.contacts[field].isna().sum()

        score = max(0, round(100 - penalties))
        return DataQualityScore(score, issues, duplicate_count, empty_required)


class DataQualityScore:
    """Container for data quality check results."""

    def __init__(self, overall: int, issue_list: list,
                 duplicate_count: int, empty_required: int):
        self.overall = overall
        self._issues = issue_list
        self.duplicate_count = duplicate_count
        self.empty_required = empty_required

    def issues(self) -> list:
        """Return list of identified issues."""
        return self._issues

    def summary(self) -> dict:
        """Summary dict for the audit report."""
        return {
            "score": self.overall,
            "top_issues": self._issues[:5],
            "duplicate_count": self.duplicate_count,
            "empty_required": self.empty_required,
        }

    def __repr__(self):
        return f"DataQualityScore(overall={self.overall}/100, issues={len(self._issues)})"

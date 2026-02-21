# CRM Audit Toolkit 🔍

**Open-source Python toolkit for analyzing CRM data and finding revenue leaks.**

Built and maintained by [Agine AI](https://agineai.com) — AI-powered CRM audit platform.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)

---

## What It Does

This toolkit helps sales teams and revenue operations professionals analyze their CRM data to find:

- **Dead Deals** — Stale opportunities sitting in your pipeline with no activity
- **Speed-to-Lead Issues** — How fast your team responds to new leads
- **Funnel Bottlenecks** — Pipeline stages where deals drop off at abnormal rates
- **Rep Performance Gaps** — Conversion and activity differences between team members
- **Data Quality Problems** — Missing fields, duplicates, and data hygiene issues

## Quick Start

### Installation

```bash
pip install pandas numpy
git clone https://github.com/kindhomehelp5-create/crm-audit-toolkit.git
cd crm-audit-toolkit
```

### Basic Usage

```python
from crm_audit import CRMAudit

# Load your CRM export (CSV)
audit = CRMAudit("deals_export.csv")

# Run all checks
report = audit.run_full_audit()

# Print summary
report.print_summary()

# Export detailed report
report.to_html("audit_report.html")
```

### Input Format

The toolkit expects a CSV export with these columns (names are configurable):

| Column | Description | Required |
|--------|-------------|----------|
| `deal_id` | Unique deal identifier | Yes |
| `deal_name` | Deal name | No |
| `stage` | Current pipeline stage | Yes |
| `amount` | Deal value | Yes |
| `created_at` | Deal creation date | Yes |
| `updated_at` | Last activity date | Yes |
| `closed_at` | Close date (if closed) | No |
| `owner` | Sales rep / owner | Yes |
| `status` | Won/Lost/Open | Yes |
| `lead_source` | Lead source | No |

## Audit Modules

### 1. Dead Deal Finder

Identifies deals with no activity beyond the expected cycle time.

```python
from crm_audit.modules import DeadDealFinder

finder = DeadDealFinder(deals_df)
dead_deals = finder.find(
    stale_threshold_days=30,  # Days without activity
    min_amount=1000           # Minimum deal value
)

print(f"Found {len(dead_deals)} dead deals")
print(f"Total pipeline at risk: ${dead_deals['amount'].sum():,.0f}")
```

### 2. Speed-to-Lead Analyzer

Measures response time from lead creation to first meaningful contact.

```python
from crm_audit.modules import SpeedToLead

stl = SpeedToLead(deals_df, activities_df)
results = stl.analyze(
    business_hours_only=True,
    exclude_weekends=True
)

# Average response time by rep
print(results.by_rep())

# Correlation with conversion rate
print(results.conversion_correlation())
```

### 3. Funnel Analysis

Calculates stage-by-stage conversion and identifies bottlenecks.

```python
from crm_audit.modules import FunnelAnalyzer

funnel = FunnelAnalyzer(deals_df)
analysis = funnel.analyze(
    stages=["Lead", "Qualified", "Demo", "Proposal", "Negotiation", "Closed Won"],
    period="last_6_months"
)

# Stage conversion rates
print(analysis.conversion_rates())

# Identify bottleneck stages (below expected conversion)
print(analysis.bottlenecks())

# Average time per stage
print(analysis.stage_duration())
```

### 4. Rep Performance Comparison

Compares key metrics across sales reps to identify coaching opportunities.

```python
from crm_audit.modules import RepPerformance

perf = RepPerformance(deals_df, activities_df)
comparison = perf.compare(
    metrics=["conversion_rate", "avg_deal_size", "cycle_time", "activity_count"],
    normalize_by="lead_quality"  # Fair comparison
)

print(comparison.summary())
print(comparison.coaching_recommendations())
```

### 5. Data Quality Check

Scores your CRM data quality and identifies hygiene issues.

```python
from crm_audit.modules import DataQuality

dq = DataQuality(deals_df, contacts_df)
score = dq.check(
    required_fields=["email", "company", "phone"],
    check_duplicates=True,
    check_formatting=True
)

print(f"Data Quality Score: {score.overall}/100")
print(score.issues())
```

## Configuration

Create a `config.yaml` file to customize field mappings and thresholds:

```yaml
# Column mappings (map your CRM export columns to toolkit fields)
columns:
  deal_id: "Opportunity ID"
  stage: "Sales Stage"
  amount: "Amount (USD)"
  created_at: "Created Date"
  updated_at: "Last Modified"
  owner: "Owner Full Name"
  status: "Stage Category"

# Thresholds
thresholds:
  stale_deal_days: 30
  speed_to_lead_target_hours: 4
  min_data_quality_score: 70

# Pipeline stages (in order)
stages:
  - "New Lead"
  - "Qualified"
  - "Demo Scheduled"
  - "Demo Completed"
  - "Proposal Sent"
  - "Negotiation"
  - "Closed Won"
  - "Closed Lost"
```

## Example Output

```
═══════════════════════════════════════════
         CRM AUDIT REPORT SUMMARY
═══════════════════════════════════════════

Period: 2024-07-01 to 2025-01-01
Total Deals Analyzed: 1,247
Total Pipeline Value: $4,832,000

─── DEAD DEALS ────────────────────────────
Dead deals found: 187 (15.0% of pipeline)
Revenue at risk: $723,400

─── SPEED TO LEAD ─────────────────────────
Average response time: 4.2 hours
Best rep: Sarah K. (0.8 hours avg)
Needs improvement: Mike T. (12.4 hours avg)
Estimated lost conversions: 23 deals

─── FUNNEL BOTTLENECK ─────────────────────
Biggest drop-off: Demo → Proposal (52% loss)
Expected: 30-35% loss
Revenue impact: ~$890,000/year

─── DATA QUALITY ──────────────────────────
Overall score: 64/100
Missing emails: 23% of contacts
Duplicate contacts: 89 found
Empty required fields: 312 records

═══════════════════════════════════════════
```

## Want More?

This toolkit provides a solid foundation for CRM analysis, but it's just the beginning.

**[Agine AI](https://agineai.com)** provides a full AI-powered CRM audit platform that:

- Connects directly to your CRM (no CSV exports needed)
- Uses advanced AI/ML models for deeper pattern recognition
- Provides automated, recurring audits
- Generates actionable recommendations with revenue impact estimates
- Includes executive-ready reports

**Try a free CRM audit at [agineai.com](https://agineai.com)**

## Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT License — see [LICENSE](LICENSE) for details.

## About

Built with ❤️ by [Agine AI](https://agineai.com) — AI-powered CRM audit and revenue intelligence platform.

- Website: [agineai.com](https://agineai.com)
- CRM Audit: [agineai.com/crm-audit](https://agineai.com/crm-audit)
- Telegram: [@agaborov](https://t.me/agaborov)

# CLAUDE.md

This file provides guidance for AI assistants working with the CRM Audit Toolkit codebase.

## Project Overview

CRM Audit Toolkit is an open-source Python toolkit for analyzing CRM data and finding revenue leaks. It helps sales teams and RevOps professionals identify dead deals, speed-to-lead issues, funnel bottlenecks, rep performance gaps, and data quality problems.

- **Language:** Python 3.9+
- **Core dependencies:** pandas, numpy
- **Configuration:** YAML (`config.yaml`)
- **License:** MIT
- **Maintainer:** Agine AI (https://agineai.com)

## Repository Structure

This project is in early development. The current file layout:

```
crm-audit-toolkit/
├── CLAUDE.md            # This file — AI assistant guidance
├── README.md            # Project documentation and usage examples
├── LICENSE              # MIT License
```

### Planned Architecture (from README)

The intended module structure once implemented:

```
crm-audit-toolkit/
├── crm_audit/
│   ├── __init__.py      # CRMAudit main class
│   └── modules/
│       ├── __init__.py
│       ├── dead_deal_finder.py   # DeadDealFinder
│       ├── speed_to_lead.py      # SpeedToLead
│       ├── funnel_analyzer.py    # FunnelAnalyzer
│       ├── rep_performance.py    # RepPerformance
│       └── data_quality.py       # DataQuality
├── config.yaml          # Column mappings and thresholds
├── requirements.txt     # Python dependencies
├── tests/               # Test suite
├── README.md
├── CONTRIBUTING.md
└── LICENSE
```

## Development Status

The repository currently contains only documentation (README.md and LICENSE). No Python source code, package configuration, tests, or CI/CD pipelines exist yet. All module descriptions below reflect the planned design documented in the README.

## Planned Audit Modules

1. **DeadDealFinder** — Identifies stale opportunities with no activity beyond expected cycle time
2. **SpeedToLead** — Measures response time from lead creation to first contact
3. **FunnelAnalyzer** — Calculates stage-by-stage conversion rates and identifies bottlenecks
4. **RepPerformance** — Compares metrics across sales reps for coaching opportunities
5. **DataQuality** — Scores CRM data quality and identifies hygiene issues

## Naming Conventions

Follow these conventions when writing code for this project:

- **Classes:** PascalCase (e.g., `CRMAudit`, `DeadDealFinder`, `SpeedToLead`)
- **Functions/methods:** snake_case (e.g., `run_full_audit`, `print_summary`, `to_html`)
- **Variables:** snake_case (e.g., `stale_threshold_days`, `deal_id`, `created_at`)
- **Modules/files:** snake_case (e.g., `dead_deal_finder.py`, `funnel_analyzer.py`)
- **Constants:** UPPER_SNAKE_CASE

## Input Data Format

The toolkit processes CSV exports with these columns (names configurable via `config.yaml`):

| Column       | Description                  | Required |
|-------------|------------------------------|----------|
| `deal_id`    | Unique deal identifier       | Yes      |
| `deal_name`  | Deal name                    | No       |
| `stage`      | Current pipeline stage       | Yes      |
| `amount`     | Deal value                   | Yes      |
| `created_at` | Deal creation date           | Yes      |
| `updated_at` | Last activity date           | Yes      |
| `closed_at`  | Close date (if closed)       | No       |
| `owner`      | Sales rep / owner            | Yes      |
| `status`     | Won/Lost/Open                | Yes      |
| `lead_source` | Lead source                 | No       |

## Build and Setup Commands

No build system is configured yet. The planned setup is:

```bash
pip install pandas numpy
git clone https://github.com/kindhomehelp5-create/crm-audit-toolkit.git
cd crm-audit-toolkit
```

When a `requirements.txt` or `pyproject.toml` is added, prefer:

```bash
pip install -r requirements.txt   # or: pip install -e .
```

## Testing

No test framework is configured yet. When tests are added, follow these conventions:

- Use `pytest` as the test runner
- Place tests in a `tests/` directory mirroring the source structure
- Name test files `test_<module>.py` (e.g., `test_dead_deal_finder.py`)
- Run tests with: `pytest`

## Key Design Patterns

Based on the README's API examples:

- **Entry point:** `CRMAudit` class accepts a CSV file path and orchestrates all modules
- **Module pattern:** Each audit module takes a pandas DataFrame, has an `analyze()` or `find()` method, and returns a results object
- **Results objects** support `.print_summary()`, `.to_html()`, and attribute access for metrics
- **Configuration** is loaded from `config.yaml` for column mappings, thresholds, and pipeline stage definitions
- **Output formats:** Console text summaries and HTML reports

## Common Workflows

### Adding a new audit module

1. Create a new file in `crm_audit/modules/` with snake_case naming
2. Implement a class with PascalCase name
3. Accept a pandas DataFrame in the constructor
4. Implement an `analyze()` or `find()` method returning a results object
5. Register the module in `CRMAudit.run_full_audit()`
6. Add corresponding tests in `tests/`

### Modifying column mappings

Column names from CRM exports are mapped via `config.yaml` under the `columns` key. The toolkit should never hard-code column names — always reference the configuration.

## Git Workflow

- **Primary branch:** `main`
- Write clear, descriptive commit messages
- Keep commits focused on a single logical change

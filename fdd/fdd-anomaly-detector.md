---
name: fdd-anomaly-detector
description: "Detect financial anomalies and red flags in FDD data. Use when: (1) scanning financial data for irregularities, (2) identifying unusual trends or patterns, (3) flagging potential accounting manipulation, (4) reviewing financial ratios for outliers, (5) any request to 'find anomalies', 'detect red flags', 'scan for issues', 'check for irregularities', or 'financial health check' in due diligence context."
---

# FDD Anomaly Detector Skill

## Overview

Systematically scan financial data to flag anomalies, red flags, and areas requiring further investigation. Uses Python (pandas, numpy) for statistical analysis and outputs flagged items with severity ratings.

## Workflow

1. Load financial data (from Excel or extracted PDF data)
2. Run all applicable anomaly tests
3. Score and rank findings by severity
4. Generate anomaly report (Excel or formatted summary)
5. Output to /mnt/user-data/outputs/

## Anomaly Test Categories

### Category 1: Trend Anomalies
```python
import pandas as pd
import numpy as np

def detect_trend_breaks(series, threshold=2.0):
    """Flag values that deviate > threshold standard deviations from trend."""
    rolling_mean = series.rolling(window=3, min_periods=1).mean()
    rolling_std = series.rolling(window=3, min_periods=1).std()
    z_scores = (series - rolling_mean) / rolling_std.replace(0, np.nan)
    return z_scores.abs() > threshold
```

Tests:
- Revenue growth rate sudden change (>2 std dev from trailing avg)
- Margin compression/expansion beyond historical range
- Expense category spikes vs trailing 12-month average
- Working capital ratio sudden shifts
- Capex pattern changes

### Category 2: Ratio Anomalies
Tests:
- DSO increasing while revenue declining (potential AR quality issue)
- DIO increasing (potential obsolete inventory)
- DPO stretching significantly (potential liquidity stress)
- Gross margin inconsistent with revenue mix changes
- SG&A as % of revenue deviating from peers
- EBITDA-to-operating-cash-flow divergence
- Accruals ratio (net income vs cash flow) abnormally high

### Category 3: Period-End Manipulation Indicators
Tests:
- Revenue concentration in last month of quarter (>40% = flag)
- Journal entries in last 3 days of period (volume spike)
- Revenue reversals in first month of next quarter
- Unusual AR credit memos post-period-end
- Inventory adjustments concentrated at period-end
- Significant "top-side" or manual journal entries

### Category 4: Benford's Law Analysis
```python
def benfords_law_test(data):
    """Test if leading digits follow expected Benford's distribution."""
    expected = {d: np.log10(1 + 1/d) for d in range(1, 10)}
    leading = data.astype(str).str[0].astype(int)
    observed = leading.value_counts(normalize=True).sort_index()
    # Chi-square test against expected
    # Large deviation suggests potential data manipulation
```

### Category 5: Relationship Anomalies
Tests:
- Revenue growing but AR growing faster (booking vs collection issue)
- Revenue growing but cash flow from operations declining
- Inventory growing faster than COGS (overproduction or obsolescence)
- Capex declining while D&A increasing (deferred maintenance)
- Headcount flat but payroll increasing significantly
- Revenue per employee declining trend

### Category 6: Accounting Quality Indicators
Tests:
- Frequent accounting policy changes
- Unusual increase in "Other" categories (revenue, expense, assets)
- Growing gap between book and tax income
- Increasing use of estimates and provisions
- Changes in depreciation methods or useful lives
- Soft asset growth (goodwill, intangibles, deferred costs)

## Severity Scoring

| Level | Criteria | Action |
|-------|----------|--------|
| 🔴 HIGH | Material impact (>5% of EBITDA), potential fraud indicator | Immediate investigation, flag to deal team |
| 🟡 MEDIUM | Notable deviation, may require adjustment | Detailed analysis, request additional data |
| 🟢 LOW | Minor variance, likely explainable | Document, ask management for explanation |

## Output Format

### Excel Report
Sheet 1: Summary Dashboard
- Total anomalies by severity (HIGH/MEDIUM/LOW)
- Anomalies by category
- Top 10 highest-priority findings

Sheet 2: Detailed Findings
| # | Category | Test | Finding | Severity | Period | Amount/Impact | Recommended Action |

Sheet 3: Trend Charts
- Visual charts highlighting anomalous data points

### Markdown Summary (for inclusion in FDD report)
```
## Anomaly Detection Results

### High Priority (X items)
1. **[Finding Title]** — [Brief description]. Impact: $XM. Action: [Recommended next step].

### Medium Priority (X items)
...

### Low Priority (X items)
...
```

## Critical Rules

- NEVER conclude fraud — only flag indicators for further investigation
- ALWAYS provide context (what is normal vs what was observed)
- ALWAYS quantify the potential impact where possible
- Include both absolute and percentage-based thresholds
- Consider industry norms when setting thresholds
- Flag items that management may need to explain

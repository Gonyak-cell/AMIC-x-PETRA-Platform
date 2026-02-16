---
name: fdd-report-generator
description: "Generate professional FDD (Financial Due Diligence) reports in Word (.docx) and PDF formats following Big 4 standards. Use when: (1) creating FDD report documents, (2) generating executive summaries for deals, (3) writing due diligence findings reports, (4) creating deal memos or investment memos, (5) any request to produce an 'FDD report', 'due diligence report', 'deal memo', or 'investment memo' in Word or PDF format."
---

# FDD Report Generator Skill

## Overview

Generate professional FDD reports using docx-js (Word) or reportlab (PDF). Follow the docx skill for Word and pdf skill for PDF creation.

## Workflow

1. Gather deal information (target name, buyer, date, scope)
2. Select report type → Apply template structure from references/
3. Generate document with proper formatting
4. Validate output
5. Save to /mnt/user-data/outputs/

## Report Types

| Type | Use Case | Format |
|------|----------|--------|
| Full FDD Report | Complete due diligence findings | Word (.docx) |
| Executive Summary | 2-3 page deal overview | Word or PDF |
| Red Flag Memo | Key risks and issues | Word (.docx) |
| Management Presentation | Findings for target mgmt | PDF |
| Deal Memo | Investment committee summary | Word (.docx) |

## Standard FDD Report Structure

For detailed section content, see [references/report_sections.md](references/report_sections.md).

```
1. Cover Page
2. Table of Contents
3. Disclaimer & Limitations
4. Executive Summary
5. Transaction Overview
6. Company Overview
7. Quality of Earnings Analysis
   7.1 Revenue Analysis
   7.2 Gross Profit Analysis
   7.3 Operating Expense Analysis
   7.4 EBITDA Bridge & Adjustments
   7.5 Normalized EBITDA Summary
8. Net Debt Analysis
   8.1 Net Debt Bridge
   8.2 Debt-Like Items
   8.3 Cash-Like Items
9. Working Capital Analysis
   9.1 NWC Components
   9.2 NWC Trend Analysis
   9.3 Target NWC Recommendation
10. Cash Flow Analysis
11. Key Findings & Risk Factors
    11.1 Red Flags
    11.2 Areas Requiring Further Investigation
    11.3 Key Assumptions & Sensitivities
12. Appendices
    A. Financial Statements
    B. Detailed Adjustment Schedules
    C. Data Request List
    D. Management Representations
```

## Formatting Standards

### Page Setup (Word)
```javascript
// US Letter, 1-inch margins
page: {
  size: { width: 12240, height: 15840 },
  margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 }
}
```

### Typography
- Title: Arial 24pt Bold
- Heading 1: Arial 16pt Bold, Dark Blue (#1F4E79)
- Heading 2: Arial 13pt Bold
- Body: Arial 11pt
- Table text: Arial 9-10pt
- Footer: Arial 8pt Gray

### Table Standards
- Header row: Dark Blue (#1F4E79) background, white text
- Alternating rows: Light Gray (#F2F2F2) and White
- Financial data: Right-aligned
- Labels: Left-aligned
- All borders: Light gray (#CCCCCC), thin

### Confidentiality
- Every page footer: "CONFIDENTIAL — Prepared for [Client Name]"
- Cover page: "STRICTLY PRIVATE AND CONFIDENTIAL"
- Watermark on drafts: "DRAFT — FOR DISCUSSION PURPOSES ONLY"

## Critical Rules

- Include disclaimer on every report
- Mark DRAFT versions clearly
- Number all pages
- Cross-reference to Excel workbook for detailed schedules
- Use consistent terminology throughout
- Date all findings and data sources
-e 

---

# FDD Report Sections Reference

## 1. Cover Page Content
```
[Client Logo Placeholder]

FINANCIAL DUE DILIGENCE REPORT

Project [Code Name]
Prepared for: [Buyer Name]
Target: [Target Company Name]
Date: [Report Date]
Status: DRAFT / FINAL

STRICTLY PRIVATE AND CONFIDENTIAL

Prepared by: [Firm Name]
```

## 3. Disclaimer & Limitations

Standard disclaimer template:
```
This report has been prepared solely for the use of [Buyer] in connection
with the proposed acquisition of [Target]. This report is confidential and
must not be disclosed to any third party without prior written consent.

Our work has been limited to the procedures described herein and does not
constitute an audit or review in accordance with generally accepted auditing
standards. We have relied upon unaudited financial information and
representations of management, which we have not independently verified.

Scope limitations:
- Financial data reviewed: [Period range]
- Information provided by: [Management / data room]
- Site visits conducted: [Yes/No, dates]
- Management interviews: [Yes/No, dates]
- Tax due diligence: [In/Out of scope]
- Legal due diligence: [In/Out of scope]
```

## 4. Executive Summary

Structure (2-3 pages maximum):
```
EXECUTIVE SUMMARY

Transaction Overview
- [Buyer] proposes to acquire [100%/majority stake] in [Target]
- Enterprise Value: $[X]M, implying [X.X]x LTM Adjusted EBITDA
- Expected completion: [Date]

Key Financial Highlights
- LTM Revenue: $[X]M ([X]% YoY growth)
- LTM Adjusted EBITDA: $[X]M ([X]% margin)
- Total QoE adjustments: $[X]M (net increase/decrease to reported EBITDA)
- Net Debt at completion (estimated): $[X]M
- Target NWC: $[X]M

Key Findings Summary
[Numbered list of 5-10 most important findings]

Red Flags / Areas of Concern
[Numbered list of critical issues requiring attention]

Recommended Actions
[Numbered list of follow-up items]
```

## 7. Quality of Earnings Section

### 7.1 Revenue Analysis
- Revenue by product/service line (3-year trend)
- Revenue by geography/segment
- Customer concentration (top 5/10/20 customers as % of revenue)
- Revenue recognition policies and timing
- Backlog/pipeline analysis
- Contract terms and renewal rates

### 7.4 EBITDA Bridge & Adjustments
For each adjustment include:
1. Description of the item
2. Amount by period
3. Rationale for adjustment (why non-recurring/non-operating)
4. Supporting evidence / documentation reviewed
5. Management's position vs. FDD team's position

### Table Format for Adjustments
```
| # | Adjustment Description | FY20XX | FY20XX | FY20XX | LTM | Rationale |
|---|----------------------|--------|--------|--------|-----|-----------|
| 1 | Restructuring charges | X | X | X | X | One-time... |
| 2 | Litigation settlement | X | X | X | X | Non-recurring...|
|   | Total Adjustments    | X | X | X | X |           |
```

## 11. Key Findings & Risk Factors

### Red Flag Categories
Rate each as: HIGH / MEDIUM / LOW risk

1. **Financial Reporting Risk** — Aggressive accounting, late close, restatements
2. **Revenue Quality Risk** — Customer concentration, contract expiry, one-time sales
3. **Cost Structure Risk** — Deferred maintenance, below-market compensation
4. **Working Capital Risk** — Aging AR, obsolete inventory, seasonal swings
5. **Tax Risk** — Uncertain tax positions, transfer pricing, NOL limitations
6. **Operational Risk** — Key person dependency, supplier concentration
7. **Legal/Compliance Risk** — Pending litigation, regulatory issues
8. **IT/Systems Risk** — Legacy systems, data integrity concerns

### Findings Format
```
Finding #[X]: [Title]
Risk Level: HIGH / MEDIUM / LOW
Impact: $[X]M estimated / Unquantifiable

Description:
[2-3 sentence description of the issue]

Evidence:
[What was reviewed/observed]

Recommendation:
[Suggested action for buyer]
```

---
name: fdd-checklist
description: "Generate and track FDD (Financial Due Diligence) checklists, data request lists, and progress trackers. Use when: (1) creating FDD due diligence checklists, (2) generating data request lists for target companies, (3) tracking FDD workstream progress, (4) creating deal timeline trackers, (5) any request for 'checklist', 'data request list', 'information request', 'due diligence tracker', or 'FDD progress tracking'."
---

# FDD Checklist Skill

## Overview

Generate comprehensive FDD checklists and trackers in Excel or as interactive web dashboards.

## Workflow

1. Determine checklist type (full FDD, data request, progress tracker)
2. Customize for deal specifics (industry, size, structure)
3. Generate formatted Excel or React dashboard
4. Output to /mnt/user-data/outputs/

## Checklist Types

### Type 1: Master FDD Checklist
Complete list of all FDD procedures. See [references/master_checklist.md](references/master_checklist.md).

### Type 2: Data Request List (IRL/DRL)
Documents to request from target company. See [references/data_request_list.md](references/data_request_list.md).

### Type 3: Progress Tracker
Track completion status across workstreams.

## Excel Output Format

### Columns
| Column | Content |
|--------|---------|
| A | Category |
| B | # (Item number) |
| C | Description |
| D | Priority (H/M/L) |
| E | Status (Not Started / In Progress / Complete / N/A) |
| F | Assigned To |
| G | Due Date |
| H | Date Completed |
| I | Notes / Findings |
| J | Source Document Reference |

### Conditional Formatting
```python
# Status colors
"Not Started" → Red fill (#FFC7CE)
"In Progress" → Yellow fill (#FFEB9C)
"Complete" → Green fill (#C6EFCE)
"N/A" → Gray fill (#D9D9D9)

# Priority colors
"H" (High) → Red font
"M" (Medium) → Orange font
"L" (Low) → Black font

# Overdue = Due Date < Today AND Status != Complete
→ Red bold border
```

### Summary Dashboard (first sheet)
```
Total Items: =COUNTA(Checklist!C:C)-1
Not Started: =COUNTIF(Checklist!E:E,"Not Started")
In Progress: =COUNTIF(Checklist!E:E,"In Progress")
Complete: =COUNTIF(Checklist!E:E,"Complete")
N/A: =COUNTIF(Checklist!E:E,"N/A")
Completion %: =Complete/(Total-N/A)
Overdue Items: =COUNTIFS(Checklist!G:G,"<"&TODAY(),Checklist!E:E,"<>Complete")
```

## React Dashboard Alternative

When user requests interactive tracker, create React component with:
- Progress bars by category
- Filterable/sortable table
- Status dropdown per item
- Persistent storage for tracking across sessions
- Color-coded priority and status indicators
-e 

---

# FDD Master Checklist Reference

## 1. QUALITY OF EARNINGS (QoE)
- [ ] Obtain and reconcile management accounts to audited financials
- [ ] Analyze revenue by product/service/geography/customer
- [ ] Identify top 10 customer concentration and trend
- [ ] Review revenue recognition policies for appropriateness
- [ ] Test for cut-off issues at period ends
- [ ] Analyze gross margin by product/service line
- [ ] Identify non-recurring revenue items
- [ ] Review deferred revenue roll-forward
- [ ] Analyze COGS components and trends
- [ ] Review inventory valuation and obsolescence
- [ ] Analyze operating expenses by category (3+ years)
- [ ] Identify non-recurring expenses
- [ ] Review owner/related-party compensation vs market
- [ ] Identify personal expenses through the business
- [ ] Review related-party transactions at arm's length
- [ ] Calculate normalized EBITDA with all adjustments
- [ ] Compare management EBITDA to FDD adjusted EBITDA
- [ ] Analyze margin trends and sustainability
- [ ] Review accounting policy changes in period
- [ ] Assess impact of new accounting standards (ASC 606, 842)

## 2. NET DEBT
- [ ] Obtain detailed debt schedule with terms
- [ ] Verify cash balances (bank confirmations)
- [ ] Identify restricted cash
- [ ] Review revolving credit facility terms/covenants
- [ ] List all term loans with maturity dates
- [ ] Identify capital/finance lease obligations
- [ ] Review operating lease commitments (IFRS 16 impact)
- [ ] Identify earn-out obligations and fair value
- [ ] Review pension/post-retirement obligation (funded status)
- [ ] Identify contingent liabilities
- [ ] Review letters of credit/guarantees
- [ ] Check for off-balance-sheet financing (factoring, securitization)
- [ ] Assess debt prepayment penalties
- [ ] Calculate accrued but unpaid interest at completion
- [ ] Identify transaction-related costs to be paid at close

## 3. WORKING CAPITAL
- [ ] Obtain monthly working capital for 24+ months
- [ ] Analyze AR aging and DSO trends
- [ ] Review bad debt provision adequacy
- [ ] Analyze inventory by category (raw, WIP, FG)
- [ ] Review inventory aging and obsolescence reserve
- [ ] Analyze DIO trends
- [ ] Review AP aging and DPO trends
- [ ] Analyze accrued expense components
- [ ] Review deferred revenue trends
- [ ] Identify seasonal patterns in NWC
- [ ] Calculate target/peg NWC
- [ ] Identify excluded items (cash, debt, tax, intercompany)
- [ ] Assess NWC mechanism in SPA
- [ ] Review significant NWC fluctuations

## 4. CASH FLOW
- [ ] Reconcile reported cash flow to bank statements
- [ ] Analyze operating cash flow vs EBITDA conversion
- [ ] Review capex (maintenance vs growth)
- [ ] Identify deferred/delayed capex
- [ ] Analyze free cash flow trends
- [ ] Review working capital impact on cash flow
- [ ] Identify one-time cash flow items

## 5. TAX (if in scope)
- [ ] Obtain tax returns for review period
- [ ] Review effective tax rate vs statutory rate
- [ ] Identify uncertain tax positions
- [ ] Review tax loss carryforwards and limitations
- [ ] Assess transfer pricing risks
- [ ] Review open tax audits/disputes
- [ ] Identify change-of-control tax implications

## 6. IT / SYSTEMS (if in scope)
- [ ] Understand ERP and financial reporting systems
- [ ] Assess data integrity and controls
- [ ] Review system change log during period
- [ ] Identify manual journal entries and frequency
- [ ] Assess TSA requirements post-close

## 7. COMMERCIAL / OPERATIONAL
- [ ] Review key customer contracts and renewal risk
- [ ] Analyze customer churn/retention rates
- [ ] Review key supplier contracts
- [ ] Identify key person dependencies
- [ ] Review employee headcount trends
- [ ] Assess compensation benchmarking
- [ ] Review pending or threatened litigation
- [ ] Identify regulatory/compliance risks
- [ ] Review insurance coverage adequacy
-e 

---

# FDD Data Request List (Information Request List)

## 1. GENERAL / CORPORATE
1.1 Organization chart (legal entity and operational)
1.2 List of all legal entities, jurisdictions, ownership %
1.3 Shareholder register and cap table
1.4 Articles of incorporation / bylaws
1.5 Board meeting minutes (last 3 years)
1.6 Management biographies and employment agreements
1.7 Related party list and transaction details

## 2. FINANCIAL STATEMENTS & REPORTING
2.1 Audited financial statements (last 3 fiscal years)
2.2 Management letters from auditors (last 3 years)
2.3 Monthly management accounts (last 24 months)
2.4 Trial balance by month (last 24 months)
2.5 Chart of accounts with descriptions
2.6 General ledger detail (last 12 months)
2.7 Accounting policies and procedures manual
2.8 Budget/forecast for current and next fiscal year
2.9 Long-range plan / 5-year projections (if available)
2.10 Board presentations with financial data

## 3. REVENUE
3.1 Revenue by product/service line (monthly, 3 years)
3.2 Revenue by customer (top 50, monthly, 3 years)
3.3 Revenue by geography/region (monthly, 3 years)
3.4 Pricing schedules and recent price changes
3.5 Customer contracts (top 20 by revenue)
3.6 Backlog/pipeline report (current)
3.7 Customer churn/retention analysis
3.8 Deferred revenue roll-forward (monthly, 2 years)
3.9 Revenue recognition policy documentation

## 4. COST OF GOODS SOLD
4.1 COGS breakdown by component (monthly, 3 years)
4.2 Bill of materials for key products
4.3 Direct labor cost analysis
4.4 Manufacturing overhead allocation methodology
4.5 Supplier contracts (top 10 by spend)
4.6 Purchase orders log (last 12 months)

## 5. OPERATING EXPENSES
5.1 OpEx by department (monthly, 3 years)
5.2 Headcount by department (monthly, 2 years)
5.3 Payroll register / summary (last 12 months)
5.4 Compensation details for senior management
5.5 Bonus/commission plans and accruals
5.6 Professional fees detail (legal, accounting, consulting)
5.7 Travel & entertainment detail (last 12 months)
5.8 Rent/lease schedule for all locations
5.9 Insurance policies and premium schedule
5.10 IT spending detail (software, hardware, cloud)
5.11 Non-recurring / one-time expense detail

## 6. BALANCE SHEET
6.1 Bank statements (all accounts, last 12 months)
6.2 Bank reconciliations (last 6 months)
6.3 AR aging schedule (monthly, last 12 months)
6.4 AR write-off/bad debt detail (last 3 years)
6.5 Inventory detail by category (monthly, last 12 months)
6.6 Inventory aging / obsolescence report
6.7 Fixed asset register with depreciation schedule
6.8 Capital expenditure detail (last 3 years)
6.9 Capex budget (current and next year)
6.10 AP aging schedule (monthly, last 12 months)
6.11 Accrued expense detail (monthly, last 12 months)
6.12 Prepaid expense schedule

## 7. DEBT & FINANCING
7.1 Debt schedule (all facilities, terms, rates, maturity)
7.2 Loan agreements and amendments
7.3 Covenant compliance certificates (last 8 quarters)
7.4 Capital lease/finance lease schedules
7.5 Operating lease schedule (pre/post ASC 842)
7.6 Letters of credit / guarantees outstanding
7.7 Factoring/securitization agreements
7.8 Earn-out/deferred consideration agreements

## 8. TAX
8.1 Federal and state/local tax returns (last 3 years)
8.2 Tax provision workpapers (last 3 years)
8.3 NOL/tax credit carryforward schedule
8.4 Transfer pricing documentation
8.5 Open tax audits/disputes
8.6 Sales/use tax returns and status
8.7 Property tax assessments

## 9. LEGAL & COMPLIANCE
9.1 Pending/threatened litigation summary
9.2 Regulatory compliance certifications
9.3 Environmental reports/assessments
9.4 IP portfolio (patents, trademarks, copyrights)
9.5 Material contracts not otherwise provided
9.6 Government contracts (if applicable)

## 10. IT & SYSTEMS
10.1 ERP/accounting system description
10.2 System architecture diagram
10.3 IT infrastructure summary
10.4 Software license inventory
10.5 Data security/privacy policies
10.6 Disaster recovery/business continuity plans

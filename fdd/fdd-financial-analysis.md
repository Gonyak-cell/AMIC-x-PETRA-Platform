---
name: fdd-financial-analysis
description: "Financial Due Diligence (FDD) analysis skill for creating Quality of Earnings (QoE), Net Debt, Working Capital, and cash flow analysis in Excel. Use when: (1) building FDD financial models, (2) analyzing Quality of Earnings adjustments, (3) computing normalized EBITDA, (4) Net Debt bridge analysis, (5) Working Capital trend analysis, (6) creating pro-forma financial statements, (7) any request mentioning 'FDD', 'due diligence', 'QoE', 'quality of earnings', 'net debt bridge', 'working capital analysis', or 'normalized EBITDA'."
---

# FDD Financial Analysis Skill

## Overview

Build FDD Excel models following Big 4 accounting firm standards. All outputs use openpyxl with proper Excel formulas (never hardcoded calculations).

## Workflow

1. Determine analysis type → Select appropriate template from references/
2. Create Excel workbook with standardized tabs
3. Apply FDD color coding and formatting
4. Insert Excel formulas (never hardcode calculated values)
5. Run recalc.py to verify zero formula errors
6. Output to /mnt/user-data/outputs/

## Standard Tab Structure

Every FDD model MUST include these sheets (add more as needed):

| Sheet | Purpose |
|-------|---------|
| Cover | Deal name, date, preparer, status |
| TOC | Table of contents with hyperlinks |
| QoE | Quality of Earnings analysis |
| Net Debt | Net Debt bridge at completion |
| Working Capital | NWC trend and target analysis |
| Revenue | Revenue breakdown and trends |
| OPEX | Operating expense analysis |
| Cash Flow | Cash flow reconciliation |
| Assumptions | All assumptions in one place |
| Sources | Data sources and references |

## FDD Color Coding (Apply to ALL sheets)

```python
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

BLUE_INPUT = Font(color="0000FF")        # User inputs / hardcoded values
BLACK_FORMULA = Font(color="000000")     # Formulas and calculations
GREEN_LINK = Font(color="008000")        # Cross-sheet references
RED_EXTERNAL = Font(color="FF0000")      # External data links
YELLOW_ATTENTION = PatternFill("solid", fgColor="FFFF00")  # Needs review
HEADER_FILL = PatternFill("solid", fgColor="1F4E79")
HEADER_FONT = Font(color="FFFFFF", bold=True, name="Arial", size=11)
SUBTOTAL_FILL = PatternFill("solid", fgColor="D6E4F0")
TOTAL_FILL = PatternFill("solid", fgColor="B4C6E7")
```

## Number Formatting

```python
FORMATS = {
    "currency": '$#,##0;($#,##0);"-"',
    "currency_k": '$#,##0,"K";($#,##0,"K");"-"',
    "currency_m": '$#,##0.0,,"M";($#,##0.0,,"M");"-"',
    "percent": '0.0%;(0.0%);"-"',
    "multiple": '0.0x',
    "number": '#,##0;(#,##0);"-"',
    "year": '@',
    "date": 'YYYY-MM-DD',
}
```

## Quality of Earnings (QoE) Template

For detailed QoE structure and adjustment categories, see [references/qoe_template.md](references/qoe_template.md).

Key sections: Reported Revenue/COGS/Gross Profit → Reported EBITDA bridge → Adjustments (non-recurring, non-operating, normalization) → Adjusted EBITDA → Management vs Adjusted comparison → Margin analysis

## Net Debt Bridge Template

For detailed Net Debt categories, see [references/net_debt_template.md](references/net_debt_template.md).

Structure: Cash (+) → Short-term debt (-) → Long-term debt (-) → Capital leases (-) → Debt-like items → Net Debt at completion

## Working Capital Analysis Template

For detailed NWC structure, see [references/working_capital_template.md](references/working_capital_template.md).

Structure: Current Assets (AR, Inventory, Prepaid) → Current Liabilities (AP, Accrued, Deferred Revenue) → NWC = CA - CL → NWC % of Revenue trend → Target NWC peg

## Critical Rules

- ALWAYS use Excel formulas, never hardcode calculated values
- ALWAYS run recalc.py after creating the file
- ALWAYS include source documentation for every hardcoded number
- ALWAYS apply FDD color coding consistently
- Period headers as text ("FY2022" not 2022)
- Negative numbers in parentheses: (1,234) not -1,234
- Include variance columns ($ and %) between periods
-e 

---

# Quality of Earnings (QoE) Template Reference

## Sheet Structure

### Row Layout
```
Row 1-3: Header (Deal Name, Period, Prepared By)
Row 5: Column headers (Line Item | FY20XX | FY20XX | FY20XX | LTM | YoY$ | YoY%)
Row 6: ---separator---

SECTION A: INCOME STATEMENT SUMMARY
Row 7:  Revenue
Row 8:    Product Revenue
Row 9:    Service Revenue
Row 10:   Other Revenue
Row 11: Total Revenue (=SUM formula)
Row 12: (-) COGS
Row 13: Gross Profit (=Revenue - COGS)
Row 14: Gross Margin % (=GP/Revenue)
Row 15: ---separator---

SECTION B: OPERATING EXPENSES
Row 16: Sales & Marketing
Row 17: General & Administrative
Row 18: Research & Development
Row 19: Depreciation & Amortization
Row 20: Other Operating Expenses
Row 21: Total Operating Expenses (=SUM)
Row 22: ---separator---

SECTION C: REPORTED EBITDA BRIDGE
Row 23: Operating Income (=GP - OpEx + D&A)
Row 24: (+) Depreciation & Amortization
Row 25: Reported EBITDA
Row 26: EBITDA Margin %
Row 27: ---separator---

SECTION D: QoE ADJUSTMENTS
Row 28: HEADER - Non-Recurring Items
Row 29:   (+) Restructuring charges
Row 30:   (+) Litigation / settlement costs
Row 31:   (+) Transaction costs (M&A, IPO)
Row 32:   (+) One-time consulting / advisory
Row 33:   (+) Natural disaster / COVID impacts
Row 34:   (+) Asset impairments / write-downs
Row 35: Subtotal Non-Recurring

Row 36: HEADER - Non-Operating Items
Row 37:   (+/-) Owner/related-party compensation adj
Row 38:   (+/-) Above/below market rent (related party)
Row 39:   (+) Personal expenses through company
Row 40:   (+/-) Related party revenue/cost adjustments
Row 41: Subtotal Non-Operating

Row 42: HEADER - Normalization Adjustments
Row 43:   (+/-) Revenue recognition timing
Row 44:   (+/-) Inventory valuation adjustments
Row 45:   (+/-) Accounting policy changes
Row 46:   (+/-) Run-rate salary adjustments (new hires/departures)
Row 47:   (+/-) Pro-forma cost savings (synergies)
Row 48:   (+/-) Seasonality normalization
Row 49: Subtotal Normalization

Row 50: ---separator---
Row 51: TOTAL QoE Adjustments (=Sum of subtotals)
Row 52: ---separator---

SECTION E: ADJUSTED EBITDA
Row 53: Adjusted EBITDA (=Reported + Total Adjustments)
Row 54: Adjusted EBITDA Margin %
Row 55: ---separator---

SECTION F: MANAGEMENT vs ADJUSTED COMPARISON
Row 56: Management EBITDA
Row 57: Adjusted EBITDA (link)
Row 58: Difference ($)
Row 59: Difference (%)
```

## Adjustment Categories Detail

### Non-Recurring Items (add back to EBITDA)
Items that occurred but are not expected to recur:
- Restructuring charges (severance, facility closure)
- Litigation and settlement costs
- Transaction / deal costs
- One-time consulting projects
- Natural disaster / pandemic impacts
- Asset impairments and write-downs
- Gain/loss on disposal of assets
- Insurance proceeds (one-time)

### Non-Operating Items (add back or deduct)
Items related to owner/related-party transactions:
- Owner compensation above/below market rate
- Related-party rent above/below market
- Personal expenses run through the business
- Related-party sales/purchases at non-arm's length
- Management fees to parent/holding company
- Non-business use of assets

### Normalization Adjustments (adjust to run-rate)
Items to reflect ongoing business economics:
- Revenue recognition timing differences
- Inventory valuation method changes
- New hire/departure salary run-rate
- Pro-forma impact of acquisitions/divestitures
- Contract wins/losses not yet in financials
- Seasonality normalization for partial periods
- Pro-forma cost savings (if buyer-specific, flag separately)

## Formula Patterns

```python
# Gross Profit
sheet[f'B13'] = f'=B11-B12'

# EBITDA
sheet[f'B25'] = f'=B23+B24'

# EBITDA Margin
sheet[f'B26'] = f'=IF(B11=0,0,B25/B11)'

# Total Adjustments
sheet[f'B51'] = f'=B35+B41+B49'

# Adjusted EBITDA
sheet[f'B53'] = f'=B25+B51'

# YoY $ Variance
sheet[f'E7'] = f'=D7-C7'

# YoY % Variance
sheet[f'F7'] = f'=IF(C7=0,0,(D7-C7)/ABS(C7))'
```
-e 

---

# Net Debt Bridge Template Reference

## Sheet Structure

```
Row 1-3: Header (Deal Name, Completion Date, Currency)
Row 5: Column headers (Item | Book Value | Adjustments | FDD Adjusted | Notes)

SECTION A: CASH & EQUIVALENTS
Row 7:  Cash on hand
Row 8:  Bank balances
Row 9:  Short-term investments (< 3 months)
Row 10: Restricted cash (flag if not freely available)
Row 11: Total Cash & Equivalents (=SUM, positive)

SECTION B: FUNDED DEBT
Row 13: Revolving credit facility
Row 14: Term loan A
Row 15: Term loan B
Row 16: Senior notes / bonds
Row 17: Subordinated / mezzanine debt
Row 18: Shareholder loans
Row 19: Bank overdrafts
Row 20: Total Funded Debt (=SUM, negative)

SECTION C: CAPITAL LEASES / FINANCE LEASES
Row 22: Equipment leases
Row 23: Real estate leases (IFRS 16 / ASC 842)
Row 24: Vehicle leases
Row 25: Total Capital Leases (=SUM, negative)

SECTION D: DEBT-LIKE ITEMS
Row 27: Deferred consideration / earn-outs
Row 28: Pension / post-retirement obligations (unfunded)
Row 29: Deferred tax liabilities (non-current)
Row 30: Accrued restructuring costs
Row 31: Outstanding litigation / claims
Row 32: Environmental liabilities
Row 33: Deferred rent obligations
Row 34: Capital expenditure commitments
Row 35: Customer deposits (if repayable)
Row 36: Total Debt-Like Items (=SUM, negative)

SECTION E: CASH-LIKE ITEMS
Row 38: Tax refunds receivable
Row 39: Insurance claims receivable
Row 40: Excess cash in subsidiaries
Row 41: Non-operating assets held for sale
Row 42: Total Cash-Like Items (=SUM, positive)

SECTION F: NET DEBT SUMMARY
Row 44: Total Cash & Equivalents (=link to Row 11)
Row 45: (-) Total Funded Debt (=link to Row 20)
Row 46: (-) Total Capital Leases (=link to Row 25)
Row 47: (-) Total Debt-Like Items (=link to Row 36)
Row 48: (+) Total Cash-Like Items (=link to Row 42)
Row 49: ═══════════════════════════
Row 50: NET DEBT (=SUM of above)
```

## Key Considerations

### Items Often Missed
- Bank overdrafts (sometimes netted against cash)
- Finance lease obligations post-IFRS 16
- Pension underfunding
- Earn-out present value
- Accrued interest on debt
- Prepayment penalties on debt refinancing
- Letters of credit / guarantees
- Factored receivables (off-balance-sheet debt)

### Common Adjustments Column
- Mark-to-market adjustments on debt
- Fair value of hedging instruments
- Foreign currency translation on debt
- Accrued but unpaid interest
- Debt issuance costs (add back to gross debt)

## Formula Patterns

```python
# Net Debt = Cash - Debt - Leases - Debt-like + Cash-like
sheet['D50'] = '=D11+D20+D25+D36+D42'

# Adjustment impact
sheet['D7'] = '=B7+C7'  # Book + Adjustment = FDD Adjusted
```
-e 

---

# Working Capital Analysis Template Reference

## Sheet Structure

```
Row 1-3: Header (Deal Name, Analysis Period, Currency)
Row 5: Column headers (Item | M1 | M2 | ... | M12 | Avg | Target | Notes)

SECTION A: CURRENT ASSETS
Row 7:  Accounts Receivable (gross)
Row 8:    (-) Allowance for doubtful accounts
Row 9:  Net Accounts Receivable
Row 10: Inventory - Raw Materials
Row 11: Inventory - WIP
Row 12: Inventory - Finished Goods
Row 13: Total Inventory
Row 14: Prepaid Expenses
Row 15: Other Current Assets
Row 16: Total Current Assets (=SUM)

SECTION B: CURRENT LIABILITIES
Row 18: Accounts Payable
Row 19: Accrued Expenses
Row 20: Accrued Payroll & Benefits
Row 21: Deferred Revenue (current portion)
Row 22: Customer Deposits
Row 23: Income Tax Payable
Row 24: Other Current Liabilities
Row 25: Total Current Liabilities (=SUM)

SECTION C: NET WORKING CAPITAL
Row 27: Net Working Capital (=CA - CL)
Row 28: NWC as % of Revenue
Row 29: NWC as % of LTM Revenue

SECTION D: TARGET / PEG NWC
Row 31: Average NWC (trailing 12 months)
Row 32: Median NWC (trailing 12 months)
Row 33: Agreed Target NWC (peg)
Row 34: NWC at Completion
Row 35: Surplus / (Shortfall) vs Target

SECTION E: EFFICIENCY METRICS
Row 37: Days Sales Outstanding (DSO) = AR / Revenue * Days
Row 38: Days Inventory Outstanding (DIO) = Inv / COGS * Days
Row 39: Days Payable Outstanding (DPO) = AP / COGS * Days
Row 40: Cash Conversion Cycle = DSO + DIO - DPO

SECTION F: EXCLUDED ITEMS (Not in NWC for deal purposes)
Row 42: Cash & equivalents
Row 43: Short-term debt / current portion of LTD
Row 44: Income tax receivable/payable
Row 45: Intercompany balances
Row 46: Deferred tax assets/liabilities (current)
```

## Target NWC (Peg) Methodologies

1. **Trailing Average**: Average of last 12 months NWC
2. **Trailing Median**: Median of last 12 months (reduces outlier impact)
3. **Normalized Average**: Remove seasonal peaks/troughs, then average
4. **Revenue-Based**: NWC as fixed % of projected revenue
5. **Negotiated**: Buyer/seller agreed fixed amount

## Formula Patterns

```python
# NWC
sheet[f'B27'] = f'=B16-B25'

# NWC % of Revenue
sheet[f'B28'] = f'=IF(Revenue!B11=0,0,B27/Revenue!B11)'

# DSO
sheet[f'B37'] = f'=IF(Revenue!B11=0,0,B9/(Revenue!B11/365))'

# DIO
sheet[f'B38'] = f'=IF(QoE!B12=0,0,B13/(QoE!B12/365))'

# DPO
sheet[f'B39'] = f'=IF(QoE!B12=0,0,B18/(QoE!B12/365))'

# CCC
sheet[f'B40'] = f'=B37+B38-B39'

# Trailing 12M Average
sheet['N31'] = '=AVERAGE(B27:M27)'

# Surplus/(Shortfall)
sheet['B35'] = '=B34-B33'
```

## Key Exclusions from NWC (Common Deal Terms)

Items typically excluded from NWC calculation in SPAs:
- Cash and cash equivalents (in Net Debt)
- Short-term debt / CPLTD (in Net Debt)
- Income tax receivable/payable (separate tax mechanism)
- Intercompany balances (eliminated at close)
- Non-trade receivables/payables
- Deferred revenue > 12 months
- Contingent liabilities

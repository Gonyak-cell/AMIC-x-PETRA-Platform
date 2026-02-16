---
name: fdd-data-extractor
description: "Extract financial data from PDF financial statements, trial balances, and audit reports into structured Excel format for FDD analysis. Use when: (1) extracting tables from PDF financial statements, (2) parsing trial balance PDFs, (3) converting audit reports to Excel, (4) extracting Balance Sheet, Income Statement, or Cash Flow Statement from PDF, (5) any request to 'extract', 'parse', or 'pull data from' financial PDFs, (6) processing scanned financial documents with OCR."
---

# FDD Data Extractor Skill

## Overview

Extract financial data from PDF documents into structured Excel files. Uses pdfplumber for text PDFs and pytesseract+pdf2image for scanned documents.

## Workflow

1. Identify document type (financial statement, trial balance, audit report)
2. Extract text/tables from PDF
3. Parse and structure the data
4. Map to standard FDD chart of accounts
5. Output as formatted Excel file
6. Verify extraction accuracy

## Document Type Detection

| Document | Key Indicators |
|----------|---------------|
| Balance Sheet | "Assets", "Liabilities", "Equity", "Financial Position" |
| Income Statement | "Revenue", "Net Income", "Profit or Loss", "Operations" |
| Cash Flow Statement | "Operating Activities", "Investing", "Financing" |
| Trial Balance | Debit/Credit columns, account numbers |
| Audit Report | "Independent Auditor", "Opinion", "Going Concern" |
| Tax Return | Form numbers (1120, 1065), "Taxable Income" |

## Extraction Methods

### Method 1: Text PDF with Tables (preferred)
```python
import pdfplumber
import pandas as pd

with pdfplumber.open("financial_statement.pdf") as pdf:
    all_tables = []
    for page in pdf.pages:
        tables = page.extract_tables()
        for table in tables:
            if table and len(table) > 1:
                df = pd.DataFrame(table[1:], columns=table[0])
                all_tables.append(df)
```

### Method 2: Text PDF without Tables (layout-based)
```python
with pdfplumber.open("document.pdf") as pdf:
    for page in pdf.pages:
        text = page.extract_text()
        # Parse line by line, detect numbers with regex
        lines = text.split('\n')
        for line in lines:
            # Match patterns like "Revenue  1,234,567"
            # or "  Accounts Receivable    $45,678"
```

### Method 3: Scanned PDF (OCR)
```python
import pytesseract
from pdf2image import convert_from_path

images = convert_from_path('scanned.pdf', dpi=300)
for image in images:
    text = pytesseract.image_to_string(image)
```

## Standard Chart of Accounts Mapping

For FDD purposes, map extracted accounts to these standard categories.
See [references/chart_of_accounts.md](references/chart_of_accounts.md) for complete mapping.

### Quick Reference
```
1000s - Assets
  1100 - Cash & Equivalents
  1200 - Accounts Receivable
  1300 - Inventory
  1400 - Prepaid & Other CA
  1500 - PP&E
  1600 - Intangibles & Goodwill
2000s - Liabilities
  2100 - Accounts Payable
  2200 - Accrued Liabilities
  2300 - Short-term Debt
  2400 - Long-term Debt
3000s - Equity
4000s - Revenue
5000s - COGS
6000s - Operating Expenses
7000s - Other Income/Expense
8000s - Tax
```

## Data Validation Checks

After extraction, verify:
1. Balance Sheet balances: Assets = Liabilities + Equity
2. Income Statement: Revenue - Expenses = Net Income
3. Cash Flow: Beginning Cash + Net CF = Ending Cash
4. Trial Balance: Total Debits = Total Credits
5. No missing periods or accounts
6. Numbers match PDF source (spot check 5-10 values)

## Output Format

Excel file with these sheets:
- **Raw Extract**: Exact data as extracted
- **Mapped Data**: Accounts mapped to standard categories
- **Validation**: Checks and reconciliation
- **Source Notes**: Page references and extraction confidence

## Critical Rules

- ALWAYS preserve original formatting/sign conventions
- ALWAYS flag low-confidence extractions (OCR quality < 90%)
- ALWAYS include source page reference for each data point
- If amounts don't balance, flag but don't adjust
- Parentheses = negative numbers
- Watch for footnote numbers mixed into financial data
-e 

---

# Standard Chart of Accounts Mapping for FDD

## Balance Sheet Accounts

### Assets
| Code | Standard Name | Common Variations |
|------|--------------|-------------------|
| 1100 | Cash & Cash Equivalents | Cash, Bank, Petty Cash, Money Market |
| 1110 | Restricted Cash | Escrow, Collateral Deposits |
| 1200 | Accounts Receivable (Gross) | Trade Receivables, AR, Debtors |
| 1210 | Allowance for Doubtful Accounts | Bad Debt Reserve, Provision |
| 1220 | Notes Receivable | Loans Receivable, Employee Advances |
| 1300 | Inventory - Raw Materials | Raw Material, Components |
| 1310 | Inventory - WIP | Work in Progress, In-Process |
| 1320 | Inventory - Finished Goods | Merchandise, Product Inventory |
| 1330 | Inventory Reserve | Obsolescence Reserve, Write-down |
| 1400 | Prepaid Expenses | Prepaid Insurance, Prepaid Rent |
| 1410 | Other Current Assets | Deposits, Short-term Receivables |
| 1500 | Property, Plant & Equipment | Fixed Assets, Tangible Assets |
| 1510 | Accumulated Depreciation | AD, Contra Asset |
| 1600 | Goodwill | Acquisition Goodwill |
| 1610 | Intangible Assets | Patents, Trademarks, Customer Lists |
| 1620 | Accumulated Amortization | IA Amortization |
| 1700 | Right-of-Use Assets | Operating Lease Asset, ROU |
| 1800 | Other Non-Current Assets | LT Investments, Deferred Tax Asset |

### Liabilities
| Code | Standard Name | Common Variations |
|------|--------------|-------------------|
| 2100 | Accounts Payable | Trade Payables, AP, Creditors |
| 2110 | Accrued Expenses | Accrued Liabilities, Accruals |
| 2120 | Accrued Payroll | Wages Payable, Salary Accrual |
| 2130 | Accrued Benefits | Pension, Health Insurance Payable |
| 2200 | Deferred Revenue | Unearned Revenue, Contract Liability |
| 2210 | Customer Deposits | Advance Payments |
| 2300 | Short-term Debt | Line of Credit, CPLTD, Revolver |
| 2310 | Current Lease Obligations | Current Portion Lease Liability |
| 2400 | Long-term Debt | Term Loan, Notes Payable, Bonds |
| 2410 | Non-current Lease Obligations | LT Lease Liability |
| 2500 | Other Non-Current Liabilities | Deferred Tax Liability, Contingencies |

### Equity
| Code | Standard Name | Common Variations |
|------|--------------|-------------------|
| 3100 | Common Stock | Share Capital, Paid-in Capital |
| 3200 | Additional Paid-in Capital | APIC, Share Premium |
| 3300 | Retained Earnings | Accumulated Profit/Loss |
| 3400 | Treasury Stock | Repurchased Shares |
| 3500 | Other Comprehensive Income | AOCI, Currency Translation |

## Income Statement Accounts

### Revenue
| Code | Standard Name | Common Variations |
|------|--------------|-------------------|
| 4100 | Product Revenue | Sales, Merchandise Revenue |
| 4200 | Service Revenue | Consulting Revenue, Fee Income |
| 4300 | Subscription Revenue | SaaS Revenue, Recurring Revenue |
| 4400 | License Revenue | Royalty Income, IP Revenue |
| 4900 | Other Revenue | Miscellaneous Income |

### Cost of Goods Sold
| Code | Standard Name | Common Variations |
|------|--------------|-------------------|
| 5100 | Direct Materials | Raw Material Cost, Components |
| 5200 | Direct Labor | Production Wages, Manufacturing Labor |
| 5300 | Manufacturing Overhead | Factory Overhead, Production Costs |
| 5400 | Cost of Services | Direct Service Costs |
| 5500 | Depreciation (COGS) | Production Depreciation |

### Operating Expenses
| Code | Standard Name | Common Variations |
|------|--------------|-------------------|
| 6100 | Sales & Marketing | Advertising, Sales Commission |
| 6200 | General & Administrative | G&A, Corporate Overhead |
| 6300 | Research & Development | R&D, Product Development |
| 6400 | Depreciation & Amortization | D&A (below gross profit) |
| 6500 | Rent & Occupancy | Facility Costs, Office Rent |
| 6600 | Professional Fees | Legal, Accounting, Consulting |
| 6700 | Insurance | General Insurance, D&O |
| 6800 | IT & Technology | Software, Cloud, Hardware |
| 6900 | Other Operating Expenses | Miscellaneous, Sundry |

### Other Income/Expense
| Code | Standard Name | Common Variations |
|------|--------------|-------------------|
| 7100 | Interest Income | Investment Income, Bank Interest |
| 7200 | Interest Expense | Loan Interest, Debt Service |
| 7300 | Gain/Loss on FX | Currency Gain/Loss |
| 7400 | Gain/Loss on Asset Sale | Disposal Gain/Loss |
| 7500 | Other Non-Operating | Miscellaneous Non-Operating |

### Tax
| Code | Standard Name | Common Variations |
|------|--------------|-------------------|
| 8100 | Income Tax Expense - Current | Current Tax Provision |
| 8200 | Income Tax Expense - Deferred | DTA/DTL Movement |

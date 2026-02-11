import type { GlossaryTerm } from "@/types/help";

export const GLOSSARY: GlossaryTerm[] = [
  // FDD Terms
  {
    term: "Quality of Earnings",
    abbreviation: "QoE",
    definition:
      "Analysis that adjusts reported earnings to reflect sustainable, recurring income by removing non-recurring, non-operating, and owner-related items.",
    module: "fdd",
  },
  {
    term: "Net Working Capital",
    abbreviation: "NWC",
    definition:
      "Current assets minus current liabilities, representing the capital needed for day-to-day operations. Used to calculate purchase price adjustments.",
    module: "fdd",
  },
  {
    term: "Net Debt",
    abbreviation: null,
    definition:
      "Total financial debt minus cash and cash equivalents. A key component in enterprise-to-equity value bridge calculations.",
    module: "fdd",
  },
  {
    term: "EBITDA",
    abbreviation: "EBITDA",
    definition:
      "Earnings Before Interest, Taxes, Depreciation, and Amortization. A proxy for operating cash flow used in valuation.",
    module: "fdd",
  },
  {
    term: "Virtual Data Room",
    abbreviation: "VDR",
    definition:
      "Secure online repository for sharing confidential documents during due diligence processes.",
    module: "fdd",
  },
  {
    term: "Locked Box",
    abbreviation: null,
    definition:
      "A pricing mechanism where the purchase price is fixed at signing based on a set of locked accounts, with protections against value leakage.",
    module: "fdd",
  },
  {
    term: "Completion Accounts",
    abbreviation: null,
    definition:
      "A pricing mechanism where the purchase price is adjusted post-closing based on actual balance sheet figures at completion date.",
    module: "fdd",
  },
  {
    term: "Trial Balance",
    abbreviation: "TB",
    definition:
      "A list of all general ledger accounts and their balances at a specific date, used to verify accounting accuracy.",
    module: "fdd",
  },
  {
    term: "General Ledger",
    abbreviation: "GL",
    definition:
      "The complete record of all financial transactions for a company, forming the basis for financial statements.",
    module: "fdd",
  },

  // KIIS Terms
  {
    term: "DART",
    abbreviation: "DART",
    definition:
      "Data Analysis, Retrieval and Transfer System — Korea's electronic disclosure system operated by FSS for corporate filings.",
    module: "kiis",
  },
  {
    term: "KOFIA",
    abbreviation: "KOFIA",
    definition:
      "Korea Financial Investment Association — industry body that regulates and provides data on Korean financial investment products.",
    module: "kiis",
  },
  {
    term: "Corp Code",
    abbreviation: null,
    definition:
      "Unique identifier assigned to each corporation in the DART system, used for API queries and cross-referencing.",
    module: "kiis",
  },
  {
    term: "Reputation Score",
    abbreviation: null,
    definition:
      "Composite score combining trend, news sentiment, and financial performance to assess corporate reputation risk.",
    module: "kiis",
  },
  {
    term: "Entity Resolution",
    abbreviation: null,
    definition:
      "Process of matching and deduplicating company records across different data sources using name similarity and aliases.",
    module: "kiis",
  },
  {
    term: "Survival Status",
    abbreviation: null,
    definition:
      "Portfolio monitoring status indicating whether an invested company is active, dissolved, audit-missing, or unicorn.",
    module: "kiis",
  },
  {
    term: "Sanctions Screening",
    abbreviation: null,
    definition:
      "Check against international sanctions lists (OFAC, EU, UN) to identify restricted entities or individuals.",
    module: "kiis",
  },

  // IM Terms
  {
    term: "Investment Memorandum",
    abbreviation: "IM",
    definition:
      "Comprehensive document summarizing a company's business, financials, and investment thesis for potential investors.",
    module: "im",
  },
  {
    term: "IM Style",
    abbreviation: null,
    definition:
      "Template variant for the generated Investment Memorandum: TITAN (concise), COVENANT (detailed), FULL (comprehensive), or CUSTOM.",
    module: "im",
  },

  // General
  {
    term: "Role-Based Access Control",
    abbreviation: "RBAC",
    definition:
      "Security model that restricts system access based on user roles: Admin, Manager, Analyst, Viewer.",
    module: "general",
  },
  {
    term: "Activity Log",
    abbreviation: null,
    definition:
      "Audit trail recording all user actions across the platform for compliance and accountability.",
    module: "general",
  },
];

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

  // MA Terms
  {
    term: "Transaction Phase",
    abbreviation: null,
    definition:
      "One of seven stages in the M&A workflow: Engagement, Preparation, Marketing, Bidding/DD, Negotiation, Closing, and Post-Close. Each phase has prerequisites that must be met before advancing.",
    module: "ma",
  },
  {
    term: "Non-Disclosure Agreement",
    abbreviation: "NDA",
    definition:
      "Confidentiality agreement signed by potential buyers before receiving detailed deal information. Can be one-way or mutual.",
    module: "ma",
  },
  {
    term: "Indication of Interest",
    abbreviation: "IOI",
    definition:
      "A non-binding preliminary bid submitted by a potential buyer expressing interest in a transaction, typically including a valuation range.",
    module: "ma",
  },
  {
    term: "Letter of Intent",
    abbreviation: "LOI",
    definition:
      "A semi-binding document outlining the principal terms and conditions of a proposed transaction, submitted after due diligence.",
    module: "ma",
  },
  {
    term: "Share Purchase Agreement",
    abbreviation: "SPA",
    definition:
      "The definitive legal agreement governing the sale and purchase of shares in a target company, including representations, warranties, and indemnities.",
    module: "ma",
  },
  {
    term: "Earnout",
    abbreviation: null,
    definition:
      "A contingent payment mechanism where a portion of the purchase price is paid based on the target company achieving specified financial or operational milestones post-closing.",
    module: "ma",
  },
  {
    term: "Post-Merger Integration",
    abbreviation: "PMI",
    definition:
      "The process of combining two organizations after a transaction closes, including integration planning, Day One readiness, synergy realization, and cultural alignment.",
    module: "ma",
  },
  {
    term: "Condition Precedent",
    abbreviation: "CP",
    definition:
      "A condition that must be satisfied or waived before a transaction can close, such as regulatory approvals, board consents, or financing confirmations.",
    module: "ma",
  },
  {
    term: "Confidential Information Memorandum",
    abbreviation: "CIM",
    definition:
      "A detailed document describing the target company's business, financials, and investment highlights, distributed to potential buyers after NDA execution.",
    module: "ma",
  },
  {
    term: "Due Diligence Checklist",
    abbreviation: null,
    definition:
      "A structured list of items to be investigated during due diligence, organized by workstream (FDD, LDD, TDD) with status tracking for each item.",
    module: "ma",
  },

  // Docs Terms
  {
    term: "Teaser Memorandum",
    abbreviation: "TM",
    definition:
      "A brief, anonymous marketing document providing a high-level overview of an investment opportunity to gauge initial buyer interest before NDA execution.",
    module: "docs",
  },
  {
    term: "Legal Due Diligence Report",
    abbreviation: "LDD",
    definition:
      "A comprehensive legal review covering corporate structure, contracts, permits, litigation, intellectual property, labor, and environmental matters of the target company.",
    module: "docs",
  },
  {
    term: "Ralph Loop",
    abbreviation: null,
    definition:
      "AI-powered document generation and review system that automatically drafts deal documents, validates content with vision-based quality gates, and learns from feedback patterns.",
    module: "docs",
  },
  {
    term: "Deal Document Studio",
    abbreviation: null,
    definition:
      "Integrated document management hub for creating and managing all deal-related documents: marketing materials (TM/IM), legal documents (MOU/contracts), DD reports (FDD/LDD), and closing checklists.",
    module: "docs",
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
  {
    term: "Webhook",
    abbreviation: null,
    definition:
      "An HTTP callback that sends real-time notifications to external systems when specific events occur in the platform, such as deal status changes or document generation completions.",
    module: "general",
  },
  {
    term: "Cross-Module Analytics",
    abbreviation: null,
    definition:
      "A unified dashboard aggregating KPIs and trend charts from all platform modules (MA, FDD, KIIS, IM), enabling managers to monitor overall deal pipeline health and performance.",
    module: "general",
  },
  {
    term: "Module Switcher",
    abbreviation: null,
    definition:
      "Sidebar navigation control that allows quick switching between the four core modules: M&A Deals, VDR, Deal Doc Studio, and KIIS.",
    module: "general",
  },
];

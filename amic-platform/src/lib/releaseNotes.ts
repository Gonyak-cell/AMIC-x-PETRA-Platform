import type { ReleaseNote } from "@/types/help";
import { APP_VERSION } from "@/lib/app-version";

/** 현재 앱 버전 — package.json에서 빌드 시 주입 */
export const CURRENT_VERSION = APP_VERSION;

export const RELEASE_NOTES: ReleaseNote[] = [
  {
    version: "0.10.0",
    date: "2026-02-25",
    highlights: [
      "Team page with member profiles",
      "Structured JSON logging across all backends",
      "CLIENT role with deal assignment access control",
      "Help Center content refresh",
    ],
    changes: [
      {
        type: "feature",
        description:
          "Added Team page (/team) with member photos and role badges",
      },
      {
        type: "feature",
        description:
          "Implemented JSON structured logging with rotating file handlers across all 4 backends",
      },
      {
        type: "feature",
        description:
          "Added CLIENT user role with restricted access to assigned MA transactions only",
      },
      {
        type: "feature",
        description:
          "Added deal-client assignment management for controlled external access",
      },
      {
        type: "improvement",
        description:
          "Updated Help Center with comprehensive module guides, MA/Docs glossary terms, and complete release history",
      },
    ],
  },
  {
    version: "0.9.0",
    date: "2026-02-24",
    highlights: [
      "MA Phase 3–5: Legal, Marketing, VDR, Meeting Logs, Permits, Risks & Compliance",
      "DD workstream restructure (FDD/LDD/TDD hierarchy)",
      "Ralph Loop AI document generation",
    ],
    changes: [
      {
        type: "feature",
        description:
          "Added legal document management with contract markups and clause suggestions",
      },
      {
        type: "feature",
        description:
          "Added marketing materials (TM/IM) generation and management",
      },
      {
        type: "feature",
        description:
          "Added VDR (Virtual Data Room) with folder hierarchy and document upload",
      },
      {
        type: "feature",
        description:
          "Added meeting logs with attendees, action items, and buyer reaction tracking",
      },
      {
        type: "feature",
        description:
          "Added permit analysis with knowledge base and regulatory filing tracking",
      },
      {
        type: "feature",
        description:
          "Added risk register and compliance item management with severity/likelihood matrix",
      },
      {
        type: "feature",
        description:
          "Restructured DD checklist with FDD/LDD/TDD workstream hierarchy",
      },
      {
        type: "feature",
        description:
          "Implemented Ralph Loop AI: core engine, LLM client, vision gate, and learning patterns (295 tests)",
      },
      {
        type: "improvement",
        description:
          "Added notes and approvals system for transaction-level collaboration",
      },
    ],
  },
  {
    version: "0.8.0",
    date: "2026-02-23",
    highlights: [
      "Deal Document Studio integration",
      "InlineSelect UX unification",
      "IM/Docs DELETE endpoints",
    ],
    changes: [
      {
        type: "feature",
        description:
          "Implemented Deal Document Studio (/docs) with Marketing, Legal, DD, and Checklist sections",
      },
      {
        type: "feature",
        description:
          "Added document deletion endpoints for IM and Docs modules",
      },
      {
        type: "feature",
        description:
          "Integrated 26 TM section renderers for Investment Memorandum generation",
      },
      {
        type: "improvement",
        description:
          "Unified table cell Select to InlineSelect across 5 locations in MA module",
      },
      {
        type: "improvement",
        description:
          "Standardized filter chip UI across 3 locations in MA pipeline",
      },
      {
        type: "fix",
        description:
          "Fixed IM Documents 500 error caused by missing user title migration",
      },
    ],
  },
  {
    version: "0.7.0",
    date: "2026-02-22",
    highlights: [
      "GSAP motion system for page transitions",
      "GP-centric search for KIIS funds",
      "IM corp_code optional migration",
    ],
    changes: [
      {
        type: "feature",
        description:
          "Added GSAP-powered page transitions, scroll reveal animations, and micro-interactions with accessibility support",
      },
      {
        type: "feature",
        description:
          "Redesigned KIIS fund search to GP-centric model with GP-Company cross-links and responsive layout",
      },
      {
        type: "feature",
        description:
          "Made IM corp_code selection optional with 3 data source types and Excel upload support",
      },
      {
        type: "feature",
        description:
          "Added private fund GP data source research with 9 sources and 3-phase strategy",
      },
      {
        type: "improvement",
        description:
          "Browser E2E verification: Playwright 16 pages + MA 15 tabs, 31 screenshots",
      },
    ],
  },
  {
    version: "0.6.0",
    date: "2026-02-19",
    highlights: [
      "M&A Deals module with 7-phase workflow",
      "deal-mgmt backend (47 files)",
      "DD Checklist and Closing management",
    ],
    changes: [
      {
        type: "feature",
        description:
          "Implemented M&A transaction pipeline with 7-phase workflow (Engagement → Post-Close)",
      },
      {
        type: "feature",
        description:
          "Added deal-mgmt FastAPI backend: transactions, buyers, NDAs, bids, contracts, closing, PMI, earnout",
      },
      {
        type: "feature",
        description:
          "Added DD Checklist with workstream-based organization and status tracking",
      },
      {
        type: "feature",
        description:
          "Added closing conditions management with standard 15-item auto-generation",
      },
      {
        type: "feature",
        description:
          "Added transaction workspace with tabbed navigation and phase-aware visibility",
      },
      {
        type: "feature",
        description:
          "Added workflow engine with phase prerequisites and advancement validation",
      },
      {
        type: "feature",
        description:
          "Full Docker integration for deal-mgmt service (port 8003, PostgreSQL 5436)",
      },
      {
        type: "fix",
        description:
          "Fixed JWT secret unification across all backends in production",
      },
    ],
  },
  {
    version: "0.5.0",
    date: "2026-02-11",
    highlights: [
      "Cross-module Analytics Dashboard",
      "Help Center with glossary and keyboard shortcuts",
      "Data Export Hub and Calendar/Timeline views",
      "E2E testing with Playwright",
    ],
    changes: [
      {
        type: "feature",
        description:
          "Added cross-module analytics dashboard with KPI aggregation and trend charts",
      },
      {
        type: "feature",
        description:
          "Added Help Center with domain glossary, keyboard shortcuts, and release notes",
      },
      {
        type: "feature",
        description:
          "Added Data Export Hub for unified export history and batch download",
      },
      {
        type: "feature",
        description: "Added Calendar/Timeline view with Gantt and monthly grid",
      },
      {
        type: "feature",
        description: "Added Playwright E2E testing infrastructure",
      },
    ],
  },
  {
    version: "0.4.0",
    date: "2026-02-01",
    highlights: [
      "Activity Log and audit trail",
      "Team Collaboration with comments",
      "Global search and favorites",
    ],
    changes: [
      {
        type: "feature",
        description:
          "Added Activity Log page with timeline and table views for compliance",
      },
      {
        type: "feature",
        description:
          "Added team collaboration features: comment threads and team assignment",
      },
      {
        type: "feature",
        description: "Added global search (Ctrl+K) with cross-module results",
      },
      {
        type: "feature",
        description: "Added favorites and recent items in sidebar",
      },
      {
        type: "feature",
        description: "Added notification center with polling updates",
      },
    ],
  },
  {
    version: "0.3.0",
    date: "2026-01-20",
    highlights: [
      "Dashboard and admin panel",
      "User management and profile settings",
    ],
    changes: [
      {
        type: "feature",
        description:
          "Added portal dashboard with cross-module KPIs and module health check",
      },
      {
        type: "feature",
        description: "Added admin user management with role-based permissions",
      },
      {
        type: "feature",
        description: "Added user profile and preference settings",
      },
    ],
  },
  {
    version: "0.2.0",
    date: "2026-01-10",
    highlights: [
      "KIIS module with 17 pages",
      "IM module with document generation",
    ],
    changes: [
      {
        type: "feature",
        description:
          "Implemented KIIS module: companies, funds, REITs, news, deals, portfolio, managers, entities, disclosures, watchlist",
      },
      {
        type: "feature",
        description:
          "Implemented IM module: document list, creation wizard, detail view, templates",
      },
    ],
  },
  {
    version: "0.1.0",
    date: "2025-12-20",
    highlights: [
      "Platform foundation with FDD module",
      "Authentication and routing",
    ],
    changes: [
      {
        type: "feature",
        description:
          "Initial platform setup: React 19, Vite 6, TanStack Query v5, Tailwind CSS 3",
      },
      {
        type: "feature",
        description:
          "Implemented FDD module: deal management, QoE analysis, NWC, Net Debt, issues, reports",
      },
      {
        type: "feature",
        description:
          "JWT authentication with auto-refresh and role-based access control",
      },
    ],
  },
];

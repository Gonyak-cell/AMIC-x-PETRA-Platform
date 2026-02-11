import type { ReleaseNote } from "@/types/help";

export const RELEASE_NOTES: ReleaseNote[] = [
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
        description:
          "Added Calendar/Timeline view with Gantt and monthly grid",
      },
      {
        type: "feature",
        description:
          "Added Playwright E2E testing infrastructure",
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
        description:
          "Added global search (Ctrl+K) with cross-module results",
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
        description:
          "Added admin user management with role-based permissions",
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

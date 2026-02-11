import { useMemo } from "react";
import { useQueries } from "@tanstack/react-query";
import api from "@/api/client";
import { kiisApi } from "@/api/kiisClient";
import { imApi } from "@/api/imClient";
import type { Deal } from "@/modules/fdd/types/deal";
import type { DealItem } from "@/modules/kiis/types/deal";
import type { Document } from "@/modules/im/types/document";
import type { CalendarEvent, GanttItem, CalendarFilter } from "@/types/calendar";

export interface CalendarErrors {
  fdd: boolean;
  kiis: boolean;
  im: boolean;
}

export function useCalendarEvents(filter: CalendarFilter) {
  const results = useQueries({
    queries: [
      {
        queryKey: ["calendar", "fdd-deals"],
        queryFn: async () => {
          const { data } = await api.get<Deal[]>("/deals");
          return data;
        },
        staleTime: 60_000,
        enabled: filter.modules.includes("fdd"),
      },
      {
        queryKey: ["calendar", "im-documents"],
        queryFn: async () => {
          const { data } = await imApi.get<{ items: Document[]; total: number }>(
            "/documents",
          );
          return data.items;
        },
        staleTime: 60_000,
        enabled: filter.modules.includes("im"),
      },
      {
        queryKey: ["calendar", "kiis-deals"],
        queryFn: async () => {
          try {
            const { data } = await kiisApi.get<{ items: DealItem[] }>("/deals", {
              params: { size: 200 },
            });
            return data.items;
          } catch {
            // KIIS may not have a /deals listing endpoint
            return [];
          }
        },
        staleTime: 60_000,
        enabled: filter.modules.includes("kiis"),
      },
    ],
  });

  const [dealsQuery, docsQuery, kiisDealsQuery] = results;
  const isLoading = results.some((r) => r.isLoading);

  const errors: CalendarErrors = {
    fdd: dealsQuery.isError,
    kiis: kiisDealsQuery.isError,
    im: docsQuery.isError,
  };

  const events = useMemo<CalendarEvent[]>(() => {
    const items: CalendarEvent[] = [];

    // FDD deal events
    if (dealsQuery.data) {
      for (const deal of dealsQuery.data) {
        if (deal.period_start) {
          items.push({
            id: `fdd-start-${deal.id}`,
            module: "fdd",
            type: "deal_start",
            title: `${deal.name} — Period Start`,
            date: deal.period_start,
            entityId: deal.id,
            entityPath: `/fdd/deals/${deal.id}`,
          });
        }
        if (deal.period_end) {
          items.push({
            id: `fdd-end-${deal.id}`,
            module: "fdd",
            type: "deal_end",
            title: `${deal.name} — Period End`,
            date: deal.period_end,
            entityId: deal.id,
            entityPath: `/fdd/deals/${deal.id}`,
          });
        }
        if (deal.reference_date) {
          items.push({
            id: `fdd-ref-${deal.id}`,
            module: "fdd",
            type: "deal_reference",
            title: `${deal.name} — Reference Date`,
            date: deal.reference_date,
            entityId: deal.id,
            entityPath: `/fdd/deals/${deal.id}`,
          });
        }
        items.push({
          id: `fdd-created-${deal.id}`,
          module: "fdd",
          type: "deal_created",
          title: `${deal.name} — Created`,
          date: deal.created_at.slice(0, 10),
          entityId: deal.id,
          entityPath: `/fdd/deals/${deal.id}`,
        });
      }
    }

    // IM document events
    if (docsQuery.data) {
      for (const doc of docsQuery.data) {
        items.push({
          id: `im-created-${doc.id}`,
          module: "im",
          type: "document_created",
          title: `${doc.project_name ?? doc.company_name} — Created`,
          date: doc.created_at.slice(0, 10),
          entityId: doc.id,
          entityPath: `/im/documents/${doc.id}`,
        });
        if (doc.completed_at) {
          items.push({
            id: `im-done-${doc.id}`,
            module: "im",
            type: "document_completed",
            title: `${doc.project_name ?? doc.company_name} — Completed`,
            date: doc.completed_at.slice(0, 10),
            entityId: doc.id,
            entityPath: `/im/documents/${doc.id}`,
          });
        }
      }
    }

    // KIIS deal events
    if (kiisDealsQuery.data) {
      for (const deal of kiisDealsQuery.data) {
        if (deal.deal_date) {
          items.push({
            id: `kiis-deal-${deal.id}`,
            module: "kiis",
            type: "audit_date",
            title: `${deal.target_company} — Deal${deal.round_stage ? ` (${deal.round_stage})` : ""}`,
            date: deal.deal_date,
            entityId: String(deal.id),
            entityPath: deal.target_company_id
              ? `/kiis/companies/${deal.target_company_id}`
              : "/kiis",
          });
        }
      }
    }

    return items;
  }, [dealsQuery.data, docsQuery.data, kiisDealsQuery.data]);

  const ganttItems = useMemo<GanttItem[]>(() => {
    const items: GanttItem[] = [];

    if (dealsQuery.data) {
      for (const deal of dealsQuery.data) {
        if (deal.period_start && deal.period_end) {
          items.push({
            id: `gantt-fdd-${deal.id}`,
            label: deal.name,
            module: "fdd",
            startDate: deal.period_start,
            endDate: deal.period_end,
            entityPath: `/fdd/deals/${deal.id}`,
          });
        }
      }
    }

    if (docsQuery.data) {
      for (const doc of docsQuery.data) {
        if (doc.completed_at) {
          items.push({
            id: `gantt-im-${doc.id}`,
            label: doc.project_name ?? doc.company_name,
            module: "im",
            startDate: doc.created_at.slice(0, 10),
            endDate: doc.completed_at.slice(0, 10),
            entityPath: `/im/documents/${doc.id}`,
            progress: 100,
          });
        } else {
          items.push({
            id: `gantt-im-${doc.id}`,
            label: doc.project_name ?? doc.company_name,
            module: "im",
            startDate: doc.created_at.slice(0, 10),
            endDate: new Date().toISOString().slice(0, 10),
            entityPath: `/im/documents/${doc.id}`,
            progress: doc.progress_pct,
          });
        }
      }
    }

    // KIIS deals as single-day milestones in Gantt
    if (kiisDealsQuery.data) {
      for (const deal of kiisDealsQuery.data) {
        if (deal.deal_date) {
          items.push({
            id: `gantt-kiis-${deal.id}`,
            label: `${deal.target_company}${deal.round_stage ? ` (${deal.round_stage})` : ""}`,
            module: "kiis",
            startDate: deal.deal_date,
            endDate: deal.deal_date,
            entityPath: deal.target_company_id
              ? `/kiis/companies/${deal.target_company_id}`
              : "/kiis",
          });
        }
      }
    }

    return items.sort((a, b) => a.startDate.localeCompare(b.startDate));
  }, [dealsQuery.data, docsQuery.data, kiisDealsQuery.data]);

  return { events, ganttItems, isLoading, errors };
}

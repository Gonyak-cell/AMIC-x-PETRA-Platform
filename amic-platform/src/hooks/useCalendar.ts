import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { maApi } from "@/api/maClient";
import { toArray, safeStr } from "@/api/safe-parse";
import { PHASE_CONFIG } from "@/modules/ma/constants";
import type { Transaction } from "@/modules/ma/types/transaction";
import type { CalendarEvent, GanttItem, CalendarFilter } from "@/types/calendar";

export interface CalendarErrors {
  ma: boolean;
}

const PHASE_ORDER: Record<string, number> = {};
for (const p of PHASE_CONFIG) {
  PHASE_ORDER[p.phase] = p.order;
}

const PHASE_LABEL: Record<string, string> = {};
for (const p of PHASE_CONFIG) {
  PHASE_LABEL[p.phase] = p.label;
}

export function useCalendarEvents(_filter: CalendarFilter) {
  const txnQuery = useQuery({
    queryKey: ["calendar", "ma-transactions"],
    queryFn: async () => {
      const { data } = await maApi.get("/transactions", {
        params: { limit: 100 },
      });
      const raw = (data as { items?: unknown[] })?.items ?? data;
      return toArray<Transaction>(raw);
    },
    staleTime: 60_000,
  });

  const isLoading = txnQuery.isLoading;

  const errors: CalendarErrors = {
    ma: txnQuery.isError,
  };

  const events = useMemo<CalendarEvent[]>(() => {
    const items: CalendarEvent[] = [];
    if (!txnQuery.data) return items;

    for (const txn of txnQuery.data) {
      const label = txn.code_name || txn.target_company_name || txn.name;

      const phaseLbl = PHASE_LABEL[txn.phase] ?? txn.phase;
      const phaseOrd = PHASE_ORDER[txn.phase] ?? 1;
      const phaseFields = {
        phase: txn.phase,
        phaseLabel: phaseLbl,
        phaseOrder: phaseOrd,
      };

      // 거래 생성일
      items.push({
        id: `ma-created-${txn.id}`,
        module: "ma",
        type: "transaction_created",
        title: `${label} — 거래 생성`,
        date: safeStr(txn.created_at).slice(0, 10),
        entityId: txn.id,
        entityPath: `/ma/transactions/${txn.id}`,
        ...phaseFields,
      });

      // 목표 종결일
      if (txn.target_close_date) {
        items.push({
          id: `ma-close-${txn.id}`,
          module: "ma",
          type: "target_close",
          title: `${label} — 목표 종결일`,
          date: txn.target_close_date,
          entityId: txn.id,
          entityPath: `/ma/transactions/${txn.id}`,
          ...phaseFields,
        });
      }

      // 현재 단계
      items.push({
        id: `ma-phase-${txn.id}`,
        module: "ma",
        type: "phase_current",
        title: `${label} — ${phaseLbl} 단계`,
        date: safeStr(txn.updated_at).slice(0, 10),
        entityId: txn.id,
        entityPath: `/ma/transactions/${txn.id}`,
        ...phaseFields,
      });
    }

    return items;
  }, [txnQuery.data]);

  const ganttItems = useMemo<GanttItem[]>(() => {
    const items: GanttItem[] = [];
    if (!txnQuery.data) return items;

    const today = new Date().toISOString().slice(0, 10);

    for (const txn of txnQuery.data) {
      const label = txn.code_name || txn.target_company_name || txn.name;
      const startDate = safeStr(txn.created_at).slice(0, 10);
      const endDate = txn.target_close_date ?? today;
      const order = PHASE_ORDER[txn.phase] ?? 1;
      const progress = Math.round((order / 7) * 100);

      items.push({
        id: `gantt-ma-${txn.id}`,
        label: `${label} (${PHASE_LABEL[txn.phase] ?? txn.phase})`,
        module: "ma",
        startDate,
        endDate,
        entityPath: `/ma/transactions/${txn.id}`,
        progress,
      });
    }

    return items.sort((a, b) => a.startDate.localeCompare(b.startDate));
  }, [txnQuery.data]);

  return { events, ganttItems, isLoading, errors };
}

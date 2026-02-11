import { useQuery } from "@tanstack/react-query";
import api from "@/api/client";
import type {
  ActivityLogFilter,
  PaginatedActivityLog,
} from "@/types/activity";

export function useActivityLog(filters: ActivityLogFilter = {}) {
  return useQuery<PaginatedActivityLog>({
    queryKey: ["admin", "activity", filters],
    queryFn: async () => {
      try {
        const { data } = await api.get<PaginatedActivityLog>("/audit/logs", {
          params: filters,
        });
        return data;
      } catch {
        // Backend not implemented yet — return empty result
        return { items: [], total: 0, page: 1, size: 20 };
      }
    },
    staleTime: 30_000,
  });
}

export function useActivityExport() {
  return async (filters: ActivityLogFilter) => {
    try {
      const { data } = await api.get("/audit/logs/export", {
        params: filters,
        responseType: "blob",
      });

      const blob = new Blob([data], { type: "text/csv" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `activity-log-${new Date().toISOString().slice(0, 10)}.csv`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      // Backend not implemented — generate CSV from current data client-side
      throw new Error("Export not available: backend not implemented");
    }
  };
}

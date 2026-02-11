import { useQuery } from "@tanstack/react-query";
import api from "@/api/client";
import type {
  ActivityLogFilter,
  ActivityLogItem,
  ActivityAction,
  PaginatedActivityLog,
  RawAuditLogListResponse,
  RawAuditLogItem,
} from "@/types/activity";

const ACTION_VERBS: Record<string, string> = {
  CREATE: "Created",
  UPDATE: "Updated",
  DELETE: "Deleted",
  APPROVE: "Approved",
  LOCK: "Locked",
  LOGIN: "Logged in",
  LOGOUT: "Logged out",
  EXPORT: "Exported",
  PURGE: "Purged",
};

function buildDescription(raw: RawAuditLogItem): string {
  const verb = ACTION_VERBS[raw.action] ?? raw.action;
  if (raw.action === "LOGIN" || raw.action === "LOGOUT") return verb;
  const entity = raw.entity_type.replace(/_/g, " ");
  return `${verb} ${entity}`;
}

function transformItem(raw: RawAuditLogItem): ActivityLogItem {
  return {
    id: raw.id,
    user_id: raw.user_id ?? "",
    user_name: raw.user_email ?? raw.actor,
    module: "fdd",
    action: raw.action.toLowerCase() as ActivityAction,
    entity_type: raw.entity_type,
    entity_id: raw.entity_id,
    entity_name: null,
    description: buildDescription(raw),
    metadata:
      raw.changed_fields || raw.old_value || raw.new_value
        ? {
            changed_fields: raw.changed_fields,
            old_value: raw.old_value,
            new_value: raw.new_value,
          }
        : null,
    created_at: raw.created_at,
    ip_address: raw.ip_address,
  };
}

function buildBackendParams(filters: ActivityLogFilter) {
  const page = filters.page ?? 1;
  const size = filters.size ?? 20;
  const params: Record<string, unknown> = {
    limit: size,
    offset: (page - 1) * size,
  };
  if (filters.date_from) params.start_date = filters.date_from;
  if (filters.date_to) params.end_date = filters.date_to;
  if (filters.user_id) params.user_id = filters.user_id;
  if (filters.action) params.action = filters.action.toUpperCase();
  return { params, page, size };
}

export function useActivityLog(filters: ActivityLogFilter = {}) {
  return useQuery<PaginatedActivityLog>({
    queryKey: ["admin", "activity", filters],
    queryFn: async () => {
      const { params, page } = buildBackendParams(filters);
      const { data } = await api.get<RawAuditLogListResponse>("/audit-logs", {
        params,
      });
      return {
        items: data.items.map(transformItem),
        total: data.total,
        page,
        size: data.limit,
      };
    },
    staleTime: 30_000,
  });
}

export function useActivityExport() {
  return async (filters: ActivityLogFilter) => {
    const params: Record<string, unknown> = {};
    if (filters.date_from) params.start_date = filters.date_from;
    if (filters.date_to) params.end_date = filters.date_to;
    if (filters.user_id) params.user_id = filters.user_id;
    if (filters.action) params.action = filters.action.toUpperCase();

    const { data } = await api.get("/audit-logs/export", {
      params,
      responseType: "blob",
    });

    const blob = new Blob([data], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `activity-log-${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };
}

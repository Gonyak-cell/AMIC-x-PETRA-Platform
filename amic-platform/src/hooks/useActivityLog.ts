import { useQuery } from "@tanstack/react-query";
import api from "@/api/client";
import { kiisApi } from "@/api/kiisClient";
import { imApi } from "@/api/imClient";
import { maApi } from "@/api/maClient";
import { toArray } from "@/api/safe-parse";
import type {
  ActivityLogFilter,
  ActivityLogItem,
  ActivityAction,
  ActivityModule,
  PaginatedActivityLog,
  RawAuditLogListResponse,
  RawAuditLogItem,
} from "@/types/activity";

/* ── 상수 ─────────────────────────────────────────────── */

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
  PHASE_TRANSITION: "Phase changed",
  STATUS_CHANGE: "Status changed",
  MEMBER_ADDED: "Member added",
  MEMBER_REMOVED: "Member removed",
  SERVICE_LINKED: "Service linked",
  APPROVAL_REQUESTED: "Approval requested",
  APPROVAL_DECIDED: "Approval decided",
  NOTE_CREATED: "Note created",
  CLIENT_ASSIGNED: "Client assigned",
  CLIENT_REMOVED: "Client removed",
};

/** deal-mgmt entity_type → 세부 모듈 매핑 */
const MA_ENTITY_TO_MODULE: Record<string, ActivityModule> = {
  vdr_folder: "vdr",
  vdr_document: "vdr",
  legal_document: "docs",
  marketing_material: "docs",
  ldd_report: "docs",
};

/** 모듈 필터 → 쿼리 대상 백엔드 매핑 */
const MODULE_TO_SOURCE: Record<string, ("fdd" | "kiis" | "im" | "ma")[]> = {
  fdd: ["fdd"],
  kiis: ["kiis"],
  im: ["im"],
  ma: ["ma"],
  docs: ["ma"],
  vdr: ["ma"],
  portal: ["fdd"],
};

type BackendSource = "fdd" | "kiis" | "im" | "ma";

/* ── 헬퍼 ─────────────────────────────────────────────── */

function resolveModule(
  source: BackendSource,
  raw: RawAuditLogItem,
): ActivityModule {
  if (source !== "ma") return source;
  const type = raw.entity_type.toLowerCase();
  return MA_ENTITY_TO_MODULE[type] ?? "ma";
}

function buildDescription(raw: RawAuditLogItem): string {
  const verb = ACTION_VERBS[raw.action] ?? raw.action;
  if (raw.action === "LOGIN" || raw.action === "LOGOUT") return verb;
  const entity = raw.entity_type.replace(/_/g, " ");
  return `${verb} ${entity}`;
}

function transformItem(
  source: BackendSource,
  raw: RawAuditLogItem,
): ActivityLogItem {
  return {
    id: raw.id,
    user_id: raw.user_id ?? "",
    user_name: raw.user_email ?? raw.actor,
    module: resolveModule(source, raw),
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
  if (filters.action) params.action = filters.action.toUpperCase();
  return { params, page, size };
}

const API_MAP: Record<BackendSource, typeof api> = {
  fdd: api,
  kiis: kiisApi,
  im: imApi,
  ma: maApi,
};

const AUDIT_PATH: Record<BackendSource, string> = {
  fdd: "/audit-logs",
  kiis: "/audit/audit-logs",
  im: "/audit-logs",
  ma: "/audit-logs",
};

async function fetchAuditLogs(
  source: BackendSource,
  params: Record<string, unknown>,
): Promise<{ items: ActivityLogItem[]; total: number }> {
  try {
    const client = API_MAP[source];
    const { data } = await client.get<RawAuditLogListResponse>(
      AUDIT_PATH[source],
      { params },
    );
    const items = toArray<RawAuditLogItem>(data?.items).map((raw) =>
      transformItem(source, raw),
    );
    return { items, total: data?.total ?? 0 };
  } catch {
    // 백엔드 미접근 시 빈 결과 반환
    return { items: [], total: 0 };
  }
}

/* ── Hooks ─────────────────────────────────────────────── */

export function useActivityLog(filters: ActivityLogFilter = {}) {
  return useQuery<PaginatedActivityLog>({
    queryKey: ["admin", "activity", filters],
    queryFn: async () => {
      const { params, page, size } = buildBackendParams(filters);

      // 모듈 필터에 따라 조회 대상 백엔드 결정
      let sources: BackendSource[];
      if (filters.module) {
        sources =
          MODULE_TO_SOURCE[filters.module] ??
          (["fdd", "kiis", "im", "ma"] as BackendSource[]);
      } else {
        sources = ["fdd", "kiis", "im", "ma"];
      }

      // 병렬 조회
      const results = await Promise.all(
        sources.map((src) => fetchAuditLogs(src, params)),
      );

      // 병합 + 정렬
      const allItems = results.flatMap((r) => r.items);
      allItems.sort(
        (a, b) =>
          new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
      );

      // 모듈 세부 필터 (docs/vdr는 ma 백엔드에서 오지만 entity_type으로 분리)
      const filtered = filters.module
        ? allItems.filter((item) => item.module === filters.module)
        : allItems;

      const totalSum = results.reduce((sum, r) => sum + r.total, 0);

      return {
        items: filtered.slice(0, size),
        total: totalSum,
        page,
        size,
      };
    },
    staleTime: 30_000,
  });
}

export function useActivityExport() {
  return async (filters: ActivityLogFilter) => {
    // 4개 백엔드 병렬 조회 → 클라이언트 CSV 생성 (모든 모듈 데이터 포함)
    const { params } = buildBackendParams({ ...filters, size: 10000 });
    const results = await Promise.all(
      (["fdd", "kiis", "im", "ma"] as BackendSource[]).map((src) =>
        fetchAuditLogs(src, params),
      ),
    );
    const allItems = results
      .flatMap((r) => r.items)
      .sort(
        (a, b) =>
          new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
      );

    const header = "Timestamp,User,Module,Action,Entity Type,Description\n";
    const rows = allItems
      .map((i) =>
        [
          i.created_at,
          i.user_name,
          i.module,
          i.action,
          i.entity_type,
          i.description,
        ]
          .map((v) => `"${String(v ?? "").replace(/"/g, '""')}"`)
          .join(","),
      )
      .join("\n");

    const blob = new Blob([header + rows], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `activity-log-${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };
}

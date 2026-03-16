/** 홈 대시보드 — 최근 프로젝트 진행상황 위젯 */

import { useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { FolderKanban, Inbox } from "lucide-react";
import { Card, Badge } from "@/components/ui";
import { useTransactions } from "@/modules/ma/hooks/useTransactions";
import { PHASE_CONFIG } from "@/modules/ma/constants";
import type { TransactionStatus } from "@/modules/ma/types/transaction";
import { cn } from "@/lib/cn";

const PHASE_LABEL: Record<string, string> = {};
for (const p of PHASE_CONFIG) {
  PHASE_LABEL[p.phase] = p.label;
}

const STATUS_BADGE: Record<
  TransactionStatus,
  {
    label: string;
    variant: "success" | "warning" | "info" | "neutral" | "error";
  }
> = {
  ACTIVE: { label: "진행중", variant: "success" },
  ON_HOLD: { label: "보류", variant: "warning" },
  DRAFT: { label: "초안", variant: "neutral" },
  COMPLETED: { label: "완료", variant: "info" },
  TERMINATED: { label: "종결", variant: "error" },
};

/** 포함 대상 status (COMPLETED, TERMINATED 제외) */
const VISIBLE_STATUSES = new Set<TransactionStatus>([
  "ACTIVE",
  "ON_HOLD",
  "DRAFT",
]);

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60_000);
  if (mins < 1) return "방금 전";
  if (mins < 60) return `${mins}분 전`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}시간 전`;
  const days = Math.floor(hrs / 24);
  return `${days}일 전`;
}

export default function RecentProjectUpdatesWidget() {
  const navigate = useNavigate();
  const { data, isLoading, isError } = useTransactions({ limit: 20 });

  const recent = useMemo(() => {
    if (!data?.items) return [];
    return data.items
      .filter((t) => VISIBLE_STATUSES.has(t.status as TransactionStatus))
      .sort(
        (a, b) =>
          new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime(),
      )
      .slice(0, 5);
  }, [data]);

  /* ── Loading skeleton ── */
  if (isLoading) {
    return (
      <Card title="최근 프로젝트 진행상황" padding="md">
        <div className="space-y-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="flex gap-3 animate-pulse">
              <div className="w-8 h-8 rounded-lg bg-gray-100 shrink-0" />
              <div className="flex-1 space-y-1.5">
                <div className="h-3.5 w-3/4 bg-gray-100 rounded" />
                <div className="h-3 w-1/2 bg-gray-100 rounded" />
              </div>
            </div>
          ))}
        </div>
      </Card>
    );
  }

  /* ── Error state ── */
  if (isError) {
    return (
      <Card title="최근 프로젝트 진행상황" padding="md">
        <div className="flex flex-col items-center py-6 text-text-muted">
          <Inbox className="w-8 h-8 mb-2 opacity-40" />
          <p className="text-sm">프로젝트 정보를 불러올 수 없습니다</p>
        </div>
      </Card>
    );
  }

  return (
    <Card title="최근 프로젝트 진행상황" padding="none">
      {recent.length === 0 ? (
        <div className="flex flex-col items-center py-8 text-text-muted">
          <FolderKanban className="w-8 h-8 mb-2 opacity-40" />
          <p className="text-sm">최근 업데이트된 프로젝트가 없습니다</p>
        </div>
      ) : (
        <ul className="divide-y divide-border">
          {recent.map((txn) => {
            const label = txn.code_name || txn.target_company_name || txn.name;
            const phaseLabel = PHASE_LABEL[txn.phase] ?? txn.phase;
            const statusInfo =
              STATUS_BADGE[txn.status as TransactionStatus] ??
              STATUS_BADGE.ACTIVE;

            return (
              <li key={txn.id}>
                <button
                  className={cn(
                    "w-full text-left px-4 py-3 hover:bg-bg-cool transition-colors",
                    "flex items-center gap-3 group",
                  )}
                  onClick={() => navigate(`/ma/transactions/${txn.id}`)}
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-text-dark truncate group-hover:text-accent transition-colors">
                        {label}
                      </span>
                      <Badge
                        variant={statusInfo.variant}
                        className="shrink-0 text-[10px]"
                      >
                        {statusInfo.label}
                      </Badge>
                    </div>
                    <div className="flex items-center gap-2 mt-0.5">
                      <span className="text-xs text-text-secondary">
                        {phaseLabel} 단계
                      </span>
                      <span className="text-[11px] text-text-muted">
                        · {timeAgo(txn.updated_at)}
                      </span>
                    </div>
                  </div>
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </Card>
  );
}

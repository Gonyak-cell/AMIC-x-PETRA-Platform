import { cn } from "@/lib/cn";
import type { FMChecklist, FMChecklistStatus } from "@/modules/ma/types/financial_model";

const STATUS_COLORS: Record<FMChecklistStatus, string> = {
  GENERATING: "bg-blue-100 text-blue-700",
  PENDING_REVIEW: "bg-amber-100 text-amber-700",
  REVIEWED: "bg-indigo-100 text-indigo-700",
  FINALIZED: "bg-emerald-100 text-emerald-700",
};

const STATUS_LABELS: Record<FMChecklistStatus, string> = {
  GENERATING: "생성 중",
  PENDING_REVIEW: "리뷰 대기",
  REVIEWED: "리뷰 완료",
  FINALIZED: "확정",
};

interface Props {
  checklist: FMChecklist;
  className?: string;
}

export default function FMChecklistSummaryBar({ checklist, className }: Props) {
  const { total_items, confirmed_count, corrected_count, flagged_count, pending_count } = checklist;
  const reviewedCount = confirmed_count + corrected_count;
  const pct = total_items > 0 ? Math.round((reviewedCount / total_items) * 100) : 0;

  return (
    <div className={cn("space-y-3", className)}>
      {/* Top row */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span
            className={cn(
              "inline-flex items-center px-2.5 py-1 text-xs font-semibold rounded-full",
              STATUS_COLORS[checklist.status],
            )}
          >
            {STATUS_LABELS[checklist.status]}
          </span>
          <span className="text-sm text-text-dark font-medium">
            {reviewedCount} / {total_items} 리뷰 완료
          </span>
        </div>
        <div className="flex items-center gap-3 text-xs">
          <span className="text-emerald-600">
            확인 {confirmed_count}
          </span>
          <span className="text-yellow-600">
            수정 {corrected_count}
          </span>
          {flagged_count > 0 && (
            <span className="text-red-600">
              플래그 {flagged_count}
            </span>
          )}
          {pending_count > 0 && (
            <span className="text-gray-500">
              대기 {pending_count}
            </span>
          )}
        </div>
      </div>

      {/* Progress bar */}
      <div
        className="relative h-2.5 bg-gray-100 rounded-full overflow-hidden"
        role="progressbar"
        aria-valuenow={pct}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={`체크리스트 진행률: ${pct}%`}
      >
        <div
          className="absolute inset-y-0 left-0 rounded-full bg-gradient-to-r from-amic to-accent transition-all duration-500"
          style={{ width: `${pct}%` }}
        />
      </div>
      <div className="flex items-center justify-between text-xs text-text-secondary">
        <span>{pct}% 완료</span>
        <span>총 {total_items}개 항목</span>
      </div>
    </div>
  );
}

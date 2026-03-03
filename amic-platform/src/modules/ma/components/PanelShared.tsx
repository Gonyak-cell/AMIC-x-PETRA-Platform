/**
 * MA Panel 공유 컴포넌트 — DRY 리팩토링 기반.
 *
 * 9개 Panel 컴포넌트에서 반복되는 보일러플레이트 추출:
 * - PanelHeader: 제목 + 우측 액션 버튼
 * - PanelLoadingState: 스피너 + 메시지
 * - PanelEmptyState: 아이콘 + 빈 상태 메시지
 * - ProgressBar: 백분율 바 + 통계
 */

import type { LucideIcon } from "lucide-react";
import { Loader2, Inbox } from "lucide-react";

// ── Panel Header ──

interface PanelHeaderProps {
  title: string;
  count?: number;
  actions?: React.ReactNode;
  className?: string;
}

export function PanelHeader({
  title,
  count,
  actions,
  className,
}: PanelHeaderProps) {
  return (
    <div
      className={`flex items-center justify-between mb-4 ${className ?? ""}`}
    >
      <h3 className="text-base font-semibold text-text-dark">
        {title}
        {count !== undefined && (
          <span className="ml-2 text-sm font-normal text-text-muted">
            ({count}건)
          </span>
        )}
      </h3>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  );
}

// ── Panel Loading State ──

interface PanelLoadingStateProps {
  message?: string;
  className?: string;
}

export function PanelLoadingState({
  message = "데이터를 불러오는 중...",
  className,
}: PanelLoadingStateProps) {
  return (
    <div
      className={`flex flex-col items-center justify-center py-12 text-text-muted ${className ?? ""}`}
    >
      <Loader2 className="h-6 w-6 animate-spin mb-2" />
      <span className="text-sm">{message}</span>
    </div>
  );
}

// ── Panel Empty State ──

interface PanelEmptyStateProps {
  icon?: LucideIcon;
  title: string;
  description?: string;
  action?: React.ReactNode;
  className?: string;
}

export function PanelEmptyState({
  icon: Icon = Inbox,
  title,
  description,
  action,
  className,
}: PanelEmptyStateProps) {
  return (
    <div
      className={`flex flex-col items-center justify-center py-12 text-center ${className ?? ""}`}
    >
      <Icon className="h-10 w-10 text-text-muted/50 mb-3" />
      <p className="text-sm font-medium text-text-dark">{title}</p>
      {description && (
        <p className="text-xs text-text-muted mt-1 max-w-xs">{description}</p>
      )}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

// ── Progress Bar ──

interface ProgressBarProps {
  value: number; // 0-100
  label?: string;
  showPercentage?: boolean;
  className?: string;
}

export function ProgressBar({
  value,
  label,
  showPercentage = true,
  className,
}: ProgressBarProps) {
  const clamped = Math.min(100, Math.max(0, value));
  return (
    <div className={className}>
      {(label || showPercentage) && (
        <div className="flex items-center justify-between mb-1.5">
          {label && (
            <span className="text-xs text-text-secondary">{label}</span>
          )}
          {showPercentage && (
            <span className="text-xs font-semibold text-text-dark tabular-nums">
              {Math.round(clamped)}%
            </span>
          )}
        </div>
      )}
      <div className="w-full bg-gray-200 rounded-full h-2">
        <div
          className="bg-accent h-2 rounded-full transition-all duration-500"
          style={{ width: `${clamped}%` }}
        />
      </div>
    </div>
  );
}

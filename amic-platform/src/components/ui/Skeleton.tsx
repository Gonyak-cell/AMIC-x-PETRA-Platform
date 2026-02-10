import { cn } from "@/lib/cn";

export interface SkeletonProps {
  className?: string;
  style?: React.CSSProperties;
}

export function Skeleton({ className, style }: SkeletonProps) {
  return (
    <div
      className={cn(
        "animate-pulse bg-gray-200 rounded",
        className
      )}
      style={style}
    />
  );
}

/**
 * 여러 줄의 스켈레톤 텍스트
 */
export function SkeletonText({ lines = 3 }: { lines?: number }) {
  return (
    <div className="space-y-2">
      {[...Array(lines)].map((_, i) => (
        <Skeleton
          key={i}
          className={cn(
            "h-4",
            i === lines - 1 ? "w-3/4" : "w-full"
          )}
        />
      ))}
    </div>
  );
}

/**
 * 카드 형태의 스켈레톤
 */
export function SkeletonCard() {
  return (
    <div className="bg-white rounded-lg border border-gray-border p-5 space-y-4">
      <Skeleton className="h-6 w-1/3" />
      <SkeletonText lines={2} />
    </div>
  );
}

/**
 * KPI 카드 스켈레톤
 */
export function KpiCardSkeleton() {
  return (
    <div
      className="bg-white rounded-lg border border-gray-border p-5"
      role="status"
      aria-label="Loading KPI card"
    >
      <Skeleton className="h-4 w-24 mb-2" />
      <Skeleton className="h-8 w-32 mb-1" />
      <Skeleton className="h-3 w-16" />
      <span className="sr-only">Loading...</span>
    </div>
  );
}

/**
 * 전체 페이지 로딩 스켈레톤
 */
export function PageSkeleton() {
  return (
    <div className="space-y-6 animate-pulse" role="status" aria-label="Loading page content">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <Skeleton className="h-8 w-48 mb-2" />
          <Skeleton className="h-4 w-32" />
        </div>
        <Skeleton className="h-10 w-32" />
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {[...Array(4)].map((_, i) => (
          <KpiCardSkeleton key={i} />
        ))}
      </div>

      {/* Main Table */}
      <div className="bg-white rounded-lg border border-gray-border p-5">
        <Skeleton className="h-6 w-1/4 mb-4" />
        <div className="space-y-3">
          {[...Array(5)].map((_, i) => (
            <Skeleton key={i} className="h-12 w-full" />
          ))}
        </div>
      </div>

      <span className="sr-only">Loading...</span>
    </div>
  );
}

export interface ChartSkeletonProps {
  height?: number;
  type?: "bar" | "line" | "waterfall";
}

/**
 * 차트 로딩 스켈레톤
 */
export function ChartSkeleton({ height = 300, type = "bar" }: ChartSkeletonProps) {
  return (
    <div
      className="bg-white rounded-lg border border-gray-border p-5 animate-pulse"
      role="status"
      aria-label="Loading chart"
    >
      <Skeleton className="h-5 w-32 mb-4" />
      <div className="relative" style={{ height: `${height}px` }}>
        {/* Y-axis */}
        <div className="absolute left-0 top-0 bottom-0 w-12 flex flex-col justify-between py-2">
          {[...Array(5)].map((_, i) => (
            <Skeleton key={i} className="h-3 w-8" />
          ))}
        </div>

        {/* Chart area */}
        <div className="ml-14 h-full flex items-end gap-2 pb-6">
          {type === "bar" || type === "waterfall" ? (
            [...Array(6)].map((_, i) => (
              <div key={i} className="flex-1 flex flex-col items-center">
                <Skeleton
                  className="w-full rounded-t"
                  style={{ height: `${30 + (i % 3) * 20}%` }}
                />
              </div>
            ))
          ) : (
            <Skeleton className="w-full h-3/4 rounded" />
          )}
        </div>

        {/* X-axis labels */}
        <div className="absolute bottom-0 left-14 right-0 flex justify-between">
          {[...Array(6)].map((_, i) => (
            <Skeleton key={i} className="h-3 w-10" />
          ))}
        </div>
      </div>
      <span className="sr-only">Loading chart...</span>
    </div>
  );
}

/**
 * 테이블 스켈레톤
 */
export interface TableSkeletonProps {
  rows?: number;
  columns?: number;
}

export function TableSkeleton({ rows = 5, columns = 4 }: TableSkeletonProps) {
  return (
    <div
      className="bg-white rounded-lg border border-gray-border overflow-hidden"
      role="status"
      aria-label="Loading table"
    >
      {/* Header */}
      <div className="bg-gray-50 px-4 py-3 flex gap-4 border-b border-gray-border">
        {[...Array(columns)].map((_, i) => (
          <Skeleton
            key={i}
            className="h-4"
            style={{ width: `${100 / columns}%` }}
          />
        ))}
      </div>

      {/* Rows */}
      <div className="divide-y divide-gray-100">
        {[...Array(rows)].map((_, rowIdx) => (
          <div key={rowIdx} className="px-4 py-3 flex gap-4">
            {[...Array(columns)].map((_, colIdx) => (
              <Skeleton
                key={colIdx}
                className="h-4"
                style={{ width: `${100 / columns}%` }}
              />
            ))}
          </div>
        ))}
      </div>
      <span className="sr-only">Loading table...</span>
    </div>
  );
}

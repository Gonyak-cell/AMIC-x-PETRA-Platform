import { Fragment, useState, useRef, useCallback, useEffect } from "react";
import type { ReactNode, KeyboardEvent } from "react";
import { cn } from "@/lib/cn";
import { gsap } from "@/lib/gsap";
import { Skeleton } from "./Skeleton";

export interface Column<T> {
  key: Extract<keyof T, string> | (string & {});
  /** Column heading text — accepts either `header` or `label` */
  header?: string;
  label?: string;
  align?: "left" | "center" | "right";
  width?: string;
  render?: (row: T, index: number) => ReactNode;
  mono?: boolean;
  sortable?: boolean;
}

export interface SectionHeaderConfig {
  index: number;
  label: string;
}

export interface DataTableProps<T> {
  columns: Column<T>[];
  data: T[];
  keyField: string;
  loading?: boolean;
  skeletonRows?: number;
  emptyMessage?: string;
  striped?: boolean;
  compact?: boolean;
  onRowClick?: (row: T) => void;
  sectionHeaders?: SectionHeaderConfig[];
  footer?: ReactNode;
  uppercaseHeaders?: boolean;
  borderless?: boolean;
  className?: string;
}

const alignStyles = {
  left: "text-left",
  center: "text-center",
  right: "text-right",
};

export function DataTable<T extends object>({
  columns,
  data,
  keyField,
  loading = false,
  skeletonRows = 5,
  emptyMessage = "No data available",
  striped = true,
  compact = false,
  onRowClick,
  sectionHeaders = [],
  footer,
  uppercaseHeaders = false,
  borderless = true,
  className,
}: DataTableProps<T>) {
  const cellPadding = compact ? "px-3 py-2" : "px-4 py-3";
  const [focusedRowIndex, setFocusedRowIndex] = useState<number>(-1);
  const rowRefs = useRef<(HTMLTableRowElement | null)[]>([]);
  const tbodyRef = useRef<HTMLTableSectionElement>(null);
  const prevDataLen = useRef(0);

  // Stagger-in rows when data changes
  useEffect(() => {
    if (!tbodyRef.current || !data.length || data.length === prevDataLen.current) return;
    prevDataLen.current = data.length;

    const rows = tbodyRef.current.querySelectorAll("tr");
    if (!rows.length) return;

    gsap.fromTo(
      Array.from(rows),
      { opacity: 0, y: 10 },
      { opacity: 1, y: 0, stagger: 0.03, duration: 0.35, ease: "power2.out" },
    );
  }, [data]);

  // 섹션 헤더 인덱스 맵
  const sectionMap = new Map(sectionHeaders.map((s) => [s.index, s.label]));

  // 키보드 내비게이션 핸들러
  const handleKeyDown = useCallback(
    (e: KeyboardEvent<HTMLTableRowElement>, rowIndex: number, row: T) => {
      switch (e.key) {
        case "ArrowDown":
          e.preventDefault();
          if (rowIndex < data.length - 1) {
            setFocusedRowIndex(rowIndex + 1);
            rowRefs.current[rowIndex + 1]?.focus();
          }
          break;
        case "ArrowUp":
          e.preventDefault();
          if (rowIndex > 0) {
            setFocusedRowIndex(rowIndex - 1);
            rowRefs.current[rowIndex - 1]?.focus();
          }
          break;
        case "Home":
          e.preventDefault();
          setFocusedRowIndex(0);
          rowRefs.current[0]?.focus();
          break;
        case "End":
          e.preventDefault();
          setFocusedRowIndex(data.length - 1);
          rowRefs.current[data.length - 1]?.focus();
          break;
        case "Enter":
        case " ":
          e.preventDefault();
          onRowClick?.(row);
          break;
      }
    },
    [data.length, onRowClick]
  );

  if (loading) {
    return (
      <div className={cn("overflow-hidden overflow-x-auto", !borderless && "border border-gray-border rounded-dr", className)}>
        <table className="w-full">
          <thead>
            <tr className="bg-amic-50 border-b-2 border-amic">
              {columns.map((col) => (
                <th
                  key={col.key}
                  className={cn(
                    "text-amic font-heading font-semibold text-sub-header tracking-wide",
                    uppercaseHeaders && "uppercase tracking-[0.15em]",
                    cellPadding,
                    alignStyles[col.align || "left"]
                  )}
                  style={{ width: col.width }}
                >
                  {col.header ?? col.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {[...Array(skeletonRows)].map((_, i) => (
              <tr key={i} className={striped && i % 2 === 1 ? "bg-table-alt" : "bg-white"}>
                {columns.map((col) => (
                  <td key={col.key} className={cellPadding}>
                    <Skeleton className="h-4 w-full" />
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  if (!data.length) {
    return (
      <div className={cn("overflow-hidden overflow-x-auto", !borderless && "border border-gray-border rounded-dr", className)}>
        <table className="w-full">
          <thead>
            <tr className="bg-amic-50 border-b-2 border-amic">
              {columns.map((col) => (
                <th
                  key={col.key}
                  className={cn(
                    "text-amic font-heading font-semibold text-sub-header tracking-wide",
                    uppercaseHeaders && "uppercase tracking-[0.15em]",
                    cellPadding,
                    alignStyles[col.align || "left"]
                  )}
                  style={{ width: col.width }}
                >
                  {col.header ?? col.label}
                </th>
              ))}
            </tr>
          </thead>
        </table>
        <div className="py-12 text-center text-text-secondary">{emptyMessage}</div>
      </div>
    );
  }

  return (
    <div className={cn("overflow-hidden overflow-x-auto", !borderless && "border border-gray-border rounded-dr", className)}>
      <table className="w-full">
        <thead>
          <tr className="bg-amic-50 border-b-2 border-amic">
            {columns.map((col) => (
              <th
                key={col.key}
                className={cn(
                  "text-amic font-heading font-semibold text-sub-header tracking-wide",
                    uppercaseHeaders && "uppercase tracking-[0.15em]",
                  cellPadding,
                  alignStyles[col.align || "left"]
                )}
                style={{ width: col.width }}
              >
                {col.header ?? col.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody ref={tbodyRef} className="font-body text-body-text">
          {data.map((row, rowIndex) => {
            const sectionLabel = sectionMap.get(rowIndex);
            const rowKey = String((row as Record<string, unknown>)[keyField] ?? rowIndex);

            return (
              <Fragment key={rowKey}>
                {/* 섹션 헤더 (다크그린 바) */}
                {sectionLabel && (
                  <tr className="bg-amic">
                    <td
                      colSpan={columns.length}
                      className="px-4 py-2 text-white font-heading font-semibold text-sm"
                    >
                      {sectionLabel}
                    </td>
                  </tr>
                )}

                {/* 데이터 행 */}
                <tr
                  ref={(el) => { rowRefs.current[rowIndex] = el; }}
                  tabIndex={onRowClick ? 0 : undefined}
                  role={onRowClick ? "button" : undefined}
                  aria-label={onRowClick ? `Row ${rowIndex + 1}` : undefined}
                  className={cn(
                    striped && rowIndex % 2 === 1 ? "bg-table-alt" : "bg-white",
                    onRowClick && "cursor-pointer hover:bg-accent/5 transition-colors",
                    onRowClick && "focus:outline-none focus:ring-2 focus:ring-inset focus:ring-accent",
                    focusedRowIndex === rowIndex && "ring-2 ring-inset ring-accent"
                  )}
                  onClick={() => onRowClick?.(row)}
                  onKeyDown={onRowClick ? (e) => handleKeyDown(e, rowIndex, row) : undefined}
                  onFocus={() => setFocusedRowIndex(rowIndex)}
                  onBlur={() => setFocusedRowIndex(-1)}
                >
                  {columns.map((col) => (
                    <td
                      key={col.key}
                      className={cn(
                        cellPadding,
                        alignStyles[col.align || "left"],
                        col.mono && "font-mono tabular-nums"
                      )}
                      style={{ width: col.width }}
                    >
                      {col.render
                        ? col.render(row, rowIndex)
                        : ((row as Record<string, unknown>)[col.key] as ReactNode) ?? "-"}
                    </td>
                  ))}
                </tr>
              </Fragment>
            );
          })}
        </tbody>
        {footer && (
          <tfoot>
            <tr className="bg-amic-50 border-t border-gray-border font-semibold">
              {footer}
            </tr>
          </tfoot>
        )}
      </table>
    </div>
  );
}

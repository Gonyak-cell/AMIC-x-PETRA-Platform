import { useState, useMemo } from "react";
import {
  Search,
  MessageSquare,
  Paperclip,
  Trash2,
  X,
  ChevronRight,
} from "lucide-react";
import { Badge, Button, Spinner } from "@/components/ui";
import { useRFIItems, useDeleteRFIItem } from "@/modules/ma/hooks/useRFI";
import {
  RFI_CATEGORY_OPTIONS,
  RFI_ITEM_STATUS_OPTIONS,
  RFI_PRIORITY_OPTIONS,
  RFI_CATEGORY_LABELS,
  RFI_ITEM_STATUS_LABELS,
  RFI_PRIORITY_LABELS,
} from "@/modules/ma/constants";
import { RFI_ITEM_STATUS_VARIANT } from "@/modules/ma/constants/status-variants";
import type {
  RFIItemListOut,
  RFICategoryV2,
  RFIItemStatusV2,
  RFIPriority,
} from "@/modules/ma/types/rfi";

// ── Priority color mapping ─────────────────────────────
const PRIORITY_TEXT_COLOR: Record<RFIPriority, string> = {
  HIGH: "text-red-600",
  MEDIUM: "text-amber-600",
  LOW: "text-green-600",
};

// ── Props ──────────────────────────────────────────────
interface RFIItemListProps {
  txnId: string;
  onSelectItem: (itemId: string) => void;
}

// ── Component ──────────────────────────────────────────
export default function RFIItemList({ txnId, onSelectItem }: RFIItemListProps) {
  const [category, setCategory] = useState("");
  const [status, setStatus] = useState("");
  const [priority, setPriority] = useState("");
  const [search, setSearch] = useState("");

  const filters = useMemo(() => {
    const f: Record<string, string> = {};
    if (category) f.category = category;
    if (status) f.status = status;
    if (priority) f.priority = priority;
    if (search.trim()) f.search = search.trim();
    return f;
  }, [category, status, priority, search]);

  const { data, isLoading, isError } = useRFIItems(txnId, filters);
  const deleteMutation = useDeleteRFIItem(txnId);

  const items: RFIItemListOut[] = Array.isArray(data) ? data : [];

  const hasActiveFilters = !!(category || status || priority || search);

  const resetFilters = () => {
    setCategory("");
    setStatus("");
    setPriority("");
    setSearch("");
  };

  const handleDelete = (e: React.MouseEvent, itemId: string) => {
    e.stopPropagation();
    if (!window.confirm("이 질의를 삭제하시겠습니까?")) return;
    deleteMutation.mutate(itemId);
  };

  const formatDate = (iso: string | null): string => {
    if (!iso) return "-";
    return new Date(iso).toLocaleDateString("ko-KR", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
    });
  };

  const truncate = (text: string, max: number): string => {
    if (text.length <= max) return text;
    return text.slice(0, max) + "...";
  };

  // ── Filter bar ─────────────────────────────────────
  const filterBar = (
    <div className="flex flex-wrap items-center gap-2 p-3 border-b border-gray-border">
      {/* Search input */}
      <div className="relative flex-1 min-w-[180px]">
        <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-4 w-4 text-text-muted" />
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="질문 검색..."
          aria-label="질문 검색"
          className="w-full pl-8 pr-3 py-1.5 text-sm border border-gray-border rounded-dr bg-bg-white placeholder:text-text-muted focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
      </div>

      {/* Category */}
      <select
        value={category}
        onChange={(e) => setCategory(e.target.value)}
        aria-label="카테고리 필터"
        className="text-sm border border-gray-border rounded-dr px-2 py-1.5 bg-bg-white text-text-dark focus:outline-none focus:ring-1 focus:ring-blue-500"
      >
        {RFI_CATEGORY_OPTIONS.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>

      {/* Status */}
      <select
        value={status}
        onChange={(e) => setStatus(e.target.value)}
        aria-label="상태 필터"
        className="text-sm border border-gray-border rounded-dr px-2 py-1.5 bg-bg-white text-text-dark focus:outline-none focus:ring-1 focus:ring-blue-500"
      >
        {RFI_ITEM_STATUS_OPTIONS.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>

      {/* Priority */}
      <select
        value={priority}
        onChange={(e) => setPriority(e.target.value)}
        aria-label="우선순위 필터"
        className="text-sm border border-gray-border rounded-dr px-2 py-1.5 bg-bg-white text-text-dark focus:outline-none focus:ring-1 focus:ring-blue-500"
      >
        {RFI_PRIORITY_OPTIONS.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>

      {/* Reset */}
      {hasActiveFilters && (
        <Button variant="ghost" size="sm" onClick={resetFilters} aria-label="필터 초기화">
          <X className="h-4 w-4" />
        </Button>
      )}
    </div>
  );

  // ── Error state ───────────────────────────────────
  if (isError) {
    return (
      <div className="rounded-dr border border-gray-border shadow-dr-sm bg-bg-white">
        {filterBar}
        <div className="flex flex-col items-center justify-center py-16 text-red-600">
          <p className="text-sm">데이터를 불러오는 중 오류가 발생했습니다.</p>
        </div>
      </div>
    );
  }

  // ── Loading state ──────────────────────────────────
  if (isLoading) {
    return (
      <div className="rounded-dr border border-gray-border shadow-dr-sm bg-bg-white">
        {filterBar}
        <div className="flex items-center justify-center py-16">
          <Spinner size="md" />
        </div>
      </div>
    );
  }

  // ── Main render ────────────────────────────────────
  return (
    <div className="rounded-dr border border-gray-border shadow-dr-sm bg-bg-white overflow-hidden">
      {filterBar}

      {items.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 text-text-muted">
          <Search className="h-8 w-8 mb-2 opacity-40" />
          <p className="text-sm">
            {hasActiveFilters
              ? "필터 조건에 맞는 질의가 없습니다."
              : "등록된 질의가 없습니다."}
          </p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-border bg-bg-cool/30 text-left text-xs font-medium text-text-secondary">
                <th className="px-3 py-2">번호</th>
                <th className="px-3 py-2">카테고리</th>
                <th className="px-3 py-2">우선순위</th>
                <th className="px-3 py-2">질문</th>
                <th className="px-3 py-2">상태</th>
                <th className="px-3 py-2 text-center">답변</th>
                <th className="px-3 py-2 text-center">첨부</th>
                <th className="px-3 py-2">마감일</th>
                <th className="px-3 py-2 w-8" />
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr
                  key={item.id}
                  onClick={() => onSelectItem(item.id)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      e.preventDefault();
                      onSelectItem(item.id);
                    }
                  }}
                  className="border-b border-gray-border last:border-b-0 cursor-pointer hover:bg-bg-cool/50 transition-colors"
                >
                  <td className="px-3 py-2.5 font-mono text-text-secondary whitespace-nowrap">
                    {item.item_number}
                  </td>
                  <td className="px-3 py-2.5">
                    <Badge variant="neutral">
                      {RFI_CATEGORY_LABELS[item.category]}
                    </Badge>
                  </td>
                  <td className="px-3 py-2.5 whitespace-nowrap">
                    <span
                      className={`text-xs font-semibold ${PRIORITY_TEXT_COLOR[item.priority]}`}
                    >
                      {RFI_PRIORITY_LABELS[item.priority]}
                    </span>
                  </td>
                  <td className="px-3 py-2.5 text-text-dark max-w-[320px]">
                    {truncate(item.question_text, 60)}
                  </td>
                  <td className="px-3 py-2.5">
                    <Badge
                      variant={RFI_ITEM_STATUS_VARIANT[item.current_status]}
                    >
                      {RFI_ITEM_STATUS_LABELS[item.current_status]}
                    </Badge>
                  </td>
                  <td className="px-3 py-2.5 text-center">
                    <span className="inline-flex items-center gap-1 text-text-secondary">
                      <MessageSquare className="h-3.5 w-3.5" />
                      {item.thread_count}
                    </span>
                  </td>
                  <td className="px-3 py-2.5 text-center">
                    <span className="inline-flex items-center gap-1 text-text-secondary">
                      <Paperclip className="h-3.5 w-3.5" />
                      {item.attachment_count}
                    </span>
                  </td>
                  <td className="px-3 py-2.5 text-text-muted whitespace-nowrap">
                    {formatDate(item.due_date)}
                  </td>
                  <td className="px-3 py-2.5">
                    <div className="flex items-center gap-1">
                      <button
                        type="button"
                        className="p-1 rounded text-text-muted hover:text-red-600 hover:bg-red-50 transition-colors"
                        onClick={(e) => handleDelete(e, item.id)}
                        title="삭제"
                        aria-label={`${item.item_number} 삭제`}
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                      <ChevronRight className="h-4 w-4 text-text-muted" />
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

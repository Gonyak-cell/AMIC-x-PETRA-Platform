import { useMemo, useState } from "react";
import { ChevronDown, ChevronRight, CheckCircle } from "lucide-react";
import { cn } from "@/lib/cn";
import { Button } from "@/components/ui";
import FMChecklistItemCard from "./FMChecklistItemCard";
import type {
  FMChecklistItem,
  FMChecklistItemStatus,
  FMChecklistCategory,
} from "@/modules/ma/types/financial_model";
import { FM_CATEGORY_LABELS } from "@/modules/ma/types/financial_model";

interface Props {
  groupName: string;
  categories: FMChecklistCategory[];
  items: FMChecklistItem[];
  onUpdateItem: (
    itemId: string,
    body: { status: FMChecklistItemStatus; user_correction?: string | null; user_value?: string | null },
  ) => void;
  onConfirmAllInGroup: (itemIds: string[]) => void;
  isUpdating?: boolean;
}

export default function FMChecklistCategorySection({
  groupName,
  categories,
  items,
  onUpdateItem,
  onConfirmAllInGroup,
  isUpdating = false,
}: Props) {
  const [collapsed, setCollapsed] = useState(false);

  const groupItems = useMemo(
    () => items.filter((it) => categories.includes(it.category)).sort((a, b) => a.order_index - b.order_index),
    [items, categories],
  );

  const unconfirmedItems = useMemo(
    () => groupItems.filter((it) => it.status === "AUTO_GENERATED"),
    [groupItems],
  );

  const confirmedCount = groupItems.length - unconfirmedItems.length;
  const allDone = unconfirmedItems.length === 0 && groupItems.length > 0;

  if (groupItems.length === 0) return null;

  return (
    <div className="border border-gray-border rounded-lg overflow-hidden">
      {/* Header */}
      <button
        type="button"
        onClick={() => setCollapsed(!collapsed)}
        className="w-full flex items-center justify-between px-4 py-3 bg-bg-cool hover:bg-gray-50 transition-colors"
      >
        <div className="flex items-center gap-2">
          {collapsed ? <ChevronRight className="h-4 w-4 text-text-secondary" /> : <ChevronDown className="h-4 w-4 text-text-secondary" />}
          <span className="text-sm font-semibold text-text-dark">{groupName}</span>
          <span className="text-xs text-text-secondary">
            ({confirmedCount}/{groupItems.length})
          </span>
          {allDone && <CheckCircle className="h-3.5 w-3.5 text-positive" />}
        </div>
        <div className="flex items-center gap-2">
          {categories.map((cat) => (
            <span key={cat} className="text-[10px] text-text-secondary bg-white px-1.5 py-0.5 rounded">
              {FM_CATEGORY_LABELS[cat]}
            </span>
          ))}
        </div>
      </button>

      {/* Content */}
      {!collapsed && (
        <div>
          {/* Bulk confirm */}
          {unconfirmedItems.length > 0 && (
            <div className="flex items-center justify-between px-4 py-2 border-b border-gray-border bg-white">
              <span className="text-xs text-text-secondary">
                {unconfirmedItems.length}개 항목 리뷰 대기
              </span>
              <Button
                variant="accent"
                size="sm"
                icon={CheckCircle}
                onClick={() => onConfirmAllInGroup(unconfirmedItems.map((it) => it.id))}
                loading={isUpdating}
              >
                전체 확인 ({unconfirmedItems.length})
              </Button>
            </div>
          )}

          {/* Table */}
          <div className="overflow-x-auto">
            <table className="w-full text-left" aria-label={`${groupName} checklist items`}>
              <thead>
                <tr className="border-b border-gray-border bg-white">
                  <th className="px-4 py-2 text-xs font-semibold text-text-secondary uppercase tracking-wider w-[18%]">항목</th>
                  <th className="px-4 py-2 text-xs font-semibold text-text-secondary uppercase tracking-wider w-[16%]">자동 추출</th>
                  <th className="px-4 py-2 text-xs font-semibold text-text-secondary uppercase tracking-wider w-[20%]">확인/수정 값</th>
                  <th className="px-4 py-2 text-xs font-semibold text-text-secondary uppercase tracking-wider w-[16%]">VDR 소스</th>
                  <th className="px-4 py-2 text-xs font-semibold text-text-secondary uppercase tracking-wider w-[12%]">신뢰도</th>
                  <th className="px-4 py-2 text-xs font-semibold text-text-secondary uppercase tracking-wider w-[18%]">상태</th>
                </tr>
              </thead>
              <tbody>
                {groupItems.map((item) => (
                  <FMChecklistItemCard
                    key={item.id}
                    item={item}
                    onUpdate={onUpdateItem}
                    isUpdating={isUpdating}
                  />
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

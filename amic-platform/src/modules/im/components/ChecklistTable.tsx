import { useMemo, useCallback } from "react";
import { CheckCircle } from "lucide-react";
import { Button } from "@/components/ui";
import { ChecklistItemRow } from "./ChecklistItemRow";
import type {
  ChecklistCategory,
  ChecklistItem,
  ChecklistItemStatus,
} from "@/modules/im/types/checklist";

export interface ChecklistTableProps {
  items: ChecklistItem[];
  category: ChecklistCategory;
  onUpdateItem: (
    itemId: string,
    body: Partial<Pick<ChecklistItem, "confirmed_value" | "status" | "notes">>,
  ) => void;
  onConfirmAllInCategory: (category: ChecklistCategory) => void;
  isUpdating?: boolean;
}

/**
 * Renders all checklist items for a single category as a table.
 * Includes a "Confirm All" bulk action button at the top.
 */
export function ChecklistTable({
  items,
  category,
  onUpdateItem,
  onConfirmAllInCategory,
  isUpdating = false,
}: ChecklistTableProps) {
  const sortedItems = useMemo(
    () => [...items].sort((a, b) => a.sort_order - b.sort_order),
    [items],
  );

  const unconfirmedCount = useMemo(
    () =>
      sortedItems.filter(
        (it) =>
          it.status !== "CONFIRMED" &&
          it.status !== "MODIFIED" &&
          it.status !== "NOT_APPLICABLE",
      ).length,
    [sortedItems],
  );

  const allConfirmed = unconfirmedCount === 0;

  const handleConfirmAll = useCallback(() => {
    onConfirmAllInCategory(category);
  }, [category, onConfirmAllInCategory]);

  if (sortedItems.length === 0) {
    return (
      <div className="py-8 text-center text-sm text-text-secondary">
        No items in this category.
      </div>
    );
  }

  return (
    <div>
      {/* Bulk action bar */}
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-gray-border bg-bg-cool">
        <span className="text-xs text-text-secondary">
          {sortedItems.length} items
          {!allConfirmed && (
            <> &middot; {unconfirmedCount} unconfirmed</>
          )}
        </span>
        {!allConfirmed && (
          <Button
            variant="accent"
            size="sm"
            icon={CheckCircle}
            onClick={handleConfirmAll}
            loading={isUpdating}
          >
            Confirm All ({unconfirmedCount})
          </Button>
        )}
        {allConfirmed && (
          <span className="inline-flex items-center gap-1 text-xs text-positive font-medium">
            <CheckCircle className="h-3.5 w-3.5" />
            All confirmed
          </span>
        )}
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-left" aria-label="Checklist items">
          <thead>
            <tr className="border-b border-gray-border bg-white">
              <th className="px-4 py-2.5 text-xs font-semibold text-text-secondary uppercase tracking-wider w-[18%]">
                Field
              </th>
              <th className="px-4 py-2.5 text-xs font-semibold text-text-secondary uppercase tracking-wider w-[16%]">
                Extracted
              </th>
              <th className="px-4 py-2.5 text-xs font-semibold text-text-secondary uppercase tracking-wider w-[20%]">
                Confirmed Value
              </th>
              <th className="px-4 py-2.5 text-xs font-semibold text-text-secondary uppercase tracking-wider w-[18%]">
                VDR Source
              </th>
              <th className="px-4 py-2.5 text-xs font-semibold text-text-secondary uppercase tracking-wider w-[12%]">
                Confidence
              </th>
              <th className="px-4 py-2.5 text-xs font-semibold text-text-secondary uppercase tracking-wider w-[16%]">
                Status
              </th>
            </tr>
          </thead>
          <tbody>
            {sortedItems.map((item) => (
              <ChecklistItemRow
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
  );
}

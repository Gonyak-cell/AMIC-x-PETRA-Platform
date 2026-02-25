import { useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import ChecklistItemCard from "./ChecklistItemCard";
import type {
  ChecklistItem,
  ChecklistItemStatus,
} from "@/modules/fdd/hooks/useChecklist";

interface Props {
  groupName: string;
  items: ChecklistItem[];
  dealId: string;
  onUpdateItem: (
    itemId: string,
    status: ChecklistItemStatus,
    correction?: string,
    amount?: string
  ) => void;
  isUpdating?: boolean;
}

export default function ChecklistCategorySection({
  groupName,
  items,
  dealId,
  onUpdateItem,
  isUpdating,
}: Props) {
  const [open, setOpen] = useState(true);

  const reviewed = items.filter((i) => i.status !== "AUTO_GENERATED").length;

  return (
    <div className="border border-border-default rounded-lg overflow-hidden">
      {/* Section header */}
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-4 py-3 bg-bg-cool hover:bg-bg-warm transition-colors"
      >
        <div className="flex items-center gap-2">
          {open ? (
            <ChevronDown className="w-4 h-4 text-text-secondary" />
          ) : (
            <ChevronRight className="w-4 h-4 text-text-secondary" />
          )}
          <span className="text-sm font-semibold text-text-heading">
            {groupName}
          </span>
        </div>
        <span className="text-xs text-text-secondary">
          {reviewed}/{items.length} reviewed
        </span>
      </button>

      {/* Items */}
      {open && (
        <div className="p-3 space-y-3">
          {items.map((item) => (
            <ChecklistItemCard
              key={item.id}
              item={item}
              dealId={dealId}
              onUpdate={onUpdateItem}
              isUpdating={isUpdating}
            />
          ))}
        </div>
      )}
    </div>
  );
}

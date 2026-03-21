import { useState, useCallback, useRef, useEffect } from "react";
import { Check, X, Pencil, AlertTriangle, Flag, MinusCircle } from "lucide-react";
import { cn } from "@/lib/cn";
import type { FMChecklistItem, FMChecklistItemStatus } from "@/modules/ma/types/financial_model";
import {
  FM_ITEM_STATUS_LABELS,
  FM_ITEM_STATUS_COLORS,
  FM_SEVERITY_COLORS,
} from "@/modules/ma/types/financial_model";

interface Props {
  item: FMChecklistItem;
  onUpdate: (
    itemId: string,
    body: { status: FMChecklistItemStatus; user_correction?: string | null; user_value?: string | null },
  ) => void;
  isUpdating?: boolean;
}

function confidenceColor(value: number): string {
  if (value >= 0.8) return "bg-positive";
  if (value >= 0.5) return "bg-amber-400";
  return "bg-negative";
}

export default function FMChecklistItemCard({ item, onUpdate, isUpdating = false }: Props) {
  const [editing, setEditing] = useState(false);
  const [editValue, setEditValue] = useState(item.user_value ?? item.auto_value ?? "");
  const [editCorrection, setEditCorrection] = useState(item.user_correction ?? "");
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (editing) {
      inputRef.current?.focus();
      inputRef.current?.select();
    }
  }, [editing]);

  const handleSave = useCallback(() => {
    const trimmedVal = editValue.trim();
    onUpdate(item.id, {
      status: "CORRECTED",
      user_value: trimmedVal || null,
      user_correction: editCorrection.trim() || null,
    });
    setEditing(false);
  }, [editValue, editCorrection, item.id, onUpdate]);

  const handleConfirm = useCallback(() => {
    onUpdate(item.id, { status: "CONFIRMED" });
  }, [item.id, onUpdate]);

  const handleFlag = useCallback(() => {
    onUpdate(item.id, { status: "FLAGGED" });
  }, [item.id, onUpdate]);

  const handleNA = useCallback(() => {
    onUpdate(item.id, { status: "NOT_APPLICABLE" });
  }, [item.id, onUpdate]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter") handleSave();
      if (e.key === "Escape") {
        setEditValue(item.user_value ?? item.auto_value ?? "");
        setEditCorrection(item.user_correction ?? "");
        setEditing(false);
      }
    },
    [handleSave, item],
  );

  const isReviewed = item.status === "CONFIRMED" || item.status === "CORRECTED";
  const displayValue = item.user_value ?? item.auto_value;
  const unitSuffix = item.unit ? ` ${item.unit}` : "";

  return (
    <tr
      className={cn(
        "group border-b border-gray-border last:border-b-0 transition-colors",
        item.status === "FLAGGED" && "bg-red-50/50",
        isUpdating && "opacity-60 pointer-events-none",
      )}
    >
      {/* Title + Description */}
      <td className="px-4 py-3 text-sm text-text-dark">
        <div className="flex items-center gap-1.5">
          {item.severity && (
            <span className={cn("text-xs font-bold", FM_SEVERITY_COLORS[item.severity])}>
              {item.severity === "HIGH" ? "!" : item.severity === "MEDIUM" ? "~" : ""}
            </span>
          )}
          <span className="font-medium">{item.title}</span>
        </div>
        {item.field_type && (
          <span className="text-[10px] text-text-secondary">
            {item.field_type}
          </span>
        )}
      </td>

      {/* Auto Finding / Value */}
      <td className="px-4 py-3 text-sm text-text-secondary">
        {item.auto_value ? (
          <span>{item.auto_value}{unitSuffix}</span>
        ) : item.auto_finding ? (
          <span className="text-xs line-clamp-2">{item.auto_finding}</span>
        ) : (
          <span className="italic text-text-secondary/60">--</span>
        )}
      </td>

      {/* User Value (editable) */}
      <td className="px-4 py-3">
        {editing ? (
          <div className="space-y-1">
            <div className="flex items-center gap-1.5">
              <input
                ref={inputRef}
                type={item.field_type === "number" || item.field_type === "currency" || item.field_type === "percentage" ? "number" : "text"}
                value={editValue}
                onChange={(e) => setEditValue(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="수정 값"
                className="w-full px-2 py-1 text-sm border border-accent rounded focus:outline-none focus:ring-2 focus:ring-accent/40"
                step={item.field_type === "percentage" ? "0.01" : undefined}
              />
              <button type="button" onClick={handleSave} className="p-1 text-positive hover:bg-positive/10 rounded" aria-label="Save">
                <Check className="h-3.5 w-3.5" />
              </button>
              <button
                type="button"
                onClick={() => {
                  setEditValue(item.user_value ?? item.auto_value ?? "");
                  setEditCorrection(item.user_correction ?? "");
                  setEditing(false);
                }}
                className="p-1 text-text-secondary hover:bg-gray-100 rounded"
                aria-label="Cancel"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            </div>
            <input
              type="text"
              value={editCorrection}
              onChange={(e) => setEditCorrection(e.target.value)}
              placeholder="수정 사유 (선택)"
              className="w-full px-2 py-1 text-xs border border-gray-200 rounded"
            />
          </div>
        ) : (
          <div className="flex items-center gap-2">
            <span
              className={cn(
                "text-sm",
                isReviewed ? "text-text-dark font-medium" : "text-text-secondary",
                !displayValue && "text-text-secondary/60 italic",
              )}
            >
              {displayValue ? (
                <>{displayValue}{unitSuffix}</>
              ) : (
                <span className="flex items-center gap-1">
                  <AlertTriangle className="h-3 w-3 text-negative" />
                  미입력
                </span>
              )}
            </span>
            <button
              type="button"
              onClick={() => setEditing(true)}
              className="p-1 text-text-secondary hover:text-amic hover:bg-amic/5 rounded opacity-0 group-hover:opacity-100 transition-opacity"
              aria-label={`Edit ${item.title}`}
            >
              <Pencil className="h-3.5 w-3.5" />
            </button>
          </div>
        )}
        {item.user_correction && !editing && (
          <span className="text-[10px] text-yellow-600 mt-0.5 block">
            {item.user_correction}
          </span>
        )}
      </td>

      {/* VDR Source */}
      <td className="px-4 py-3 text-xs text-text-secondary">
        {item.source_vdr_doc_name ? (
          <div>
            <span className="font-medium">{item.source_vdr_doc_name}</span>
            {item.source_location && (
              <span className="block text-[10px]">{item.source_location}</span>
            )}
          </div>
        ) : (
          <span className="italic">--</span>
        )}
      </td>

      {/* Confidence */}
      <td className="px-4 py-3">
        {item.confidence != null ? (
          <div className="flex items-center gap-2">
            <div className="w-12 h-1.5 bg-gray-100 rounded-full overflow-hidden">
              <div
                className={cn("h-full rounded-full transition-all", confidenceColor(item.confidence))}
                style={{ width: `${Math.round(item.confidence * 100)}%` }}
              />
            </div>
            <span className="text-xs text-text-secondary">
              {Math.round(item.confidence * 100)}%
            </span>
          </div>
        ) : (
          <span className="text-xs text-text-secondary">--</span>
        )}
      </td>

      {/* Status + Actions */}
      <td className="px-4 py-3">
        <div className="flex items-center gap-1.5">
          <span
            className={cn(
              "inline-flex px-2 py-0.5 text-[10px] font-semibold rounded-full whitespace-nowrap",
              FM_ITEM_STATUS_COLORS[item.status],
            )}
          >
            {FM_ITEM_STATUS_LABELS[item.status]}
          </span>
          {item.status === "AUTO_GENERATED" && (
            <div className="flex items-center gap-0.5">
              <button type="button" onClick={handleConfirm} className="p-0.5 text-positive hover:bg-positive/10 rounded" aria-label="확인" disabled={isUpdating}>
                <Check className="h-3 w-3" />
              </button>
              <button type="button" onClick={handleFlag} className="p-0.5 text-negative hover:bg-negative/10 rounded" aria-label="플래그" disabled={isUpdating}>
                <Flag className="h-3 w-3" />
              </button>
              <button type="button" onClick={handleNA} className="p-0.5 text-gray-400 hover:bg-gray-100 rounded" aria-label="해당 없음" disabled={isUpdating}>
                <MinusCircle className="h-3 w-3" />
              </button>
            </div>
          )}
        </div>
      </td>
    </tr>
  );
}

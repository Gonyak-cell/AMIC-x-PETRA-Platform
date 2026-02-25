import { useState, useCallback, useRef, useEffect } from "react";
import { Check, X, Pencil, AlertTriangle } from "lucide-react";
import { cn } from "@/lib/cn";
import { Button } from "@/components/ui";
import { SourceDocumentLink } from "./SourceDocumentLink";
import type { ChecklistItem, ChecklistItemStatus } from "@/modules/im/types/checklist";
import { ITEM_STATUS_LABEL } from "@/modules/im/types/checklist";

// ── Status badge colors ─────────────────────────────────────

const ITEM_STATUS_COLORS: Record<ChecklistItemStatus, string> = {
  EXTRACTED: "bg-blue-100 text-blue-700",
  CONFIRMED: "bg-emerald-100 text-emerald-700",
  MODIFIED: "bg-violet-100 text-violet-700",
  MISSING: "bg-negative/10 text-negative",
  NOT_APPLICABLE: "bg-gray-100 text-text-secondary",
};

// ── Confidence bar color ─────────────────────────────────────

function confidenceColor(value: number): string {
  if (value >= 0.8) return "bg-positive";
  if (value >= 0.5) return "bg-amber-400";
  return "bg-negative";
}

// ── Component Props ──────────────────────────────────────────

export interface ChecklistItemRowProps {
  item: ChecklistItem;
  onUpdate: (
    itemId: string,
    body: Partial<Pick<ChecklistItem, "confirmed_value" | "status" | "notes">>,
  ) => void;
  isUpdating?: boolean;
}

/**
 * Single checklist item row with inline editing capability.
 * Clicking the edit button reveals an input to modify the confirmed value.
 */
export function ChecklistItemRow({
  item,
  onUpdate,
  isUpdating = false,
}: ChecklistItemRowProps) {
  const [editing, setEditing] = useState(false);
  const [editValue, setEditValue] = useState(
    item.confirmed_value ?? item.extracted_value ?? "",
  );
  const inputRef = useRef<HTMLInputElement>(null);

  // Focus input when entering edit mode
  useEffect(() => {
    if (editing) {
      inputRef.current?.focus();
      inputRef.current?.select();
    }
  }, [editing]);

  const handleSave = useCallback(() => {
    const trimmed = editValue.trim();
    if (trimmed === (item.confirmed_value ?? item.extracted_value ?? "")) {
      setEditing(false);
      return;
    }
    onUpdate(item.id, {
      confirmed_value: trimmed,
      status: "MODIFIED",
    });
    setEditing(false);
  }, [editValue, item, onUpdate]);

  const handleConfirm = useCallback(() => {
    onUpdate(item.id, {
      confirmed_value: item.confirmed_value ?? item.extracted_value ?? "",
      status: "CONFIRMED",
    });
  }, [item, onUpdate]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter") handleSave();
      if (e.key === "Escape") {
        setEditValue(item.confirmed_value ?? item.extracted_value ?? "");
        setEditing(false);
      }
    },
    [handleSave, item],
  );

  const isMissing = item.status === "MISSING";
  const isConfirmed = item.status === "CONFIRMED" || item.status === "MODIFIED";
  const displayValue = item.confirmed_value ?? item.extracted_value;
  const unitSuffix = item.unit ? ` ${item.unit}` : "";

  return (
    <tr
      className={cn(
        "group border-b border-gray-border last:border-b-0 transition-colors",
        isMissing && "bg-negative/5",
        isUpdating && "opacity-60 pointer-events-none",
      )}
    >
      {/* Field Label */}
      <td className="px-4 py-3 text-sm text-text-dark">
        <div className="flex items-center gap-1.5">
          {item.is_required && (
            <span className="text-negative text-xs" title="Required field">
              *
            </span>
          )}
          <span className="font-medium">{item.field_label}</span>
        </div>
        {item.fiscal_year && (
          <span className="text-[10px] text-text-secondary">
            FY{item.fiscal_year}
          </span>
        )}
      </td>

      {/* Extracted Value */}
      <td className="px-4 py-3 text-sm text-text-secondary">
        {item.extracted_value ? (
          <span>
            {item.extracted_value}
            {unitSuffix}
          </span>
        ) : (
          <span className="italic text-text-secondary/60">--</span>
        )}
      </td>

      {/* Confirmed Value (editable) */}
      <td className="px-4 py-3">
        {editing ? (
          <div className="flex items-center gap-1.5">
            <input
              ref={inputRef}
              type={item.field_type === "number" || item.field_type === "currency" || item.field_type === "percentage" ? "number" : "text"}
              value={editValue}
              onChange={(e) => setEditValue(e.target.value)}
              onKeyDown={handleKeyDown}
              className="w-full px-2 py-1 text-sm border border-accent rounded focus:outline-none focus:ring-2 focus:ring-accent/40"
              step={item.field_type === "percentage" ? "0.01" : undefined}
            />
            <button
              type="button"
              onClick={handleSave}
              className="p-1 text-positive hover:bg-positive/10 rounded"
              aria-label="Save"
            >
              <Check className="h-3.5 w-3.5" />
            </button>
            <button
              type="button"
              onClick={() => {
                setEditValue(item.confirmed_value ?? item.extracted_value ?? "");
                setEditing(false);
              }}
              className="p-1 text-text-secondary hover:bg-gray-100 rounded"
              aria-label="Cancel"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </div>
        ) : (
          <div className="flex items-center gap-2">
            <span
              className={cn(
                "text-sm",
                isConfirmed ? "text-text-dark font-medium" : "text-text-secondary",
                isMissing && "text-negative italic",
              )}
            >
              {displayValue ? (
                <>
                  {displayValue}
                  {unitSuffix}
                </>
              ) : (
                <span className="flex items-center gap-1">
                  <AlertTriangle className="h-3 w-3 text-negative" />
                  Missing
                </span>
              )}
            </span>
            <button
              type="button"
              onClick={() => setEditing(true)}
              className="p-1 text-text-secondary hover:text-amic hover:bg-amic/5 rounded opacity-0 group-hover:opacity-100 focus-visible:opacity-100 transition-opacity"
              aria-label={`Edit ${item.field_label}`}
            >
              <Pencil className="h-3.5 w-3.5" />
            </button>
          </div>
        )}
      </td>

      {/* VDR Source */}
      <td className="px-4 py-3">
        <SourceDocumentLink
          docName={item.source_vdr_doc_name}
          location={item.source_location}
        />
      </td>

      {/* Confidence */}
      <td className="px-4 py-3">
        {item.confidence != null ? (
          <div className="flex items-center gap-2">
            <div className="w-16 h-1.5 bg-gray-100 rounded-full overflow-hidden">
              <div
                className={cn(
                  "h-full rounded-full transition-all",
                  confidenceColor(item.confidence),
                )}
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
        <div className="flex items-center gap-2">
          <span
            className={cn(
              "inline-flex px-2 py-0.5 text-[10px] font-semibold rounded-full whitespace-nowrap",
              ITEM_STATUS_COLORS[item.status],
            )}
          >
            {ITEM_STATUS_LABEL[item.status]}
          </span>
          {!isConfirmed && item.status !== "NOT_APPLICABLE" && (
            <Button
              variant="ghost"
              size="sm"
              onClick={handleConfirm}
              className="text-[10px] px-1.5 py-0.5 h-auto"
              disabled={isUpdating}
            >
              <Check className="h-3 w-3" />
            </Button>
          )}
        </div>
      </td>
    </tr>
  );
}

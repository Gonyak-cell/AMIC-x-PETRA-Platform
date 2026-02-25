import { useState } from "react";
import { CheckCircle, Edit3, AlertTriangle, MinusCircle, Clock } from "lucide-react";
import { Card, Badge, Button } from "@/components/ui";
import VdrSourceLinks from "./VdrSourceLinks";
import type {
  ChecklistItem,
  ChecklistItemStatus,
  ChecklistSeverity,
} from "@/modules/fdd/hooks/useChecklist";

interface Props {
  item: ChecklistItem;
  dealId: string;
  onUpdate: (
    itemId: string,
    status: ChecklistItemStatus,
    correction?: string,
    amount?: string
  ) => void;
  isUpdating?: boolean;
}

const STATUS_ICONS: Record<ChecklistItemStatus, typeof CheckCircle> = {
  AUTO_GENERATED: Clock,
  CONFIRMED: CheckCircle,
  CORRECTED: Edit3,
  FLAGGED: AlertTriangle,
  NOT_APPLICABLE: MinusCircle,
};

const STATUS_COLORS: Record<ChecklistItemStatus, string> = {
  AUTO_GENERATED: "bg-bg-cool text-text-secondary",
  CONFIRMED: "bg-positive/10 text-positive",
  CORRECTED: "bg-warning/10 text-warning",
  FLAGGED: "bg-negative/10 text-negative",
  NOT_APPLICABLE: "bg-bg-cool text-text-muted",
};

const SEVERITY_VARIANTS: Record<ChecklistSeverity, "error" | "warning" | "info" | "default"> = {
  HIGH: "error",
  MEDIUM: "warning",
  LOW: "info",
  INFO: "default",
};

export default function ChecklistItemCard({
  item,
  dealId,
  onUpdate,
  isUpdating,
}: Props) {
  const [expanded, setExpanded] = useState(false);
  const [correction, setCorrection] = useState(item.user_correction ?? "");
  const [amount, setAmount] = useState(item.user_amount ?? "");

  const StatusIcon = STATUS_ICONS[item.status];

  return (
    <Card padding="sm" className="border border-border-default">
      {/* Header row */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2 flex-1 min-w-0">
          <span className={`p-1 rounded ${STATUS_COLORS[item.status]}`}>
            <StatusIcon className="w-4 h-4" />
          </span>
          <div className="min-w-0">
            <p className="text-sm font-medium text-text-heading truncate">
              {item.title}
            </p>
            <p className="text-xs text-text-secondary mt-0.5">
              {item.description}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          {item.severity && (
            <Badge variant={SEVERITY_VARIANTS[item.severity]}>
              {item.severity}
            </Badge>
          )}
          <button
            onClick={() => setExpanded(!expanded)}
            className="text-xs text-accent-primary hover:underline"
          >
            {expanded ? "Collapse" : "Review"}
          </button>
        </div>
      </div>

      {/* Auto finding */}
      {item.auto_finding && (
        <div className="mt-2 px-7 text-xs text-text-body bg-bg-warm/50 rounded p-2">
          <span className="font-medium">Auto Finding:</span> {item.auto_finding}
          {item.auto_amount && (
            <span className="ml-2 font-mono text-accent-primary">
              ({Number(item.auto_amount).toLocaleString()})
            </span>
          )}
        </div>
      )}

      {/* VDR Source Links */}
      {item.vdr_links.length > 0 && (
        <div className="px-7">
          <VdrSourceLinks links={item.vdr_links} dealId={dealId} />
        </div>
      )}

      {/* Expanded review section */}
      {expanded && (
        <div className="mt-3 pt-3 border-t border-border-default space-y-3 px-7">
          {/* Status buttons */}
          <div className="flex flex-wrap gap-2">
            {(
              [
                "CONFIRMED",
                "CORRECTED",
                "FLAGGED",
                "NOT_APPLICABLE",
              ] as ChecklistItemStatus[]
            ).map((status) => {
              const Icon = STATUS_ICONS[status];
              return (
                <Button
                  key={status}
                  size="sm"
                  variant={item.status === status ? "primary" : "ghost"}
                  icon={Icon}
                  onClick={() => onUpdate(item.id, status, correction, amount)}
                  disabled={isUpdating}
                >
                  {status.replace(/_/g, " ")}
                </Button>
              );
            })}
          </div>

          {/* Correction input */}
          <div className="space-y-2">
            <label className="text-xs font-medium text-text-secondary">
              Correction Note
            </label>
            <textarea
              value={correction}
              onChange={(e) => setCorrection(e.target.value)}
              className="w-full rounded border border-border-default bg-bg-primary px-3 py-2 text-sm text-text-body focus:border-accent-primary focus:outline-none"
              rows={2}
              placeholder="Enter correction or note..."
            />
          </div>
          <div className="space-y-2">
            <label className="text-xs font-medium text-text-secondary">
              Corrected Amount
            </label>
            <input
              type="text"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              className="w-full rounded border border-border-default bg-bg-primary px-3 py-2 text-sm text-text-body font-mono focus:border-accent-primary focus:outline-none"
              placeholder="e.g., 1000000"
            />
          </div>
        </div>
      )}
    </Card>
  );
}

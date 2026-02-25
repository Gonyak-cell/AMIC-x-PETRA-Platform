import { KpiCard } from "@/components/ui";
import { CheckCircle, Edit3, AlertTriangle, Clock, MinusCircle } from "lucide-react";
import type { Checklist } from "@/modules/fdd/hooks/useChecklist";

interface Props {
  checklist: Checklist;
}

export default function ChecklistSummaryBar({ checklist }: Props) {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
      <KpiCard label="Total" value={checklist.total_items} icon={Clock} />
      <KpiCard label="Confirmed" value={checklist.confirmed_count} icon={CheckCircle} />
      <KpiCard label="Corrected" value={checklist.corrected_count} icon={Edit3} />
      <KpiCard label="Flagged" value={checklist.flagged_count} icon={AlertTriangle} />
      <KpiCard label="Pending" value={checklist.pending_count} icon={MinusCircle} />
    </div>
  );
}

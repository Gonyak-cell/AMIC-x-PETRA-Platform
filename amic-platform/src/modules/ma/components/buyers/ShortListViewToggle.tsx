import { LayoutGrid, Columns3, List } from "lucide-react";
import { cn } from "@/lib/cn";

export type ShortListViewMode = "grid" | "kanban" | "timeline";

interface ShortListViewToggleProps {
  viewMode: ShortListViewMode;
  onViewModeChange: (mode: ShortListViewMode) => void;
}

const VIEWS: {
  mode: ShortListViewMode;
  icon: typeof LayoutGrid;
  label: string;
}[] = [
  { mode: "grid", icon: LayoutGrid, label: "그리드" },
  { mode: "kanban", icon: Columns3, label: "칸반" },
  { mode: "timeline", icon: List, label: "타임라인" },
];

export default function ShortListViewToggle({
  viewMode,
  onViewModeChange,
}: ShortListViewToggleProps) {
  return (
    <div role="group" aria-label="뷰 전환" className="inline-flex rounded-md border border-gray-border bg-bg-cool p-0.5 gap-0.5">
      {VIEWS.map(({ mode, icon: Icon, label }) => (
        <button
          key={mode}
          type="button"
          onClick={() => onViewModeChange(mode)}
          title={label}
          aria-pressed={viewMode === mode}
          className={cn(
            "flex items-center gap-1 px-2 py-1 rounded text-xs transition-colors",
            viewMode === mode
              ? "bg-accent text-white shadow-sm font-medium"
              : "text-text-muted hover:text-text-dark",
          )}
        >
          <Icon className="h-3.5 w-3.5" />
          <span className="hidden sm:inline">{label}</span>
        </button>
      ))}
    </div>
  );
}

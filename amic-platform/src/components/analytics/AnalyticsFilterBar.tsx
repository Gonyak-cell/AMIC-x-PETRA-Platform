import { Button, Select } from "@/components/ui";
import type { SelectOption } from "@/components/ui";
import type { AnalyticsTimeRange, AnalyticsModule } from "@/types/analytics";

const TIME_RANGE_OPTIONS: SelectOption[] = [
  { value: "7d", label: "Last 7 Days" },
  { value: "30d", label: "Last 30 Days" },
  { value: "90d", label: "Last 90 Days" },
  { value: "1y", label: "Last Year" },
  { value: "all", label: "All Time" },
];

const MODULES: Array<{ value: AnalyticsModule | "all"; label: string }> = [
  { value: "all", label: "All Modules" },
  { value: "ma", label: "M&A" },
  { value: "fdd", label: "FDD" },
  { value: "kiis", label: "KIIS" },
  { value: "im", label: "IM" },
  { value: "docs", label: "Docs" },
];

interface AnalyticsFilterBarProps {
  timeRange: AnalyticsTimeRange;
  selectedModule: AnalyticsModule | "all";
  onTimeRangeChange: (range: AnalyticsTimeRange) => void;
  onModuleChange: (module: AnalyticsModule | "all") => void;
}

export function AnalyticsFilterBar({
  timeRange,
  selectedModule,
  onTimeRangeChange,
  onModuleChange,
}: AnalyticsFilterBarProps) {
  return (
    <div className="flex flex-wrap items-end gap-4">
      <div className="w-44">
        <Select
          label="Time Range"
          value={timeRange}
          onChange={(e) =>
            onTimeRangeChange(e.target.value as AnalyticsTimeRange)
          }
          options={TIME_RANGE_OPTIONS}
        />
      </div>
      <div className="flex gap-1">
        {MODULES.map((m) => (
          <Button
            key={m.value}
            variant={selectedModule === m.value ? "primary" : "ghost"}
            size="sm"
            onClick={() => onModuleChange(m.value)}
          >
            {m.label}
          </Button>
        ))}
      </div>
    </div>
  );
}

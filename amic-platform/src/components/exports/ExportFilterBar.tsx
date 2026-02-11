import { Select } from "@/components/ui";
import type { SelectOption } from "@/components/ui";
import type { ExportModule, ExportStatus } from "@/types/export";

const MODULE_OPTIONS: SelectOption[] = [
  { value: "", label: "All Modules" },
  { value: "fdd", label: "FDD" },
  { value: "kiis", label: "KIIS" },
  { value: "im", label: "IM" },
];

const STATUS_OPTIONS: SelectOption[] = [
  { value: "", label: "All Statuses" },
  { value: "pending", label: "Pending" },
  { value: "completed", label: "Completed" },
  { value: "failed", label: "Failed" },
  { value: "expired", label: "Expired" },
];

interface ExportFilterBarProps {
  module: ExportModule | undefined;
  status: ExportStatus | undefined;
  onModuleChange: (module: ExportModule | undefined) => void;
  onStatusChange: (status: ExportStatus | undefined) => void;
}

export function ExportFilterBar({
  module,
  status,
  onModuleChange,
  onStatusChange,
}: ExportFilterBarProps) {
  return (
    <div className="flex flex-wrap items-end gap-4">
      <div className="w-36">
        <Select
          label="Module"
          value={module ?? ""}
          onChange={(e) =>
            onModuleChange((e.target.value as ExportModule) || undefined)
          }
          options={MODULE_OPTIONS}
        />
      </div>
      <div className="w-36">
        <Select
          label="Status"
          value={status ?? ""}
          onChange={(e) =>
            onStatusChange((e.target.value as ExportStatus) || undefined)
          }
          options={STATUS_OPTIONS}
        />
      </div>
    </div>
  );
}

import { Download } from "lucide-react";
import { Button, Select, Input } from "@/components/ui";
import type { SelectOption } from "@/components/ui";
import type { ActivityLogFilter, ActivityModule, ActivityAction } from "@/types/activity";

const MODULE_OPTIONS: SelectOption[] = [
  { value: "", label: "All Modules" },
  { value: "fdd", label: "FDD" },
  { value: "kiis", label: "KIIS" },
  { value: "im", label: "IM" },
  { value: "portal", label: "Portal" },
];

const ACTION_OPTIONS: SelectOption[] = [
  { value: "", label: "All Actions" },
  { value: "create", label: "Create" },
  { value: "update", label: "Update" },
  { value: "delete", label: "Delete" },
  { value: "approve", label: "Approve" },
  { value: "reject", label: "Reject" },
  { value: "export", label: "Export" },
  { value: "login", label: "Login" },
  { value: "logout", label: "Logout" },
];

interface ActivityFilterBarProps {
  filters: ActivityLogFilter;
  onFilterChange: (filters: ActivityLogFilter) => void;
  userOptions: SelectOption[];
  onExport: () => void;
  isExporting?: boolean;
}

export function ActivityFilterBar({
  filters,
  onFilterChange,
  userOptions,
  onExport,
  isExporting,
}: ActivityFilterBarProps) {
  const update = (patch: Partial<ActivityLogFilter>) => {
    onFilterChange({ ...filters, ...patch, page: 1 });
  };

  return (
    <div className="flex flex-wrap items-end gap-4">
      <div className="w-44">
        <Select
          label="User"
          value={filters.user_id ?? ""}
          onChange={(e) => update({ user_id: e.target.value || undefined })}
          options={[{ value: "", label: "All Users" }, ...userOptions]}
        />
      </div>
      <div className="w-36">
        <Select
          label="Module"
          value={filters.module ?? ""}
          onChange={(e) =>
            update({ module: (e.target.value as ActivityModule) || undefined })
          }
          options={MODULE_OPTIONS}
        />
      </div>
      <div className="w-36">
        <Select
          label="Action"
          value={filters.action ?? ""}
          onChange={(e) =>
            update({ action: (e.target.value as ActivityAction) || undefined })
          }
          options={ACTION_OPTIONS}
        />
      </div>
      <div className="w-40">
        <Input
          label="From"
          type="date"
          value={filters.date_from ?? ""}
          onChange={(e) => update({ date_from: e.target.value || undefined })}
        />
      </div>
      <div className="w-40">
        <Input
          label="To"
          type="date"
          value={filters.date_to ?? ""}
          onChange={(e) => update({ date_to: e.target.value || undefined })}
        />
      </div>
      <div className="ml-auto">
        <Button
          variant="ghost"
          size="sm"
          icon={Download}
          onClick={onExport}
          loading={isExporting}
        >
          Export CSV
        </Button>
      </div>
    </div>
  );
}

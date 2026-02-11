import { useState, useMemo } from "react";
import {
  ClipboardList,
  Activity,
  Users,
  Download,
  List,
  Clock,
} from "lucide-react";
import { toast } from "sonner";
import { useAuth } from "@/hooks/useAuth";
import { useActivityLog, useActivityExport } from "@/hooks/useActivityLog";
import { useUsers } from "@/hooks/useUsers";
import {
  Card,
  KpiCard,
  Button,
  Badge,
  DataTable,
  EmptyState,
  Spinner,
} from "@/components/ui";
import type { Column, SelectOption } from "@/components/ui";
import { ActivityFilterBar } from "@/components/activity/ActivityFilterBar";
import { ActivityTimeline } from "@/components/activity/ActivityTimeline";
import type { ActivityLogFilter, ActivityLogItem } from "@/types/activity";
import { formatDate } from "@/lib/format";

type ViewMode = "table" | "timeline";

const ACTION_BADGE_VARIANT: Record<string, "success" | "warning" | "error" | "info" | "neutral"> = {
  create: "success",
  update: "info",
  delete: "error",
  approve: "success",
  reject: "error",
  export: "info",
  login: "neutral",
  logout: "neutral",
  view: "neutral",
};

export default function ActivityLogPage() {
  const { hasPermission } = useAuth();
  const [filters, setFilters] = useState<ActivityLogFilter>({
    page: 1,
    size: 20,
  });
  const [viewMode, setViewMode] = useState<ViewMode>("table");
  const [isExporting, setIsExporting] = useState(false);

  const { data: activityData, isLoading } = useActivityLog(filters);
  const { data: users = [] } = useUsers();
  const exportFn = useActivityExport();

  const userOptions: SelectOption[] = useMemo(
    () =>
      users.map((u) => ({
        value: u.id,
        label: u.display_name,
      })),
    [users],
  );

  // KPI calculations
  const items = activityData?.items ?? [];
  const today = new Date().toISOString().slice(0, 10);
  const todayCount = items.filter((i) => i.created_at.startsWith(today)).length;
  const totalCount = activityData?.total ?? 0;
  const uniqueUsers = new Set(items.map((i) => i.user_id)).size;

  const handleExport = async () => {
    setIsExporting(true);
    try {
      // Client-side CSV generation as fallback
      const rows = items.map((item) =>
        [
          item.created_at,
          item.user_name,
          item.module,
          item.action,
          item.entity_type,
          item.entity_name ?? "",
          item.description,
        ].join(","),
      );
      const csv = [
        "Timestamp,User,Module,Action,Entity Type,Entity Name,Description",
        ...rows,
      ].join("\n");

      const blob = new Blob([csv], { type: "text/csv" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `activity-log-${today}.csv`;
      a.click();
      URL.revokeObjectURL(url);

      toast.success("Activity log exported");
    } catch {
      // Try server-side export as fallback
      try {
        await exportFn(filters);
        toast.success("Activity log exported");
      } catch {
        toast.error("Export not available");
      }
    } finally {
      setIsExporting(false);
    }
  };

  // Access control
  if (!hasPermission("audit:view")) {
    return (
      <div className="flex items-center justify-center py-20">
        <EmptyState
          icon={ClipboardList}
          title="Access Denied"
          description="You do not have permission to view the activity log."
        />
      </div>
    );
  }

  const columns: Column<ActivityLogItem>[] = [
    {
      key: "created_at",
      header: "Time",
      width: "160px",
      render: (row) => (
        <span className="text-text-secondary text-xs">
          {formatDate(row.created_at, "short")}{" "}
          {new Date(row.created_at).toLocaleTimeString("en-US", {
            hour: "2-digit",
            minute: "2-digit",
          })}
        </span>
      ),
    },
    {
      key: "user_name",
      header: "User",
      width: "140px",
      render: (row) => (
        <span className="font-medium text-text-dark">{row.user_name}</span>
      ),
    },
    {
      key: "module",
      header: "Module",
      width: "90px",
      align: "center",
      render: (row) => (
        <Badge
          variant={
            row.module === "fdd"
              ? "info"
              : row.module === "kiis"
                ? "success"
                : row.module === "im"
                  ? "warning"
                  : "neutral"
          }
          className="text-xs uppercase"
        >
          {row.module}
        </Badge>
      ),
    },
    {
      key: "action",
      header: "Action",
      width: "100px",
      align: "center",
      render: (row) => (
        <Badge
          variant={ACTION_BADGE_VARIANT[row.action] ?? "neutral"}
          className="text-xs"
        >
          {row.action}
        </Badge>
      ),
    },
    {
      key: "description",
      header: "Description",
      render: (row) => (
        <div className="min-w-0">
          <div className="text-sm text-text-body truncate">
            {row.description}
          </div>
          {row.entity_name && (
            <div className="text-xs text-text-secondary truncate">
              {row.entity_type}: {row.entity_name}
            </div>
          )}
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-heading font-bold text-text-dark">
            Activity Log
          </h1>
          <p className="text-text-secondary mt-1">
            Audit trail for compliance and accountability
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant={viewMode === "table" ? "accent" : "ghost"}
            size="sm"
            icon={List}
            onClick={() => setViewMode("table")}
            aria-label="Table view"
          />
          <Button
            variant={viewMode === "timeline" ? "accent" : "ghost"}
            size="sm"
            icon={Clock}
            onClick={() => setViewMode("timeline")}
            aria-label="Timeline view"
          />
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard
          label="Total Activities"
          value={String(totalCount)}
          icon={ClipboardList}
        />
        <KpiCard
          label="Today"
          value={String(todayCount)}
          icon={Activity}
          variant={todayCount > 0 ? "positive" : "default"}
        />
        <KpiCard
          label="Active Users"
          value={String(uniqueUsers)}
          icon={Users}
        />
        <KpiCard
          label="Export"
          value="CSV"
          icon={Download}
        />
      </div>

      {/* Filters */}
      <Card padding="sm">
        <ActivityFilterBar
          filters={filters}
          onFilterChange={setFilters}
          userOptions={userOptions}
          onExport={handleExport}
          isExporting={isExporting}
        />
      </Card>

      {/* Content */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Spinner size="lg" />
        </div>
      ) : viewMode === "table" ? (
        <Card title="Activity Records" headerBar padding="none">
          {items.length === 0 ? (
            <EmptyState
              icon={ClipboardList}
              title="No activities found"
              description="No activity records match your current filters. Activities will appear here as users interact with the platform."
            />
          ) : (
            <DataTable
              columns={columns}
              data={items}
              keyField="id"
              striped
            />
          )}
        </Card>
      ) : (
        <Card title="Activity Timeline" headerBar>
          <ActivityTimeline items={items} />
        </Card>
      )}

      {/* Pagination info */}
      {activityData && items.length > 0 && (
        <div className="flex items-center justify-between text-sm text-text-secondary">
          <span>
            Showing {items.length} of {activityData.total} activities
          </span>
          <div className="flex gap-2">
            <Button
              variant="ghost"
              size="sm"
              disabled={(filters.page ?? 1) <= 1}
              onClick={() =>
                setFilters((f) => ({ ...f, page: (f.page ?? 1) - 1 }))
              }
            >
              Previous
            </Button>
            <Button
              variant="ghost"
              size="sm"
              disabled={items.length < (filters.size ?? 20)}
              onClick={() =>
                setFilters((f) => ({ ...f, page: (f.page ?? 1) + 1 }))
              }
            >
              Next
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}

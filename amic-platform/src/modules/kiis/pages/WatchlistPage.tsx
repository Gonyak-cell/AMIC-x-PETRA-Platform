import { Eye, Bell, Trash2 } from "lucide-react";
import { toast } from "sonner";
import {
  useWatchlist,
  useRemoveFromWatchlist,
  useAlerts,
  useMarkAlertRead,
  useUnreadAlertCount,
} from "@/modules/kiis/hooks/useWatchlist";
import { Card, DataTable, Badge, Button, EmptyState, Spinner } from "@/components/ui";
import type { Column } from "@/components/ui";
import type { WatchlistItem, Alert } from "@/modules/kiis/types/watchlist";
import { formatDate } from "@/lib/format";
import { cn } from "@/lib/cn";

const alertTypeVariant: Record<string, "error" | "warning" | "info" | "neutral"> = {
  sanction: "error",
  reputation: "warning",
  news: "info",
  disclosure: "neutral",
};

export default function WatchlistPage() {
  const { data: watchlist, isLoading: wlLoading } = useWatchlist();
  const { data: alerts, isLoading: alertsLoading } = useAlerts();
  const { data: unread } = useUnreadAlertCount();
  const removeItem = useRemoveFromWatchlist();
  const markRead = useMarkAlertRead();

  const handleRemove = (companyId: string) => {
    removeItem.mutate(companyId, {
      onSuccess: () => toast.success("Removed from watchlist"),
      onError: () => toast.error("Failed to remove"),
    });
  };

  const handleMarkRead = (alertId: string) => {
    markRead.mutate(alertId);
  };

  const watchlistColumns: Column<WatchlistItem>[] = [
    {
      key: "corp_name",
      header: "Company",
      render: (row) => (
        <span className="font-medium text-text-dark">{row.corp_name}</span>
      ),
    },
    {
      key: "alert_types",
      header: "Alerts",
      render: (row) => (
        <div className="flex gap-1 flex-wrap">
          {row.alert_types.map((t) => (
            <Badge key={t} variant={alertTypeVariant[t] ?? "neutral"}>
              {t}
            </Badge>
          ))}
        </div>
      ),
    },
    {
      key: "added_at",
      header: "Added",
      align: "center",
      width: "120px",
      render: (row) => formatDate(row.added_at, "short"),
    },
    {
      key: "actions",
      header: "",
      align: "center",
      width: "60px",
      render: (row) => (
        <Button
          variant="ghost"
          size="sm"
          icon={Trash2}
          onClick={(e) => {
            e.stopPropagation();
            handleRemove(row.company_id);
          }}
        />
      ),
    },
  ];

  const alertColumns: Column<Alert>[] = [
    {
      key: "type",
      header: "Type",
      width: "100px",
      render: (row) => (
        <Badge variant={alertTypeVariant[row.type] ?? "neutral"}>
          {row.type}
        </Badge>
      ),
    },
    {
      key: "message",
      header: "Message",
      render: (row) => (
        <span className={cn(!row.is_read && "font-medium text-text-dark")}>
          {row.message}
        </span>
      ),
    },
    { key: "company_name", header: "Company", width: "140px" },
    {
      key: "created_at",
      header: "Date",
      align: "center",
      width: "120px",
      render: (row) => formatDate(row.created_at, "short"),
    },
    {
      key: "is_read",
      header: "Status",
      align: "center",
      width: "80px",
      render: (row) =>
        row.is_read ? (
          <span className="text-xs text-text-secondary">Read</span>
        ) : (
          <button
            className="text-xs text-accent hover:underline"
            onClick={(e) => {
              e.stopPropagation();
              handleMarkRead(row.id);
            }}
          >
            Mark read
          </button>
        ),
    },
  ];

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-heading font-bold text-text-dark">
        Watchlist
      </h1>

      {/* Watchlist */}
      <Card title="Watched Companies" headerBar padding="none">
        {wlLoading ? (
          <Spinner />
        ) : !watchlist?.length ? (
          <EmptyState
            icon={Eye}
            title="Watchlist empty"
            description="Add companies from their detail pages to start monitoring."
          />
        ) : (
          <DataTable
            columns={watchlistColumns}
            data={watchlist}
            keyField="id"
            striped
          />
        )}
      </Card>

      {/* Alerts */}
      <Card
        title={`Alert History${unread && unread.count > 0 ? ` (${unread.count} unread)` : ""}`}
        headerBar
        padding="none"
      >
        {alertsLoading ? (
          <Spinner />
        ) : !alerts?.length ? (
          <EmptyState
            icon={Bell}
            title="No alerts"
            description="Alerts will appear when changes are detected for watched companies."
          />
        ) : (
          <DataTable
            columns={alertColumns}
            data={alerts}
            keyField="id"
            striped
          />
        )}
      </Card>
    </div>
  );
}

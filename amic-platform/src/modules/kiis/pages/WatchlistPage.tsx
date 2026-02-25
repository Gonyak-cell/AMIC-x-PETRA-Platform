import { useState, useMemo, useCallback } from "react";
import { Eye, Bell, Trash2 } from "lucide-react";
import { toast } from "sonner";
import {
  useWatchlist,
  useRemoveFromWatchlist,
  useAlerts,
  useMarkAlertRead,
  useUnreadAlertCount,
} from "@/modules/kiis/hooks/useWatchlist";
import { Card, DataTable, Badge, Button, EmptyState, Spinner, Pagination, PageHero } from "@/components/ui";
import type { Column } from "@/components/ui";
import type { WatchlistItem, Alert } from "@/modules/kiis/types/watchlist";
import { formatDate } from "@/lib/format";
import { cn } from "@/lib/cn";
import heroImg from "@/assets/images/forest-bg.jpg";

const alertTypeVariant: Record<string, "error" | "warning" | "info" | "neutral"> = {
  sanction: "error",
  reputation: "warning",
  reputation_change: "warning",
  news: "info",
  disclosure: "neutral",
  new_disclosure: "neutral",
};

export default function WatchlistPage() {
  const [alertPage, setAlertPage] = useState(1);
  const [removingId, setRemovingId] = useState<number | null>(null);
  const { data: watchlistData, isLoading: wlLoading } = useWatchlist();
  const watchlist = watchlistData?.items;
  const { data: alertsData, isLoading: alertsLoading } = useAlerts({ page: alertPage, size: 20 });
  const alerts = alertsData?.items;
  const alertTotalPages = alertsData ? Math.ceil(alertsData.total / 20) : 0;
  const { data: unread } = useUnreadAlertCount();
  const removeItem = useRemoveFromWatchlist();
  const markRead = useMarkAlertRead();

  const handleRemove = useCallback((companyId: number) => {
    setRemovingId(companyId);
    removeItem.mutate(companyId, {
      onSuccess: () => { toast.success("Removed from watchlist"); setRemovingId(null); },
      onError: () => { toast.error("Failed to remove"); setRemovingId(null); },
    });
  }, [removeItem]);

  const handleMarkRead = useCallback((alertId: number) => {
    markRead.mutate(alertId);
  }, [markRead]);

  const watchlistColumns: Column<WatchlistItem>[] = useMemo(() => [
    {
      key: "company_name",
      header: "Company",
      render: (row: WatchlistItem) => (
        <span className="font-medium text-text-dark">
          {row.company_name ?? "-"}
        </span>
      ),
    },
    {
      key: "alert_types",
      header: "Alerts",
      render: (row: WatchlistItem) => (
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
      key: "created_at",
      header: "Added",
      align: "center" as const,
      width: "120px",
      render: (row: WatchlistItem) => formatDate(row.created_at, "short"),
    },
    {
      key: "actions",
      header: "",
      align: "center" as const,
      width: "60px",
      render: (row: WatchlistItem) => (
        <Button
          variant="ghost"
          size="sm"
          icon={Trash2}
          onClick={(e) => {
            e.stopPropagation();
            handleRemove(row.company_id);
          }}
          loading={removingId === row.company_id}
        />
      ),
    },
  ], [removingId, handleRemove]);

  const alertColumns: Column<Alert>[] = useMemo(() => [
    {
      key: "alert_type",
      header: "Type",
      width: "100px",
      render: (row: Alert) => (
        <Badge variant={alertTypeVariant[row.alert_type] ?? "neutral"}>
          {row.alert_type}
        </Badge>
      ),
    },
    {
      key: "title",
      header: "Title",
      render: (row: Alert) => (
        <span className={cn(!row.is_read && "font-medium text-text-dark")}>
          {row.title}
        </span>
      ),
    },
    {
      key: "message",
      header: "Message",
      render: (row: Alert) => (
        <span className="text-text-secondary text-sm">
          {row.message ?? "-"}
        </span>
      ),
    },
    {
      key: "company_name",
      header: "Company",
      width: "140px",
      render: (row: Alert) => row.company_name ?? "-",
    },
    {
      key: "created_at",
      header: "Date",
      align: "center" as const,
      width: "120px",
      render: (row: Alert) => formatDate(row.created_at, "short"),
    },
    {
      key: "is_read",
      header: "Status",
      align: "center" as const,
      width: "80px",
      render: (row: Alert) =>
        row.is_read ? (
          <span className="text-xs text-text-secondary">Read</span>
        ) : (
          <button
            aria-label={`Mark "${row.title}" as read`}
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
  ], [handleMarkRead]);

  return (
    <div className="space-y-6">
      <PageHero
        title="Watchlist"
        subtitle="Monitor companies and receive alerts"
        compact
        backgroundImage={heroImg}
        backgroundOpacity={0.18}
      />

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

      {alertTotalPages > 1 && (
        <Pagination page={alertPage} totalPages={alertTotalPages} onPageChange={setAlertPage} />
      )}
    </div>
  );
}

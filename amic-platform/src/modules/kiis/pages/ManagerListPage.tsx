import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { UserSearch, Radar } from "lucide-react";
import { toast } from "sonner";
import {
  useManagerMovements,
  useTrackManagers,
} from "@/modules/kiis/hooks/useManagers";
import {
  Card,
  DataTable,
  Input,
  Button,
  Badge,
  EmptyState,
  Spinner,
} from "@/components/ui";
import type { Column } from "@/components/ui";
import type { ManagerMovement } from "@/modules/kiis/types/manager";
import { formatDate } from "@/lib/format";

const movementVariant: Record<string, "info" | "warning" | "success"> = {
  transfer: "info",
  resignation: "warning",
  appointment: "success",
};

const columns: Column<ManagerMovement>[] = [
  {
    key: "manager_name",
    header: "Name",
    render: (row) => (
      <span className="font-medium text-text-dark">{row.manager_name}</span>
    ),
  },
  {
    key: "from_company_name",
    header: "From",
    render: (row) => row.from_company_name ?? "-",
  },
  {
    key: "to_company_name",
    header: "To",
    render: (row) => row.to_company_name ?? "-",
  },
  {
    key: "movement_type",
    header: "Type",
    align: "center",
    width: "120px",
    render: (row) => (
      <Badge variant={movementVariant[row.movement_type] ?? "neutral"}>
        {row.movement_type}
      </Badge>
    ),
  },
  {
    key: "detected_at",
    header: "Detected",
    align: "center",
    width: "120px",
    render: (row) => formatDate(row.detected_at, "short"),
  },
  {
    key: "source",
    header: "Source",
    align: "center",
    width: "80px",
    render: (row) => row.source?.toUpperCase() ?? "-",
  },
];

export default function ManagerListPage() {
  const navigate = useNavigate();
  const [nameSearch, setNameSearch] = useState("");
  const [page, setPage] = useState(1);

  const { data, isLoading } = useManagerMovements({
    manager_name: nameSearch || undefined,
    page,
    size: 20,
  });
  const trackManagers = useTrackManagers();

  const handleTrack = () => {
    trackManagers.mutate(undefined, {
      onSuccess: (res) =>
        toast.success(
          `Scanned ${res.scanned_count}, found ${res.new_movements_count} new movements`,
        ),
      onError: () => toast.error("Tracking failed"),
    });
  };

  const totalPages = data ? Math.ceil(data.total / 20) : 0;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-heading font-bold text-text-dark">
          Manager Movements
        </h1>
        <Button
          variant="secondary"
          icon={Radar}
          onClick={handleTrack}
          loading={trackManagers.isPending}
        >
          Track
        </Button>
      </div>

      <div className="max-w-sm">
        <Input
          label="Search by Name"
          placeholder="Enter manager name..."
          value={nameSearch}
          onChange={(e) => {
            setNameSearch(e.target.value);
            setPage(1);
          }}
        />
      </div>

      <Card padding="none">
        {isLoading ? (
          <Spinner />
        ) : !data?.items.length ? (
          <EmptyState
            icon={UserSearch}
            title="No movements found"
            description="No manager movements match your search."
          />
        ) : (
          <DataTable
            columns={columns}
            data={data.items}
            keyField="id"
            onRowClick={(row) =>
              navigate(
                `/kiis/managers/${encodeURIComponent(row.manager_name)}`,
              )
            }
            striped
          />
        )}
      </Card>

      {totalPages > 1 && (
        <div className="flex justify-center gap-3">
          <Button
            variant="ghost"
            size="sm"
            disabled={page <= 1}
            onClick={() => setPage((p) => p - 1)}
          >
            Previous
          </Button>
          <span className="text-sm text-text-secondary self-center">
            {page} / {totalPages}
          </span>
          <Button
            variant="ghost"
            size="sm"
            disabled={page >= totalPages}
            onClick={() => setPage((p) => p + 1)}
          >
            Next
          </Button>
        </div>
      )}
    </div>
  );
}

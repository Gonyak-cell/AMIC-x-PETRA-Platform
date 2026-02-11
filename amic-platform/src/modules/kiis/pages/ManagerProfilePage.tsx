import { useParams, Link } from "react-router-dom";
import { UserSearch, Briefcase, Clock, Tag } from "lucide-react";
import { useManagerProfile } from "@/modules/kiis/hooks/useManagers";
import {
  Card,
  KpiCard,
  DataTable,
  Badge,
  EmptyState,
  Spinner,
} from "@/components/ui";
import type { Column } from "@/components/ui";
import type {
  ManagerMovement,
  ManagerDeal,
} from "@/modules/kiis/types/manager";
import { formatDate } from "@/lib/format";

const movementVariant: Record<string, "info" | "warning" | "success"> = {
  transfer: "info",
  resignation: "warning",
  appointment: "success",
};

const movementColumns: Column<ManagerMovement>[] = [
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
    header: "Date",
    align: "center",
    width: "120px",
    render: (row) => formatDate(row.detected_at, "short"),
  },
];

const dealColumns: Column<ManagerDeal>[] = [
  {
    key: "target_company",
    header: "Company",
    render: (row) => (
      <span className="font-medium text-text-dark">{row.target_company}</span>
    ),
  },
  {
    key: "amount_display",
    header: "Amount",
    align: "right",
    width: "140px",
    render: (row) => row.amount_display ?? "-",
  },
  {
    key: "round_stage",
    header: "Stage",
    width: "120px",
    render: (row) => row.round_stage ?? "-",
  },
  {
    key: "sector",
    header: "Sector",
    width: "140px",
    render: (row) => row.sector ?? "-",
  },
];

export default function ManagerProfilePage() {
  const { managerName } = useParams<{ managerName: string }>();
  const decodedName = decodeURIComponent(managerName ?? "");
  const { data: profile, isLoading } = useManagerProfile(decodedName);

  if (isLoading) return <Spinner />;
  if (!profile) {
    return (
      <EmptyState
        icon={UserSearch}
        title="Manager not found"
        description="Could not find the requested manager profile."
      />
    );
  }

  return (
    <div className="space-y-6">
      {/* Breadcrumb */}
      <div className="text-sm text-text-secondary">
        <Link to="/kiis/managers" className="hover:text-accent">
          Managers
        </Link>
        <span className="mx-2">/</span>
        <span className="text-text-dark">{profile.manager_name}</span>
      </div>

      {/* Header */}
      <div>
        <h1 className="text-2xl font-heading font-bold text-text-dark">
          {profile.manager_name}
        </h1>
        <div className="mt-1 flex gap-4 text-sm text-text-secondary">
          {profile.current_company && (
            <span>Company: {profile.current_company}</span>
          )}
          {profile.current_fund && <span>Fund: {profile.current_fund}</span>}
        </div>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <KpiCard
          label="Deals Involved"
          value={String(profile.total_deals_involved)}
          icon={Briefcase}
        />
        <KpiCard
          label="Career Years"
          value={profile.career_years != null ? String(profile.career_years) : "-"}
          icon={Clock}
        />
        <KpiCard
          label="Specialties"
          value={String(profile.specialty_sectors.length)}
          icon={Tag}
        />
      </div>

      {/* Specialty Sectors */}
      {profile.specialty_sectors.length > 0 && (
        <div className="flex gap-2 flex-wrap">
          {profile.specialty_sectors.map((sector) => (
            <Badge key={sector} variant="info">
              {sector}
            </Badge>
          ))}
        </div>
      )}

      {/* Career Movements */}
      <Card padding="none">
        <div className="px-5 py-3 border-b border-gray-border">
          <h2 className="text-base font-heading font-semibold text-text-dark">
            Career Movements
          </h2>
        </div>
        {profile.movements.length === 0 ? (
          <EmptyState
            icon={UserSearch}
            title="No movements"
            description="No career movements recorded."
          />
        ) : (
          <DataTable
            columns={movementColumns}
            data={profile.movements}
            keyField="id"
            striped
            compact
          />
        )}
      </Card>

      {/* Related Deals */}
      <Card padding="none">
        <div className="px-5 py-3 border-b border-gray-border">
          <h2 className="text-base font-heading font-semibold text-text-dark">
            Related Deals
          </h2>
        </div>
        {profile.deals.length === 0 ? (
          <EmptyState
            icon={Briefcase}
            title="No deals"
            description="No deals associated with this manager."
          />
        ) : (
          <DataTable
            columns={dealColumns}
            data={profile.deals}
            keyField="id"
            striped
            compact
          />
        )}
      </Card>
    </div>
  );
}

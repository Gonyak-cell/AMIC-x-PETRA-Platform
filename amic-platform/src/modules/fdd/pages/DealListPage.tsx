import { useState, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { Briefcase, CheckCircle, FileEdit, Archive, Plus } from "lucide-react";
import { toast } from "sonner";
import { useDeals, useCreateDeal } from "@/modules/fdd/hooks/useDeals";
import type { DealCreate, DealType, Deal } from "@/modules/fdd/types/deal";
import {
  Button,
  Card,
  KpiCard,
  DataTable,
  Modal,
  Input,
  Select,
  Badge,
  getStatusVariant,
  EmptyState,
} from "@/components/ui";
import type { Column } from "@/components/ui";
import { formatDate } from "@/lib/format";
import { TeamAvatars } from "@/components/collaboration/TeamAvatars";
import { useTeamMembers } from "@/hooks/useTeamMembers";

const INITIAL_FORM: DealCreate = {
  name: "",
  deal_type: "COMPLETION_ACCOUNTS",
  base_currency: "KRW",
  reference_date: "",
  period_start: "",
  period_end: "",
};

const DEAL_TYPE_OPTIONS = [
  { value: "COMPLETION_ACCOUNTS", label: "Completion Accounts" },
  { value: "LOCKED_BOX", label: "Locked Box" },
];

const CURRENCY_OPTIONS = [
  { value: "KRW", label: "KRW" },
  { value: "USD", label: "USD" },
  { value: "EUR", label: "EUR" },
  { value: "JPY", label: "JPY" },
];

export default function DealListPage() {
  const navigate = useNavigate();
  const { data: deals, isLoading } = useDeals();
  const createDeal = useCreateDeal();
  const { members } = useTeamMembers();
  const [showModal, setShowModal] = useState(false);
  const [form, setForm] = useState<DealCreate>(INITIAL_FORM);

  // KPI 계산
  const kpis = useMemo(() => {
    if (!deals) return { total: 0, active: 0, draft: 0, archived: 0 };
    return {
      total: deals.length,
      active: deals.filter((d) => d.status === "ACTIVE").length,
      draft: deals.filter((d) => d.status === "DRAFT").length,
      archived: deals.filter((d) => d.status === "ARCHIVED").length,
    };
  }, [deals]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    createDeal.mutate(form, {
      onSuccess: () => {
        toast.success("Deal created successfully");
        setForm(INITIAL_FORM);
        setShowModal(false);
      },
      onError: () => {
        toast.error("Failed to create deal");
      },
    });
  };

  const handleRowClick = (deal: Deal) => {
    navigate(`/deals/${deal.id}`);
  };

  // DataTable 컬럼 정의
  const columns: Column<Deal>[] = [
    {
      key: "name",
      header: "Deal Name",
      render: (row) => (
        <span className="font-medium text-text-dark">{row.name}</span>
      ),
    },
    {
      key: "deal_type",
      header: "Type",
      render: (row) => (
        <span>
          {row.deal_type === "COMPLETION_ACCOUNTS"
            ? "Completion Accounts"
            : "Locked Box"}
        </span>
      ),
    },
    {
      key: "base_currency",
      header: "Currency",
      align: "center",
      width: "100px",
    },
    {
      key: "reference_date",
      header: "Reference Date",
      align: "center",
      width: "140px",
      render: (row) => formatDate(row.reference_date, "month"),
    },
    {
      key: "team_partner_id",
      header: "Team",
      width: "120px",
      render: (row) => {
        const teamIds = [row.team_partner_id, row.team_manager_id].filter(
          Boolean,
        ) as string[];
        const teamMembers = teamIds
          .map((id) => members.find((m) => m.user_id === id))
          .filter(Boolean) as typeof members;
        return <TeamAvatars members={teamMembers} max={3} />;
      },
    },
    {
      key: "status",
      header: "Status",
      align: "center",
      width: "100px",
      render: (row) => (
        <Badge variant={getStatusVariant(row.status)}>{row.status}</Badge>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-heading font-bold text-text-dark">
          Deals
        </h1>
        <Button
          variant="accent"
          icon={Plus}
          onClick={() => setShowModal(true)}
        >
          New Deal
        </Button>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard
          label="Total Deals"
          value={String(kpis.total)}
          icon={Briefcase}
        />
        <KpiCard
          label="Active"
          value={String(kpis.active)}
          icon={CheckCircle}
          variant="positive"
        />
        <KpiCard
          label="Draft"
          value={String(kpis.draft)}
          icon={FileEdit}
          variant="caution"
        />
        <KpiCard
          label="Archived"
          value={String(kpis.archived)}
          icon={Archive}
        />
      </div>

      {/* Deal Table */}
      <Card title="All Deals" headerBar padding="none">
        {!isLoading && (!deals || deals.length === 0) ? (
          <EmptyState
            icon={Briefcase}
            title="No deals yet"
            description="Create your first deal to get started with FDD analysis."
            actionLabel="Create Deal"
            onAction={() => setShowModal(true)}
          />
        ) : (
          <DataTable
            columns={columns}
            data={deals || []}
            keyField="id"
            loading={isLoading}
            onRowClick={handleRowClick}
            striped
          />
        )}
      </Card>

      {/* Create Deal Modal */}
      <Modal
        open={showModal}
        onClose={() => setShowModal(false)}
        title="Create New Deal"
        size="md"
        footer={
          <>
            <Button variant="ghost" onClick={() => setShowModal(false)}>
              Cancel
            </Button>
            <Button
              variant="accent"
              onClick={handleSubmit}
              loading={createDeal.isPending}
            >
              Create Deal
            </Button>
          </>
        }
      >
        <form onSubmit={handleSubmit} className="space-y-4">
          <Input
            label="Deal Name"
            required
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            placeholder="Project Alpha"
          />

          <div className="grid grid-cols-2 gap-4">
            <Select
              label="Deal Type"
              options={DEAL_TYPE_OPTIONS}
              value={form.deal_type}
              onChange={(e) =>
                setForm({ ...form, deal_type: e.target.value as DealType })
              }
            />
            <Select
              label="Currency"
              options={CURRENCY_OPTIONS}
              value={form.base_currency}
              onChange={(e) =>
                setForm({ ...form, base_currency: e.target.value })
              }
            />
          </div>

          <Input
            label="Reference Date"
            type="date"
            required
            value={form.reference_date}
            onChange={(e) =>
              setForm({ ...form, reference_date: e.target.value })
            }
          />

          <div className="grid grid-cols-2 gap-4">
            <Input
              label="Period Start"
              type="date"
              required
              value={form.period_start}
              onChange={(e) =>
                setForm({ ...form, period_start: e.target.value })
              }
            />
            <Input
              label="Period End"
              type="date"
              required
              value={form.period_end}
              onChange={(e) =>
                setForm({ ...form, period_end: e.target.value })
              }
            />
          </div>
        </form>
      </Modal>
    </div>
  );
}

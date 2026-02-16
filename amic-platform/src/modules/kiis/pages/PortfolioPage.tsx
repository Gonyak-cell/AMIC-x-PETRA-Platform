import { useState } from "react";
import {
  Activity,
  RefreshCw,
  ShieldCheck,
  Pencil,
} from "lucide-react";
import { toast } from "sonner";
import {
  usePortfolio,
  usePortfolioSummary,
  useSyncPortfolio,
  useCheckSurvival,
  useUpdateValuation,
} from "@/modules/kiis/hooks/usePortfolio";
import {
  Card,
  KpiCard,
  DataTable,
  Select,
  Button,
  Badge,
  EmptyState,
  Spinner,
  Pagination,
  PageHero,
} from "@/components/ui";
import type { Column } from "@/components/ui";
import type {
  PortfolioItem,
  SurvivalStatus,
} from "@/modules/kiis/types/portfolio";
import { formatAmount, formatDate } from "@/lib/format";
import CorpCodeInput from "@/modules/kiis/components/CorpCodeInput";
import ValuationModal from "@/modules/kiis/components/ValuationModal";

const STATUS_OPTIONS = [
  { value: "", label: "All Status" },
  { value: "active", label: "Active" },
  { value: "audit_missing", label: "Audit Missing" },
  { value: "dissolved", label: "Dissolved" },
  { value: "unicorn", label: "Unicorn" },
  { value: "unknown", label: "Unknown" },
];

const statusVariant: Record<string, "success" | "warning" | "error" | "info" | "neutral"> = {
  active: "success",
  audit_missing: "warning",
  dissolved: "error",
  unicorn: "info",
  unknown: "neutral",
};

export default function PortfolioPage() {
  const [corpCode, setCorpCode] = useState("");
  const [status, setStatus] = useState<SurvivalStatus | "">("");
  const [page, setPage] = useState(1);
  const [modalItem, setModalItem] = useState<PortfolioItem | null>(null);
  const [checkingId, setCheckingId] = useState<number | null>(null);

  const { data, isLoading } = usePortfolio(corpCode, {
    status: status || undefined,
    page,
    size: 20,
  });
  const { data: summary } = usePortfolioSummary(corpCode);
  const syncPortfolio = useSyncPortfolio(corpCode);
  const checkSurvival = useCheckSurvival(corpCode);
  const updateValuation = useUpdateValuation(corpCode);

  const handleSearch = (code: string) => {
    setCorpCode(code);
    setPage(1);
  };

  const handleSync = () => {
    if (!corpCode) return;
    syncPortfolio.mutate(undefined, {
      onSuccess: (res) => toast.success(`Synced ${res.synced_count} items`),
      onError: () => toast.error("Sync failed"),
    });
  };

  const handleCheckSurvival = (item: PortfolioItem) => {
    setCheckingId(item.id);
    checkSurvival.mutate(item.id, {
      onSuccess: (res) => {
        toast.success(
          `${item.target_company_name}: ${res.previous_status} → ${res.new_status}`,
        );
        setCheckingId(null);
      },
      onError: () => {
        toast.error("Survival check failed");
        setCheckingId(null);
      },
    });
  };

  const handleUpdateValuation = (portfolioId: number, valuation: string) => {
    updateValuation.mutate(
      { portfolioId, body: { estimated_valuation: valuation } },
      {
        onSuccess: (res) => {
          toast.success(
            res.is_newly_unicorn
              ? `${res.target_company_name} is now a Unicorn!`
              : "Valuation updated",
          );
          setModalItem(null);
        },
        onError: () => toast.error("Update failed"),
      },
    );
  };

  const columns: Column<PortfolioItem>[] = [
    {
      key: "target_company_name",
      header: "Company",
      render: (row) => (
        <span className="font-medium text-text-dark">
          {row.target_company_name}
        </span>
      ),
    },
    {
      key: "survival_status",
      header: "Status",
      align: "center",
      width: "120px",
      render: (row) => (
        <Badge variant={statusVariant[row.survival_status] ?? "neutral"}>
          {row.survival_status.replaceAll("_", " ")}
        </Badge>
      ),
    },
    {
      key: "estimated_valuation",
      header: "Valuation (KRW)",
      align: "right",
      width: "160px",
      render: (row) => (
        <span className="font-mono text-xs">
          {formatAmount(row.estimated_valuation, "KRW")}
        </span>
      ),
    },
    {
      key: "is_unicorn",
      header: "Unicorn",
      align: "center",
      width: "80px",
      render: (row) =>
        row.is_unicorn ? <Badge variant="info">Unicorn</Badge> : null,
    },
    {
      key: "last_audit_date",
      header: "Last Audit",
      align: "center",
      width: "120px",
      render: (row) => formatDate(row.last_audit_date, "short"),
    },
    {
      key: "id",
      header: "Actions",
      align: "center",
      width: "180px",
      render: (row) => (
        <div className="flex gap-1 justify-center">
          <Button
            variant="ghost"
            size="sm"
            icon={ShieldCheck}
            onClick={(e) => {
              e.stopPropagation();
              handleCheckSurvival(row);
            }}
            loading={checkingId === row.id}
          >
            Check
          </Button>
          <Button
            variant="ghost"
            size="sm"
            icon={Pencil}
            onClick={(e) => {
              e.stopPropagation();
              setModalItem(row);
            }}
          >
            Value
          </Button>
        </div>
      ),
    },
  ];

  const totalPages = data ? Math.ceil(data.total / 20) : 0;

  return (
    <div className="space-y-6">
      <PageHero title="Portfolio" subtitle="Track investor portfolio companies" compact />

      <div className="flex gap-3 items-end flex-wrap">
        <CorpCodeInput
          onSearch={handleSearch}
          label="Investor Code"
          placeholder="Enter investor corp code..."
        />
        <div className="w-48">
          <Select
            label="Status"
            options={STATUS_OPTIONS}
            value={status}
            onChange={(e) => {
              setStatus(e.target.value as SurvivalStatus | "");
              setPage(1);
            }}
          />
        </div>
        {corpCode && (
          <Button
            variant="secondary"
            icon={RefreshCw}
            onClick={handleSync}
            loading={syncPortfolio.isPending}
          >
            Sync
          </Button>
        )}
      </div>

      {corpCode && summary && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
          <KpiCard label="Total" value={String(summary.total)} icon={Activity} />
          <KpiCard
            label="Active"
            value={String(summary.active_count)}
            icon={Activity}
            variant="positive"
          />
          <KpiCard
            label="Audit Missing"
            value={String(summary.audit_missing_count)}
            icon={Activity}
            variant="caution"
          />
          <KpiCard
            label="Dissolved"
            value={String(summary.dissolved_count)}
            icon={Activity}
            variant="negative"
          />
          <KpiCard
            label="Unicorn"
            value={String(summary.unicorn_count)}
            icon={Activity}
          />
          <KpiCard
            label="Unknown"
            value={String(summary.unknown_count)}
            icon={Activity}
          />
        </div>
      )}

      <Card padding="none">
        {!corpCode ? (
          <EmptyState
            icon={Activity}
            title="Search for an investor"
            description="Enter an investor company code to view portfolio."
          />
        ) : isLoading ? (
          <Spinner />
        ) : !data?.items.length ? (
          <EmptyState
            icon={Activity}
            title="No portfolio found"
            description="No portfolio companies for this investor."
          />
        ) : (
          <DataTable
            columns={columns}
            data={data.items}
            keyField="id"
            striped
          />
        )}
      </Card>

      {corpCode && (
        <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />
      )}

      <ValuationModal
        open={!!modalItem}
        onClose={() => setModalItem(null)}
        item={modalItem}
        onSubmit={handleUpdateValuation}
        isPending={updateValuation.isPending}
      />
    </div>
  );
}

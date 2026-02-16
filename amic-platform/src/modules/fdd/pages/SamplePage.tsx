import { useState } from "react";
import {
  Briefcase,
  CheckCircle,
  FileEdit,
  Archive,
  TrendingUp,
  Wallet,
  AlertTriangle,
} from "lucide-react";
import {
  Card,
  KpiCard,
  DataTable,
  Badge,
  Button,
  EmptyState,
  getStatusVariant,
  PageHero,
} from "@/components/ui";
import type { Column } from "@/components/ui";

// ── Mock Data (백엔드 없이 확인용) ──

interface SampleDeal {
  id: string;
  name: string;
  deal_type: string;
  base_currency: string;
  reference_date: string;
  status: string;
  client_name: string;
  target_company_name: string;
  amount: number;
}

const MOCK_DEALS: SampleDeal[] = [
  {
    id: "deal-1",
    name: "Project Alpha",
    deal_type: "COMPLETION_ACCOUNTS",
    base_currency: "KRW",
    reference_date: "2025-06-30",
    status: "ACTIVE",
    client_name: "ABC Capital",
    target_company_name: "Target Corp",
    amount: 50_000_000_000,
  },
  {
    id: "deal-2",
    name: "Project Beta",
    deal_type: "LOCKED_BOX",
    base_currency: "USD",
    reference_date: "2025-03-31",
    status: "DRAFT",
    client_name: "XYZ Partners",
    target_company_name: "Beta Industries",
    amount: 25_000_000,
  },
  {
    id: "deal-3",
    name: "Project Gamma",
    deal_type: "COMPLETION_ACCOUNTS",
    base_currency: "KRW",
    reference_date: "2025-09-30",
    status: "ACTIVE",
    client_name: "DEF Holdings",
    target_company_name: "Gamma Tech",
    amount: 120_000_000_000,
  },
  {
    id: "deal-4",
    name: "Project Delta",
    deal_type: "LOCKED_BOX",
    base_currency: "EUR",
    reference_date: "2025-12-31",
    status: "ARCHIVED",
    client_name: "GHI Capital",
    target_company_name: "Delta Pharma",
    amount: 15_000_000,
  },
];

const columns: Column<SampleDeal>[] = [
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
    render: (row) =>
      row.deal_type === "COMPLETION_ACCOUNTS"
        ? "Completion Accounts"
        : "Locked Box",
  },
  {
    key: "client_name",
    header: "Client",
  },
  {
    key: "target_company_name",
    header: "Target",
  },
  {
    key: "base_currency",
    header: "Currency",
    align: "center",
    width: "100px",
  },
  {
    key: "amount",
    header: "Deal Size",
    align: "right",
    width: "160px",
    render: (row) => (
      <span className="font-mono text-sm">
        {row.amount.toLocaleString()} {row.base_currency}
      </span>
    ),
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

export default function SamplePage() {
  const [filter, setFilter] = useState<string>("ALL");

  const deals =
    filter === "ALL"
      ? MOCK_DEALS
      : MOCK_DEALS.filter((d) => d.status === filter);

  const kpis = {
    total: MOCK_DEALS.length,
    active: MOCK_DEALS.filter((d) => d.status === "ACTIVE").length,
    draft: MOCK_DEALS.filter((d) => d.status === "DRAFT").length,
    archived: MOCK_DEALS.filter((d) => d.status === "ARCHIVED").length,
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <PageHero
        title="FDD Sample Page"
        subtitle="Mock 데이터로 구성된 샘플 페이지입니다 (백엔드 불필요)"
        compact
      />

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

      {/* Filter Buttons */}
      <div className="flex gap-2">
        {["ALL", "ACTIVE", "DRAFT", "ARCHIVED"].map((s) => (
          <Button
            key={s}
            variant={filter === s ? "accent" : "ghost"}
            size="sm"
            onClick={() => setFilter(s)}
          >
            {s === "ALL" ? "All" : s.charAt(0) + s.slice(1).toLowerCase()}
          </Button>
        ))}
      </div>

      {/* Deal Table */}
      <Card title="Sample Deals" headerBar padding="none">
        {deals.length === 0 ? (
          <EmptyState
            icon={Briefcase}
            title="No deals match filter"
            description="Try selecting a different status filter."
          />
        ) : (
          <DataTable
            columns={columns}
            data={deals}
            keyField="id"
            onRowClick={(row) =>
              alert(`Clicked: ${row.name} (${row.id})`)
            }
            striped
          />
        )}
      </Card>

      {/* Sample Stats Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card title="Deal Type Distribution">
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm text-text-secondary flex items-center gap-2">
                <TrendingUp className="h-4 w-4" /> Completion Accounts
              </span>
              <span className="font-medium">
                {MOCK_DEALS.filter((d) => d.deal_type === "COMPLETION_ACCOUNTS").length}
              </span>
            </div>
            <div className="w-full bg-gray-100 rounded-full h-2">
              <div
                className="bg-accent h-2 rounded-full"
                style={{
                  width: `${(MOCK_DEALS.filter((d) => d.deal_type === "COMPLETION_ACCOUNTS").length / MOCK_DEALS.length) * 100}%`,
                }}
              />
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-text-secondary flex items-center gap-2">
                <Wallet className="h-4 w-4" /> Locked Box
              </span>
              <span className="font-medium">
                {MOCK_DEALS.filter((d) => d.deal_type === "LOCKED_BOX").length}
              </span>
            </div>
            <div className="w-full bg-gray-100 rounded-full h-2">
              <div
                className="bg-amic h-2 rounded-full"
                style={{
                  width: `${(MOCK_DEALS.filter((d) => d.deal_type === "LOCKED_BOX").length / MOCK_DEALS.length) * 100}%`,
                }}
              />
            </div>
          </div>
        </Card>

        <Card title="Currency Breakdown">
          <div className="space-y-4">
            {["KRW", "USD", "EUR"].map((currency) => {
              const count = MOCK_DEALS.filter(
                (d) => d.base_currency === currency,
              ).length;
              return (
                <div key={currency} className="flex items-center justify-between">
                  <Badge variant="neutral">{currency}</Badge>
                  <span className="font-medium">
                    {count} deal{count !== 1 ? "s" : ""}
                  </span>
                </div>
              );
            })}
          </div>
        </Card>
      </div>

      {/* Info */}
      <Card>
        <div className="flex items-start gap-3">
          <AlertTriangle className="h-5 w-5 text-amber-500 shrink-0 mt-0.5" />
          <div>
            <p className="font-medium text-text-dark">Sample Page Notice</p>
            <p className="text-sm text-text-secondary mt-1">
              이 페이지는 하드코딩된 목 데이터를 사용합니다.
              실제 API 연동 없이 UI 컴포넌트와 레이아웃을 확인할 수 있습니다.
            </p>
          </div>
        </div>
      </Card>
    </div>
  );
}

import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { Landmark, AlertCircle } from "lucide-react";
import { useFunds } from "@/modules/kiis/hooks/useFunds";
import { useFundFilters } from "@/modules/kiis/hooks/useFundFilters";
import { Card, DataTable, Badge, EmptyState, Pagination, PageHero } from "@/components/ui";
import type { Column } from "@/components/ui";
import type { FundListItem } from "@/modules/kiis/types/fund";
import { formatAmount } from "@/lib/format";
import { FundFilterPanel } from "@/modules/kiis/components/FundFilterPanel";
import {
  ASSET_CLASS_BADGE_VARIANT,
  ASSET_CLASS_LABELS,
  FUND_STATUS_BADGE_VARIANT,
  FUND_STATUS_LABELS,
} from "@/modules/kiis/constants/fundFilters";
import heroImg from "@/assets/images/heroes/forestgp-vc.jpg";

const columns: Column<FundListItem>[] = [
  {
    key: "fund_name",
    header: "Fund Name",
    render: (row) => (
      <span className="font-medium text-text-dark">{row.fund_name}</span>
    ),
  },
  {
    key: "fund_type",
    header: "Type",
    align: "center",
    width: "90px",
    render: (row) => (
      <Badge variant={row.fund_type === "blind" ? "info" : "neutral"}>
        {row.fund_type}
      </Badge>
    ),
  },
  {
    key: "asset_class",
    header: "Class",
    align: "center",
    width: "90px",
    render: (row) => (
      <Badge variant={ASSET_CLASS_BADGE_VARIANT[row.asset_class] ?? "neutral"}>
        {ASSET_CLASS_LABELS[row.asset_class] ?? row.asset_class}
      </Badge>
    ),
  },
  {
    key: "fund_status",
    header: "Status",
    align: "center",
    width: "90px",
    render: (row) => (
      <Badge variant={FUND_STATUS_BADGE_VARIANT[row.fund_status] ?? "neutral"}>
        {FUND_STATUS_LABELS[row.fund_status] ?? row.fund_status}
      </Badge>
    ),
  },
  { key: "company_name", header: "Manager" },
  {
    key: "total_amount",
    header: "Total Amount",
    align: "right",
    mono: true,
    render: (row) => formatAmount(row.total_amount, "KRW"),
  },
  {
    key: "vintage_year",
    header: "Vintage",
    align: "center",
    width: "80px",
    render: (row) => row.vintage_year ?? "-",
  },
  {
    key: "is_maturity_alert",
    header: "Alert",
    align: "center",
    width: "70px",
    render: (row) =>
      row.is_maturity_alert ? (
        <AlertCircle className="h-4 w-4 text-caution mx-auto" />
      ) : null,
  },
];

export default function FundListPage() {
  const navigate = useNavigate();
  const {
    params,
    setFilter,
    getSelected,
    setPage,
    resetFilters,
    activeFilterCount,
    page,
  } = useFundFilters();

  // 로컬 텍스트 입력 상태 (디바운스용)
  const [companyName, setCompanyName] = useState(params.company_name ?? "");
  const [fundName, setFundName] = useState(params.fund_name ?? "");

  const { data, isLoading } = useFunds(params);

  return (
    <div className="space-y-6">
      {/* Breadcrumb */}
      <div className="text-sm text-text-secondary">
        <Link to="/kiis/funds" className="hover:text-accent">
          ← GP 목록으로 돌아가기
        </Link>
      </div>

      <PageHero
        title="All Funds"
        subtitle="전체 펀드 목록 · PE & VC fund registry"
        compact
        backgroundImage={heroImg}
        backgroundOpacity={0.18}
      />

      <FundFilterPanel
        companyName={companyName}
        fundName={fundName}
        onCompanyNameChange={setCompanyName}
        onFundNameChange={setFundName}
        fundTypes={getSelected("fund_type")}
        legalTypes={getSelected("legal_type")}
        assetClasses={getSelected("asset_class")}
        fundStatuses={getSelected("fund_status")}
        vintageFrom={params.vintage_from?.toString() ?? ""}
        vintageTo={params.vintage_to?.toString() ?? ""}
        amountPreset={new URLSearchParams(window.location.search).get("amount_preset") ?? ""}
        onSetFilter={setFilter}
        onReset={() => {
          resetFilters();
          setCompanyName("");
          setFundName("");
        }}
        activeFilterCount={activeFilterCount}
      />

      <Card padding="none">
        {!isLoading && (!data?.items || data.items.length === 0) ? (
          <EmptyState
            icon={Landmark}
            title="No funds found"
            description="Try adjusting your search or filters."
          />
        ) : (
          <DataTable
            columns={columns}
            data={data?.items ?? []}
            keyField="fund_code"
            loading={isLoading}
            onRowClick={(row) => navigate(`/kiis/funds/${row.fund_code}`)}
            striped
          />
        )}
      </Card>

      <Pagination
        page={page}
        totalPages={data ? Math.ceil(data.total / 20) : 0}
        onPageChange={setPage}
      />
    </div>
  );
}

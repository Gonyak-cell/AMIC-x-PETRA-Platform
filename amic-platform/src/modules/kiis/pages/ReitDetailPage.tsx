import { useParams, Link } from "react-router-dom";
import { Home, Package, Building2, Percent, PieChart, CheckCircle } from "lucide-react";
import { useReitDetail } from "@/modules/kiis/hooks/useReits";
import { Card, DataTable, KpiCard, Spinner, EmptyState, PageHero } from "@/components/ui";
import type { Column } from "@/components/ui";
import type { REITsAssetItem } from "@/modules/kiis/types/reit";
import { formatAmount, formatPercent } from "@/lib/format";

const assetColumns: Column<REITsAssetItem>[] = [
  {
    key: "asset_name",
    header: "Asset",
    render: (row) => (
      <span className="font-medium text-text-dark">{row.asset_name}</span>
    ),
  },
  { key: "asset_type", header: "Type", align: "center", width: "120px" },
  {
    key: "asset_value",
    header: "Valuation",
    align: "right",
    mono: true,
    render: (row) => formatAmount(row.asset_value, "KRW"),
  },
  {
    key: "asset_ratio",
    header: "Ratio",
    align: "right",
    width: "100px",
    mono: true,
    render: (row) => formatPercent(row.asset_ratio),
  },
];

export default function ReitDetailPage() {
  const { reitsCode } = useParams<{ reitsCode: string }>();
  const code = reitsCode ?? "";
  const { data, isLoading, isError } = useReitDetail(code);

  const reit = data?.reits;
  const assets = data?.assets ?? [];

  if (isLoading) return <Spinner />;
  if (isError || !reit) {
    return (
      <EmptyState
        icon={Home}
        title="REIT not found"
        description="The requested REIT could not be found."
      />
    );
  }

  return (
    <div className="space-y-6">
      {/* Breadcrumb */}
      <div className="text-sm text-text-secondary">
        <Link to="/kiis/reits" className="hover:text-accent">
          REITs
        </Link>
        <span className="mx-2">/</span>
        <span className="text-text-dark">{reit.reits_name}</span>
      </div>

      {/* Header */}
      <PageHero
        title={reit.reits_name}
        subtitle={[
          reit.reits_type === "self_managed" ? "Self-Managed" : "Entrusted",
          reit.status,
          reit.management_company,
        ].filter(Boolean).join(" | ")}
        compact
      />

      {/* KPI Summary */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard
          label="총자산"
          value={formatAmount(reit.total_assets, "KRW")}
          icon={Building2}
        />
        <KpiCard
          label="배당수익률"
          value={formatPercent(reit.dividend_rate)}
          icon={Percent}
        />
        <KpiCard
          label="부동산비율"
          value={formatPercent(reit.real_estate_ratio)}
          icon={PieChart}
          variant={reit.has_asset_ratio_warning ? "caution" : "default"}
        />
        <KpiCard
          label="상장여부"
          value={reit.is_listed ? "Yes" : "No"}
          icon={CheckCircle}
          variant={reit.is_listed ? "positive" : "default"}
        />
      </div>

      {/* Assets */}
      <Card title="Assets" headerBar padding="none">
        {!assets.length ? (
          <EmptyState
            icon={Package}
            title="No assets"
            description="Asset information is not available."
          />
        ) : (
          <DataTable
            columns={assetColumns}
            data={assets}
            keyField="asset_name"
            compact
            striped
          />
        )}
      </Card>
    </div>
  );
}

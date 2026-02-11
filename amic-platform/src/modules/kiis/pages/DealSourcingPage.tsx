import { useState } from "react";
import { TrendingUp, BarChart3 } from "lucide-react";
import {
  useDealTrends,
  useDealsBySector,
  useDealsByStage,
} from "@/modules/kiis/hooks/useDeals";
import { Card, DataTable, Select, Spinner, EmptyState } from "@/components/ui";
import type { Column } from "@/components/ui";
import DealTrendChart from "@/modules/kiis/components/DealTrendChart";
import type { SectorAggregation, StageAggregation } from "@/modules/kiis/types/deal";
import { formatAmount } from "@/lib/format";
import { cn } from "@/lib/cn";

const YEARS_OPTIONS = [
  { value: "3", label: "3 Years" },
  { value: "5", label: "5 Years" },
  { value: "10", label: "10 Years" },
];

type Tab = "trends" | "sector" | "stage";

const sectorColumns: Column<SectorAggregation>[] = [
  {
    key: "sector_name",
    header: "Sector",
    render: (row) => (
      <span className="font-medium text-text-dark">{row.sector_name}</span>
    ),
  },
  {
    key: "deal_count",
    header: "Deals",
    align: "right",
    width: "100px",
    mono: true,
  },
  {
    key: "total_amount",
    header: "Total Amount",
    align: "right",
    mono: true,
    render: (row) => formatAmount(row.total_amount, "KRW"),
  },
];

const stageColumns: Column<StageAggregation>[] = [
  {
    key: "stage_name",
    header: "Round",
    render: (row) => (
      <span className="font-medium text-text-dark">{row.stage_name}</span>
    ),
  },
  {
    key: "deal_count",
    header: "Deals",
    align: "right",
    width: "100px",
    mono: true,
  },
  {
    key: "total_amount",
    header: "Total Amount",
    align: "right",
    mono: true,
    render: (row) => formatAmount(row.total_amount, "KRW"),
  },
];

export default function DealSourcingPage() {
  const [tab, setTab] = useState<Tab>("trends");
  const [years, setYears] = useState("5");

  const { data: trends, isLoading: trendsLoading } = useDealTrends({
    years: Number(years),
  });
  const { data: sectors, isLoading: sectorsLoading } = useDealsBySector({
    years: Number(years),
  });
  const { data: stages, isLoading: stagesLoading } = useDealsByStage({
    years: Number(years),
  });

  const tabs: { key: Tab; label: string }[] = [
    { key: "trends", label: "Trends" },
    { key: "sector", label: "By Sector" },
    { key: "stage", label: "By Stage" },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-heading font-bold text-text-dark">
          Deal Sourcing
        </h1>
        <Select
          label="Lookback"
          options={YEARS_OPTIONS}
          value={years}
          onChange={(e) => setYears(e.target.value)}
        />
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-gray-border">
        {tabs.map((t) => (
          <button
            key={t.key}
            className={cn(
              "px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors",
              tab === t.key
                ? "border-accent text-accent"
                : "border-transparent text-text-secondary hover:text-text-dark",
            )}
            onClick={() => setTab(t.key)}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {tab === "trends" && (
        <Card title="Deal Trends" headerBar>
          {trendsLoading ? (
            <Spinner />
          ) : !trends?.length ? (
            <EmptyState
              icon={TrendingUp}
              title="No trend data"
              description="Deal trend data is not available."
            />
          ) : (
            <DealTrendChart data={trends} />
          )}
        </Card>
      )}

      {tab === "sector" && (
        <Card title="Deals by Sector" headerBar padding="none">
          {sectorsLoading ? (
            <Spinner />
          ) : !sectors?.length ? (
            <EmptyState
              icon={BarChart3}
              title="No sector data"
              description="Sector aggregation data is not available."
            />
          ) : (
            <DataTable
              columns={sectorColumns}
              data={sectors}
              keyField="sector"
              striped
            />
          )}
        </Card>
      )}

      {tab === "stage" && (
        <Card title="Deals by Stage" headerBar padding="none">
          {stagesLoading ? (
            <Spinner />
          ) : !stages?.length ? (
            <EmptyState
              icon={BarChart3}
              title="No stage data"
              description="Stage aggregation data is not available."
            />
          ) : (
            <DataTable
              columns={stageColumns}
              data={stages}
              keyField="stage"
              striped
            />
          )}
        </Card>
      )}
    </div>
  );
}

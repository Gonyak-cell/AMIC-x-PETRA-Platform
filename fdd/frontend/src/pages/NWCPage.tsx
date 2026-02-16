import { useState } from "react";
import { useParams } from "react-router-dom";
import { Wallet, Calculator, TrendingUp } from "lucide-react";
import { toast } from "sonner";
import {
  useNWCCalculations,
  useRunNWC,
  usePegSimulation,
  useRecalculatePeg,
  useUpdateNWCLineItem,
} from "@/hooks/useNWC";
import type {
  NWCCalculationRead,
  NWCLineItemRead,
  NWCClassification,
  PegMethod,
  PegSimulationResult,
} from "@/types/nwc";
import {
  Card,
  KpiCard,
  DataTable,
  Button,
  Badge,
  Input,
  Select,
  Spinner,
  EmptyState,
} from "@/components/ui";
import type { Column } from "@/components/ui";
import { formatAmount } from "@/lib/format";

const PEG_METHOD_OPTIONS = [
  { value: "LTM_AVERAGE", label: "LTM Average" },
  { value: "TTM", label: "TTM" },
  { value: "LAST_MONTH", label: "Last Month" },
  { value: "MAX", label: "Maximum" },
  { value: "MIN", label: "Minimum" },
  { value: "CUSTOM", label: "Custom" },
];

const PEG_METHOD_LABELS: Record<PegMethod, string> = {
  LTM_AVERAGE: "LTM Average",
  TTM: "TTM",
  LAST_MONTH: "Last Month",
  MAX: "Maximum",
  MIN: "Minimum",
  CUSTOM: "Custom",
};

// ── NWC Summary Card ────────────────────────────────────

function NWCSummaryCard({ nwc }: { nwc: NWCCalculationRead }) {
  const nwcValue = Number(nwc.net_working_capital);
  const delta = Number(nwc.peg_delta);

  return (
    <Card title="NWC Summary" headerBar>
      <div className="grid grid-cols-3 gap-4 mb-4">
        <div className="text-center">
          <p className="text-text-secondary text-kpi-label">Current Assets</p>
          <p className="font-mono text-kpi-value tabular-nums">
            {formatAmount(nwc.total_current_assets, "KRW")}
          </p>
        </div>
        <div className="text-center">
          <p className="text-text-secondary text-kpi-label">Current Liabilities</p>
          <p className="font-mono text-kpi-value tabular-nums">
            {formatAmount(nwc.total_current_liabilities, "KRW")}
          </p>
        </div>
        <div className="text-center">
          <p className="text-text-secondary text-kpi-label">Net Working Capital</p>
          <p className={`font-mono text-kpi-value tabular-nums font-bold ${nwcValue < 0 ? "text-negative" : "text-amic"}`}>
            {formatAmount(nwc.net_working_capital, "KRW")}
          </p>
        </div>
      </div>

      <div className="border-t border-gray-border pt-3 grid grid-cols-3 gap-4 text-sm">
        <div>
          <span className="text-text-secondary">Peg Method: </span>
          <span className="font-medium">{PEG_METHOD_LABELS[nwc.peg_method]}</span>
        </div>
        <div>
          <span className="text-text-secondary">Peg Target: </span>
          <span className="font-mono font-medium tabular-nums">
            {formatAmount(nwc.peg_target, "KRW")}
          </span>
        </div>
        <div>
          <span className="text-text-secondary">Delta: </span>
          <span className={`font-mono font-medium tabular-nums ${delta >= 0 ? "text-positive" : "text-negative"}`}>
            {delta >= 0 ? "+" : ""}{formatAmount(nwc.peg_delta, "KRW")}
          </span>
        </div>
      </div>

      <p className="text-footnote text-text-secondary mt-3 pt-3 border-t border-gray-border">
        Engine v{nwc.engine_version} | {new Date(nwc.created_at).toLocaleString("ko-KR")}
      </p>
    </Card>
  );
}

// ── Line Items Table ────────────────────────────────────

function LineItemsTable({
  items,
  onClassify,
  isUpdating,
}: {
  items: NWCLineItemRead[];
  onClassify: (itemId: string, classification: NWCClassification) => void;
  isUpdating: boolean;
}) {
  const sorted = [...items].sort((a, b) => a.display_order - b.display_order);

  const columns: Column<NWCLineItemRead>[] = [
    { key: "account_code", header: "Code", width: "100px" },
    { key: "account_name", header: "Account Name" },
    {
      key: "line_item_category",
      header: "Category",
      width: "120px",
      render: (row) => <Badge variant="neutral">{row.line_item_category}</Badge>,
    },
    {
      key: "amount",
      header: "Amount",
      align: "right",
      width: "140px",
      mono: true,
      render: (row) => formatAmount(row.amount, "KRW"),
    },
    {
      key: "classification",
      header: "Classification",
      width: "140px",
      render: (row) => (
        <Select
          options={[
            { value: "ABOVE_LINE", label: "Above Line" },
            { value: "BELOW_LINE", label: "Below Line" },
            { value: "EXCLUDED", label: "Excluded" },
          ]}
          value={row.classification}
          onChange={(e) => onClassify(row.id, e.target.value as NWCClassification)}
          disabled={isUpdating}
        />
      ),
    },
  ];

  // Group items by classification
  const aboveLine = sorted.filter((i) => i.classification === "ABOVE_LINE");
  const belowLine = sorted.filter((i) => i.classification === "BELOW_LINE");
  const excluded = sorted.filter((i) => i.classification === "EXCLUDED");

  return (
    <Card title={`WC Line Items (${items.length})`} headerBar padding="none">
      <DataTable
        columns={columns}
        data={sorted}
        keyField="id"
        striped
        compact
        sectionHeaders={[
          { index: 0, label: `Above the Line (${aboveLine.length})` },
          { index: aboveLine.length, label: `Below the Line (${belowLine.length})` },
          { index: aboveLine.length + belowLine.length, label: `Excluded (${excluded.length})` },
        ]}
      />
    </Card>
  );
}

// ── Peg Simulation Panel ────────────────────────────────

function PegSimulationPanel({
  dealId,
  nwcId,
  currentMethod,
}: {
  dealId: string;
  nwcId: string;
  currentMethod: PegMethod;
}) {
  const { data: pegData, isLoading } = usePegSimulation(dealId, nwcId);
  const recalcMutation = useRecalculatePeg(dealId, nwcId);
  const [customValue, setCustomValue] = useState("");

  const handleApplyMethod = async (method: PegMethod) => {
    try {
      await recalcMutation.mutateAsync({
        peg_method: method,
        custom_value: method === "CUSTOM" ? customValue || null : null,
      });
      toast.success(`Peg method updated to ${PEG_METHOD_LABELS[method]}`);
    } catch {
      toast.error("Failed to update peg method");
    }
  };

  if (isLoading) {
    return (
      <Card title="Peg Simulation" headerBar>
        <div className="flex items-center justify-center py-8">
          <Spinner />
        </div>
      </Card>
    );
  }

  if (!pegData) return null;

  const columns: Column<PegSimulationResult>[] = [
    {
      key: "method",
      header: "Method",
      render: (row) => (
        <div className="flex items-center gap-2">
          <span className="font-medium">{PEG_METHOD_LABELS[row.method]}</span>
          {row.method === currentMethod && (
            <Badge variant="info">Active</Badge>
          )}
        </div>
      ),
    },
    { key: "description", header: "Description" },
    {
      key: "target_nwc",
      header: "Target NWC",
      align: "right",
      mono: true,
      render: (row) => formatAmount(row.target_nwc, "KRW"),
    },
    {
      key: "delta",
      header: "Delta",
      align: "right",
      mono: true,
      render: (row) => {
        const delta = Number(row.delta);
        return (
          <span className={delta >= 0 ? "text-positive" : "text-negative"}>
            {delta >= 0 ? "+" : ""}{formatAmount(row.delta, "KRW")}
          </span>
        );
      },
    },
    {
      key: "actions",
      header: "Action",
      width: "100px",
      render: (row) =>
        row.method !== currentMethod ? (
          <Button
            variant="primary"
            size="sm"
            onClick={() => handleApplyMethod(row.method)}
            disabled={recalcMutation.isPending}
          >
            Apply
          </Button>
        ) : null,
    },
  ];

  return (
    <Card
      title="Peg Simulation (6 Scenarios)"
      headerBar
      actions={
        <span className="text-white/70 text-sm">
          Reference NWC: <span className="font-mono font-medium">{formatAmount(pegData.reference_nwc, "KRW")}</span>
        </span>
      }
      padding="none"
    >
      <DataTable
        columns={columns}
        data={pegData.scenarios}
        keyField="method"
        striped
      />
      <div className="p-4 border-t border-gray-border flex items-center gap-3">
        <span className="text-sm text-text-secondary">Custom Peg Value:</span>
        <Input
          placeholder="e.g. 500000"
          value={customValue}
          onChange={(e) => setCustomValue(e.target.value)}
          className="w-40"
        />
        <Button
          variant="secondary"
          size="sm"
          onClick={() => handleApplyMethod("CUSTOM")}
          disabled={recalcMutation.isPending || !customValue.trim()}
        >
          Apply Custom
        </Button>
      </div>
    </Card>
  );
}

// ── Monthly Trend Table ─────────────────────────────────

function MonthlyTrendTable({ nwc }: { nwc: NWCCalculationRead }) {
  const months = Object.keys(nwc.monthly_trend).sort();

  if (months.length === 0) {
    return (
      <Card title="Monthly NWC Trend" headerBar>
        <EmptyState
          title="No trend data"
          description="Monthly trend data is not available for single-period snapshots."
        />
      </Card>
    );
  }

  const data = months.map((month) => ({
    month,
    ...nwc.monthly_trend[month],
  }));

  const columns: Column<typeof data[0]>[] = [
    { key: "month", header: "Month" },
    {
      key: "current_assets",
      header: "Current Assets",
      align: "right",
      mono: true,
      render: (row) => formatAmount(row.current_assets, "KRW"),
    },
    {
      key: "current_liabilities",
      header: "Current Liabilities",
      align: "right",
      mono: true,
      render: (row) => formatAmount(row.current_liabilities, "KRW"),
    },
    {
      key: "nwc",
      header: "NWC",
      align: "right",
      mono: true,
      render: (row) => {
        const nwcVal = Number(row.nwc);
        return (
          <span className={`font-medium ${nwcVal < 0 ? "text-negative" : ""}`}>
            {formatAmount(row.nwc, "KRW")}
          </span>
        );
      },
    },
  ];

  return (
    <Card title="Monthly NWC Trend" headerBar padding="none">
      <DataTable columns={columns} data={data} keyField="month" striped />
    </Card>
  );
}

// ── Main NWC Page ───────────────────────────────────────

export default function NWCPage() {
  const { dealId } = useParams<{ dealId: string }>();
  const { data: nwcList = [], isLoading } = useNWCCalculations(dealId!);
  const runMutation = useRunNWC(dealId!);

  const latestNWC = nwcList.length > 0 ? nwcList[0] : null;

  const updateItemMutation = useUpdateNWCLineItem(dealId!, latestNWC?.id ?? "");

  const [snapshotId, setSnapshotId] = useState("");
  const [pegMethod, setPegMethod] = useState<PegMethod>("LTM_AVERAGE");

  const handleRun = async () => {
    if (!snapshotId.trim()) return;
    try {
      await runMutation.mutateAsync({ snapshot_id: snapshotId, peg_method: pegMethod });
      toast.success("NWC calculation completed");
    } catch {
      toast.error("Failed to calculate NWC");
    }
  };

  const handleClassify = async (itemId: string, classification: NWCClassification) => {
    try {
      await updateItemMutation.mutateAsync({ itemId, body: { classification } });
      toast.success("Classification updated");
    } catch {
      toast.error("Failed to update classification");
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Spinner size="lg" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-heading font-bold text-text-dark">
            Net Working Capital
          </h1>
          <p className="text-text-secondary mt-1">Working Capital Analysis & Peg Simulation</p>
        </div>
        {!latestNWC && (
          <div className="flex items-center gap-3">
            <Input
              placeholder="Snapshot ID"
              value={snapshotId}
              onChange={(e) => setSnapshotId(e.target.value)}
              className="w-72"
            />
            <Select
              options={PEG_METHOD_OPTIONS}
              value={pegMethod}
              onChange={(e) => setPegMethod(e.target.value as PegMethod)}
            />
            <Button
              variant="accent"
              icon={Calculator}
              onClick={handleRun}
              loading={runMutation.isPending}
              disabled={!snapshotId.trim()}
            >
              Calculate NWC
            </Button>
          </div>
        )}
      </div>

      {/* KPI Cards */}
      {latestNWC && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <KpiCard
            label="Current Assets"
            value={formatAmount(latestNWC.total_current_assets, "KRW")}
            icon={Wallet}
          />
          <KpiCard
            label="Current Liabilities"
            value={formatAmount(latestNWC.total_current_liabilities, "KRW")}
          />
          <KpiCard
            label="Net Working Capital"
            value={formatAmount(latestNWC.net_working_capital, "KRW")}
            variant={Number(latestNWC.net_working_capital) >= 0 ? "positive" : "negative"}
          />
          <KpiCard
            label="Target NWC"
            value={formatAmount(latestNWC.peg_target, "KRW")}
            icon={TrendingUp}
          />
        </div>
      )}

      {/* Error */}
      {runMutation.isError && (
        <div className="bg-red-50 border border-negative/20 rounded-lg p-4 text-sm text-negative">
          Error: {runMutation.error.message}
        </div>
      )}

      {/* Empty State or Content */}
      {!latestNWC ? (
        <Card>
          <EmptyState
            icon={Wallet}
            title="No NWC Calculation"
            description="Enter a Snapshot ID and click 'Calculate NWC' to start analyzing."
          />
        </Card>
      ) : (
        <>
          {/* NWC Summary */}
          <NWCSummaryCard nwc={latestNWC} />

          {/* Line Items Table */}
          <LineItemsTable
            items={latestNWC.line_items}
            onClassify={handleClassify}
            isUpdating={updateItemMutation.isPending}
          />

          {/* Peg Simulation */}
          <PegSimulationPanel
            dealId={dealId!}
            nwcId={latestNWC.id}
            currentMethod={latestNWC.peg_method}
          />

          {/* Monthly Trend */}
          <MonthlyTrendTable nwc={latestNWC} />
        </>
      )}
    </div>
  );
}

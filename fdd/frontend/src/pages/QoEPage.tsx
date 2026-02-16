import { useState } from "react";
import { useParams } from "react-router-dom";
import { Calculator, TrendingUp, RefreshCw, Check } from "lucide-react";
import { toast } from "sonner";
import {
  useQoECalculations,
  useRunQoE,
  useApproveAdjustment,
  useRecalculateBridge,
} from "@/hooks/useQoE";
import type {
  QoECalculationRead,
  AdjustmentItemRead,
  AdjustmentCategory,
  AdjustmentStatus,
} from "@/types/qoe";
import {
  Card,
  KpiCard,
  DataTable,
  Button,
  Badge,
  Input,
  Spinner,
  EmptyState,
} from "@/components/ui";
import type { Column } from "@/components/ui";
import { formatAmount } from "@/lib/format";

const CATEGORY_LABELS: Record<AdjustmentCategory, string> = {
  NON_RECURRING: "Non-Recurring",
  NON_OPERATING: "Non-Operating",
  NORMALIZATION: "Normalization",
  OWNER_RELATED: "Owner Related",
  PRO_FORMA: "Pro Forma",
};

const STATUS_VARIANTS: Record<AdjustmentStatus, "success" | "warning" | "error" | "info"> = {
  CANDIDATE: "warning",
  PROPOSED: "info",
  APPROVED: "success",
  REJECTED: "error",
};

// ── EBITDA Summary Card ─────────────────────────────────

function EBITDASummaryCard({ qoe }: { qoe: QoECalculationRead }) {
  const rows = [
    { label: "Revenue", value: qoe.revenue, bold: false, indent: false },
    { label: "(-) COGS", value: qoe.cogs, bold: false, indent: true },
    { label: "Gross Profit", value: qoe.gross_profit, bold: true, indent: false },
    { label: "(-) SG&A", value: qoe.sga, bold: false, indent: true },
    { label: "(-) D&A", value: qoe.depreciation_amortization, bold: false, indent: true },
    { label: "(+/-) Other Operating", value: qoe.other_operating, bold: false, indent: true },
    { label: "Operating Income", value: qoe.operating_income, bold: true, indent: false },
    { label: "(+) D&A Add-back", value: qoe.depreciation_amortization, bold: false, indent: true },
    { label: "Reported EBITDA", value: qoe.reported_ebitda, bold: true, indent: false },
  ];

  return (
    <Card title="Income Statement → EBITDA" headerBar>
      <table className="w-full text-sm">
        <tbody>
          {rows.map((r) => (
            <tr
              key={r.label}
              className={r.bold ? "border-t border-gray-border" : ""}
            >
              <td
                className={`py-2 ${r.bold ? "font-semibold text-text-dark" : "text-text-secondary"} ${r.indent ? "pl-4" : ""}`}
              >
                {r.label}
              </td>
              <td
                className={`py-2 text-right font-mono tabular-nums ${r.bold ? "font-semibold text-text-dark" : ""}`}
              >
                {formatAmount(r.value, "KRW")}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="text-footnote text-text-secondary mt-3 pt-3 border-t border-gray-border">
        Engine v{qoe.engine_version} | {new Date(qoe.created_at).toLocaleString("ko-KR")}
      </p>
    </Card>
  );
}

// ── Bridge Table ────────────────────────────────────────

function BridgeTable({
  qoe,
  onRecalculate,
  isRecalculating,
}: {
  qoe: QoECalculationRead;
  onRecalculate: () => void;
  isRecalculating: boolean;
}) {
  const approvedAdjs = qoe.adjustments.filter((a) => a.status === "APPROVED");
  const isBalanced = Number(qoe.balance_check_error) === 0;

  return (
    <Card
      title="QoE Bridge"
      headerBar
      actions={
        <div className="flex items-center gap-2">
          <Badge variant={isBalanced ? "success" : "error"}>
            {isBalanced ? "Balanced" : "Imbalanced"}
          </Badge>
          <Button
            variant="secondary"
            size="sm"
            icon={RefreshCw}
            onClick={onRecalculate}
            loading={isRecalculating}
            className="bg-white/10 border-white/30 text-white hover:bg-white/20"
          >
            Recalculate
          </Button>
        </div>
      }
    >
      <table className="w-full text-sm">
        <tbody>
          {/* Reported EBITDA */}
          <tr className="border-b border-gray-border">
            <td className="py-2 font-semibold text-text-dark">Reported EBITDA</td>
            <td className="py-2 text-right font-mono tabular-nums font-semibold">
              {formatAmount(qoe.reported_ebitda, "KRW")}
            </td>
          </tr>

          {/* Approved Adjustments */}
          {approvedAdjs.length === 0 ? (
            <tr>
              <td className="py-2 text-text-secondary italic" colSpan={2}>
                No approved adjustments
              </td>
            </tr>
          ) : (
            approvedAdjs.map((adj) => (
              <tr key={adj.id} className="border-b border-gray-border">
                <td className="py-2 pl-4 text-text-secondary">
                  <Badge variant={STATUS_VARIANTS[adj.status]} className="mr-2">
                    {CATEGORY_LABELS[adj.category]}
                  </Badge>
                  {adj.description}
                </td>
                <td className="py-2 text-right font-mono tabular-nums">
                  {formatAmount(adj.amount, "KRW")}
                </td>
              </tr>
            ))
          )}

          {/* Total Adjustments */}
          <tr className="border-b border-gray-border">
            <td className="py-2 font-medium text-text-dark">Total Adjustments</td>
            <td className="py-2 text-right font-mono tabular-nums font-medium">
              {formatAmount(qoe.total_adjustments, "KRW")}
            </td>
          </tr>

          {/* Adjusted EBITDA */}
          <tr className="border-t-2 border-amic">
            <td className="py-3 font-bold text-lg text-text-dark">Adjusted EBITDA</td>
            <td className="py-3 text-right font-mono tabular-nums font-bold text-lg text-amic">
              {formatAmount(qoe.adjusted_ebitda, "KRW")}
            </td>
          </tr>
        </tbody>
      </table>
    </Card>
  );
}

// ── Adjustment Candidates Table ─────────────────────────

function AdjustmentCandidatesTable({
  adjustments,
  onApprove,
  isApproving,
}: {
  adjustments: AdjustmentItemRead[];
  onApprove: (adjId: string) => void;
  isApproving: boolean;
}) {
  const pending = adjustments.filter(
    (a) => a.status === "CANDIDATE" || a.status === "PROPOSED"
  );

  if (pending.length === 0) {
    return (
      <Card title="Adjustment Candidates" headerBar>
        <EmptyState
          title="No adjustment candidates"
          description="No pending adjustments detected from the financial data."
        />
      </Card>
    );
  }

  const columns: Column<AdjustmentItemRead>[] = [
    {
      key: "category",
      header: "Category",
      width: "140px",
      render: (row) => (
        <Badge variant="neutral">{CATEGORY_LABELS[row.category]}</Badge>
      ),
    },
    {
      key: "description",
      header: "Description",
      render: (row) => (
        <span className="truncate max-w-xs block" title={row.description}>
          {row.description}
        </span>
      ),
    },
    {
      key: "detection_method",
      header: "Method",
      width: "100px",
      render: (row) => (
        <span className="text-text-secondary">{row.detection_method}</span>
      ),
    },
    {
      key: "confidence_score",
      header: "Confidence",
      align: "right",
      width: "100px",
      mono: true,
      render: (row) =>
        row.confidence_score
          ? `${Number(row.confidence_score).toFixed(0)}%`
          : "-",
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
      key: "status",
      header: "Status",
      align: "center",
      width: "100px",
      render: (row) => (
        <Badge variant={STATUS_VARIANTS[row.status]}>{row.status}</Badge>
      ),
    },
    {
      key: "actions",
      header: "Actions",
      width: "100px",
      render: (row) => (
        <Button
          variant="accent"
          size="sm"
          icon={Check}
          onClick={() => onApprove(row.id)}
          disabled={isApproving}
        >
          Approve
        </Button>
      ),
    },
  ];

  return (
    <Card
      title={`Adjustment Candidates (${pending.length})`}
      headerBar
      padding="none"
    >
      <DataTable
        columns={columns}
        data={pending}
        keyField="id"
        striped
        compact
      />
    </Card>
  );
}

// ── Main QoE Page ───────────────────────────────────────

export default function QoEPage() {
  const { dealId } = useParams<{ dealId: string }>();
  const { data: qoeList = [], isLoading } = useQoECalculations(dealId!);
  const runMutation = useRunQoE(dealId!);

  const latestQoE = qoeList.length > 0 ? qoeList[0] : null;

  const approveMutation = useApproveAdjustment(dealId!, latestQoE?.id ?? "");
  const recalcMutation = useRecalculateBridge(dealId!, latestQoE?.id ?? "");

  const [snapshotId, setSnapshotId] = useState("");

  const handleRun = async () => {
    if (!snapshotId.trim()) return;
    try {
      await runMutation.mutateAsync({ snapshot_id: snapshotId });
      toast.success("QoE calculation completed");
    } catch {
      toast.error("Failed to calculate QoE");
    }
  };

  const handleApprove = async (adjId: string) => {
    try {
      await approveMutation.mutateAsync({
        adjustmentId: adjId,
        body: { approved_by: "analyst" },
      });
      toast.success("Adjustment approved");
    } catch {
      toast.error("Failed to approve adjustment");
    }
  };

  const handleRecalculate = async () => {
    try {
      await recalcMutation.mutateAsync();
      toast.success("Bridge recalculated");
    } catch {
      toast.error("Failed to recalculate bridge");
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
            Quality of Earnings
          </h1>
          <p className="text-text-secondary mt-1">Adjusted EBITDA Analysis</p>
        </div>
        {!latestQoE && (
          <div className="flex items-center gap-3">
            <Input
              placeholder="Snapshot ID"
              value={snapshotId}
              onChange={(e) => setSnapshotId(e.target.value)}
              className="w-72"
            />
            <Button
              variant="accent"
              icon={Calculator}
              onClick={handleRun}
              loading={runMutation.isPending}
              disabled={!snapshotId.trim()}
            >
              Calculate QoE
            </Button>
          </div>
        )}
      </div>

      {/* KPI Cards */}
      {latestQoE && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <KpiCard
            label="Revenue"
            value={formatAmount(latestQoE.revenue, "KRW")}
            icon={TrendingUp}
          />
          <KpiCard
            label="Reported EBITDA"
            value={formatAmount(latestQoE.reported_ebitda, "KRW")}
          />
          <KpiCard
            label="Adjusted EBITDA"
            value={formatAmount(latestQoE.adjusted_ebitda, "KRW")}
            variant="positive"
          />
          <KpiCard
            label="Total Adjustments"
            value={formatAmount(latestQoE.total_adjustments, "KRW")}
            variant={Number(latestQoE.total_adjustments) >= 0 ? "positive" : "negative"}
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
      {!latestQoE ? (
        <Card>
          <EmptyState
            icon={Calculator}
            title="No QoE Calculation"
            description="Enter a Snapshot ID and click 'Calculate QoE' to start analyzing."
            actionLabel="Calculate QoE"
            onAction={() => snapshotId.trim() && handleRun()}
          />
        </Card>
      ) : (
        <>
          {/* EBITDA Summary + Bridge */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <EBITDASummaryCard qoe={latestQoE} />
            <BridgeTable
              qoe={latestQoE}
              onRecalculate={handleRecalculate}
              isRecalculating={recalcMutation.isPending}
            />
          </div>

          {/* Adjustment Candidates */}
          <AdjustmentCandidatesTable
            adjustments={latestQoE.adjustments}
            onApprove={handleApprove}
            isApproving={approveMutation.isPending}
          />
        </>
      )}
    </div>
  );
}

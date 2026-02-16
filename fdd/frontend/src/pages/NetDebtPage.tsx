import { useState } from "react";
import { useParams } from "react-router-dom";
import {
  Landmark,
  Wallet,
  Calculator,
  RefreshCw,
  Check,
  Plus,
} from "lucide-react";
import { toast } from "sonner";
import {
  useDebtCalculations,
  useRunDebt,
  useDebtBridge,
  useApproveDebtItem,
  useRecalculateDebt,
  useAddDebtItem,
} from "@/hooks/useDebt";
import type {
  NetDebtBridgeSummary,
  DebtItemRead,
  DebtItemType,
  DebtItemStatus,
} from "@/types/debt";
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
import type { Column, SelectOption } from "@/components/ui";
import { formatAmount } from "@/lib/format";

const STATUS_VARIANTS: Record<DebtItemStatus, "success" | "warning" | "error" | "info"> = {
  CANDIDATE: "warning",
  PROPOSED: "info",
  APPROVED: "success",
  REJECTED: "error",
};

const ITEM_TYPE_OPTIONS: SelectOption[] = [
  { value: "GROSS_DEBT", label: "Gross Debt" },
  { value: "CASH", label: "Cash & Equivalents" },
  { value: "DEBT_LIKE", label: "Debt-Like" },
  { value: "CASH_LIKE", label: "Cash-Like" },
];

// ── Bridge Table ────────────────────────────────────────

function BridgeTable({
  bridge,
  onRecalculate,
  isRecalculating,
}: {
  bridge: NetDebtBridgeSummary;
  onRecalculate: () => void;
  isRecalculating: boolean;
}) {
  const rows: { label: string; value: string; bold: boolean; indent: boolean }[] = [
    { label: "Gross Debt", value: bridge.gross_debt, bold: false, indent: false },
    { label: "(-) Cash & Equivalents", value: bridge.cash_and_equivalents, bold: false, indent: true },
    { label: "Net Debt", value: bridge.net_debt, bold: true, indent: false },
    { label: "(+) Debt-Like Items", value: bridge.debt_like_total, bold: false, indent: true },
    { label: "(-) Cash-Like Items", value: bridge.cash_like_total, bold: false, indent: true },
    { label: "Adjusted Net Debt", value: bridge.adjusted_net_debt, bold: true, indent: false },
  ];

  return (
    <Card
      title="Net Debt Bridge"
      headerBar
      actions={
        <div className="flex items-center gap-2">
          <Badge variant={bridge.is_balanced ? "success" : "error"}>
            {bridge.is_balanced ? "Balanced" : `Error: ${formatAmount(bridge.balance_check_error, "KRW")}`}
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
          {rows.map((r) => (
            <tr key={r.label} className={r.bold ? "border-t border-gray-border" : ""}>
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
    </Card>
  );
}

// ── Debt Items Table ────────────────────────────────────

function DebtItemsTable({
  items,
  onApprove,
  isApproving,
}: {
  items: DebtItemRead[];
  onApprove: (itemId: string) => void;
  isApproving: boolean;
}) {
  const sorted = [...items].sort((a, b) => a.display_order - b.display_order);

  // 섹션별 분류
  const grossDebt = sorted.filter((i) => i.item_type === "GROSS_DEBT");
  const cash = sorted.filter((i) => i.item_type === "CASH");
  const debtLike = sorted.filter((i) => i.item_type === "DEBT_LIKE");
  const cashLike = sorted.filter((i) => i.item_type === "CASH_LIKE");

  // 섹션 헤더 인덱스 계산
  const allItems = [...grossDebt, ...cash, ...debtLike, ...cashLike];
  const sectionHeaders = [
    { index: 0, label: `Gross Debt (${grossDebt.length})` },
    { index: grossDebt.length, label: `Cash & Equivalents (${cash.length})` },
    { index: grossDebt.length + cash.length, label: `Debt-Like Items (${debtLike.length})` },
    {
      index: grossDebt.length + cash.length + debtLike.length,
      label: `Cash-Like Items (${cashLike.length})`,
    },
  ];

  const columns: Column<DebtItemRead>[] = [
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
      key: "source_account_code",
      header: "Account",
      width: "120px",
      render: (row) => (
        <span className="text-text-secondary font-mono text-xs">
          {row.source_account_code ?? "-"}
        </span>
      ),
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
      key: "detection_method",
      header: "Detection",
      width: "140px",
      render: (row) => (
        <div className="flex items-center gap-1">
          <span className="text-text-secondary">{row.detection_method}</span>
          {row.confidence_score && (
            <span className="text-xs text-text-secondary">
              ({Number(row.confidence_score).toFixed(0)}%)
            </span>
          )}
        </div>
      ),
    },
    {
      key: "status",
      header: "Status",
      align: "center",
      width: "100px",
      render: (row) => <Badge variant={STATUS_VARIANTS[row.status]}>{row.status}</Badge>,
    },
    {
      key: "actions",
      header: "Actions",
      width: "100px",
      render: (row) =>
        row.status === "CANDIDATE" || row.status === "PROPOSED" ? (
          <Button
            variant="accent"
            size="sm"
            icon={Check}
            onClick={() => onApprove(row.id)}
            disabled={isApproving}
          >
            Approve
          </Button>
        ) : null,
    },
  ];

  return (
    <Card title={`Debt & Cash Items (${items.length})`} headerBar padding="none">
      <DataTable
        columns={columns}
        data={allItems}
        keyField="id"
        striped
        compact
        sectionHeaders={sectionHeaders}
        emptyMessage="No debt items found"
      />
    </Card>
  );
}

// ── Add Manual Item Form ────────────────────────────────

function AddItemForm({
  onAdd,
  isAdding,
}: {
  onAdd: (item: { item_type: DebtItemType; description: string; amount: string }) => void;
  isAdding: boolean;
}) {
  const [itemType, setItemType] = useState<DebtItemType>("DEBT_LIKE");
  const [description, setDescription] = useState("");
  const [amount, setAmount] = useState("");

  const handleSubmit = () => {
    if (!description.trim() || !amount.trim()) return;
    onAdd({ item_type: itemType, description, amount });
    setDescription("");
    setAmount("");
  };

  return (
    <Card title="Add Manual Item" headerBar>
      <div className="flex items-end gap-4">
        <div className="w-48">
          <Select
            label="Type"
            value={itemType}
            onChange={(e) => setItemType(e.target.value as DebtItemType)}
            options={ITEM_TYPE_OPTIONS}
          />
        </div>
        <div className="flex-1">
          <Input
            label="Description"
            placeholder="e.g. 리스부채 (IFRS 16)"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </div>
        <div className="w-40">
          <Input
            label="Amount"
            placeholder="e.g. 500000"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
          />
        </div>
        <Button
          variant="primary"
          icon={Plus}
          onClick={handleSubmit}
          loading={isAdding}
          disabled={!description.trim() || !amount.trim()}
        >
          Add Item
        </Button>
      </div>
    </Card>
  );
}

// ── Main Net Debt Page ──────────────────────────────────

export default function NetDebtPage() {
  const { dealId } = useParams<{ dealId: string }>();
  const { data: debtList = [], isLoading } = useDebtCalculations(dealId!);
  const runMutation = useRunDebt(dealId!);

  const latestCalc = debtList.length > 0 ? debtList[0] : null;

  const { data: bridge } = useDebtBridge(dealId!, latestCalc?.id ?? "");

  const approveMutation = useApproveDebtItem(dealId!, latestCalc?.id ?? "");
  const recalcMutation = useRecalculateDebt(dealId!, latestCalc?.id ?? "");
  const addItemMutation = useAddDebtItem(dealId!, latestCalc?.id ?? "");

  const [snapshotId, setSnapshotId] = useState("");
  const [includeLease, setIncludeLease] = useState(false);
  const [includeDeferredRev, setIncludeDeferredRev] = useState(false);

  const handleRun = async () => {
    if (!snapshotId.trim()) return;
    try {
      await runMutation.mutateAsync({
        snapshot_id: snapshotId,
        include_lease_liabilities: includeLease,
        include_deferred_revenue: includeDeferredRev,
      });
      toast.success("Net Debt calculation completed");
    } catch {
      toast.error("Failed to calculate Net Debt");
    }
  };

  const handleApprove = async (itemId: string) => {
    try {
      await approveMutation.mutateAsync({
        itemId,
        body: { approved_by: "analyst" },
      });
      toast.success("Item approved");
    } catch {
      toast.error("Failed to approve item");
    }
  };

  const handleRecalculate = async () => {
    try {
      await recalcMutation.mutateAsync();
      toast.success("Net Debt recalculated");
    } catch {
      toast.error("Failed to recalculate");
    }
  };

  const handleAddItem = async (item: {
    item_type: DebtItemType;
    description: string;
    amount: string;
  }) => {
    try {
      await addItemMutation.mutateAsync(item);
      toast.success("Item added successfully");
    } catch {
      toast.error("Failed to add item");
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
          <h1 className="text-2xl font-heading font-bold text-text-dark">Net Debt Analysis</h1>
          <p className="text-text-secondary mt-1">Net Debt Bridge & Adjustments</p>
        </div>
        {!latestCalc && (
          <div className="flex items-center gap-3">
            <Input
              placeholder="Snapshot ID"
              value={snapshotId}
              onChange={(e) => setSnapshotId(e.target.value)}
              className="w-64"
            />
            <label className="flex items-center gap-2 text-sm text-text-body cursor-pointer">
              <input
                type="checkbox"
                checked={includeLease}
                onChange={(e) => setIncludeLease(e.target.checked)}
                className="rounded border-gray-border text-amic focus:ring-amic"
              />
              IFRS 16
            </label>
            <label className="flex items-center gap-2 text-sm text-text-body cursor-pointer">
              <input
                type="checkbox"
                checked={includeDeferredRev}
                onChange={(e) => setIncludeDeferredRev(e.target.checked)}
                className="rounded border-gray-border text-amic focus:ring-amic"
              />
              Deferred Rev
            </label>
            <Button
              variant="accent"
              icon={Calculator}
              onClick={handleRun}
              loading={runMutation.isPending}
              disabled={!snapshotId.trim()}
            >
              Calculate Net Debt
            </Button>
          </div>
        )}
      </div>

      {/* KPI Cards */}
      {latestCalc && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <KpiCard
            label="Gross Debt"
            value={formatAmount(latestCalc.gross_debt, "KRW")}
            icon={Landmark}
            variant="negative"
          />
          <KpiCard
            label="Cash & Equivalents"
            value={formatAmount(latestCalc.cash_and_equivalents, "KRW")}
            icon={Wallet}
            variant="positive"
          />
          <KpiCard
            label="Net Debt"
            value={formatAmount(latestCalc.net_debt, "KRW")}
            variant={Number(latestCalc.net_debt) > 0 ? "negative" : "positive"}
          />
          <KpiCard
            label="Adjusted Net Debt"
            value={formatAmount(latestCalc.adjusted_net_debt, "KRW")}
            variant={Number(latestCalc.adjusted_net_debt) > 0 ? "negative" : "positive"}
            subtitle={`v${latestCalc.engine_version}`}
          />
        </div>
      )}

      {/* Engine Options Tags */}
      {latestCalc && (latestCalc.include_lease_liabilities || latestCalc.include_deferred_revenue) && (
        <div className="flex items-center gap-2">
          {latestCalc.include_lease_liabilities && (
            <Badge variant="info">IFRS 16 Included</Badge>
          )}
          {latestCalc.include_deferred_revenue && (
            <Badge variant="warning">Deferred Revenue Included</Badge>
          )}
        </div>
      )}

      {/* Error */}
      {runMutation.isError && (
        <div className="bg-red-50 border border-negative/20 rounded-lg p-4 text-sm text-negative">
          Error: {runMutation.error.message}
        </div>
      )}

      {/* Empty State or Content */}
      {!latestCalc ? (
        <Card>
          <EmptyState
            icon={Landmark}
            title="No Net Debt Calculation"
            description="Enter a Snapshot ID and click 'Calculate Net Debt' to start analyzing."
            actionLabel="Calculate Net Debt"
            onAction={() => snapshotId.trim() && handleRun()}
          />
        </Card>
      ) : (
        <>
          {/* Bridge */}
          {bridge && (
            <BridgeTable
              bridge={bridge}
              onRecalculate={handleRecalculate}
              isRecalculating={recalcMutation.isPending}
            />
          )}

          {/* Debt Items */}
          <DebtItemsTable
            items={latestCalc.items}
            onApprove={handleApprove}
            isApproving={approveMutation.isPending}
          />

          {/* Add Manual Item */}
          <AddItemForm onAdd={handleAddItem} isAdding={addItemMutation.isPending} />
        </>
      )}
    </div>
  );
}

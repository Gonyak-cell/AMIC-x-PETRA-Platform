import { useState } from "react";
import { useParams } from "react-router-dom";
import {
  GitMerge,
  Wand2,
  Save,
  CheckCircle,
  CheckCheck,
  AlertTriangle,
} from "lucide-react";
import { toast } from "sonner";
import { useAuth } from "@/hooks/useAuth";
import { useDeal } from "@/modules/fdd/hooks/useDeals";
import {
  useMappings,
  useSuggestMappings,
  useSaveMappings,
  useApproveMapping,
  useApproveAllMappings,
  useStandardLineItems,
  useTieOutResults,
} from "@/modules/fdd/hooks/useMapping";
import type {
  MappingSuggestion,
  AccountMappingRead,
  MappingConfidence,
} from "@/modules/fdd/types/mapping";
import {
  Card,
  KpiCard,
  DataTable,
  Button,
  Badge,
  Spinner,
  EmptyState,
  PageHero,
} from "@/components/ui";
import type { Column } from "@/components/ui";
import { formatAmount } from "@/lib/format";
import heroImg from "@/assets/images/heroes/hero-arch-purple.jpg";

const CONFIDENCE_VARIANTS: Record<MappingConfidence, "success" | "warning" | "error" | "neutral"> = {
  HIGH: "success",
  MEDIUM: "warning",
  LOW: "error",
  UNMAPPED: "neutral",
};

const STATUS_VARIANTS: Record<string, "success" | "warning" | "error" | "info" | "neutral"> = {
  PROPOSED: "info",
  APPROVED: "success",
  REJECTED: "error",
  MANUAL: "neutral",
};

// ── Suggestions Table ─────────────────────────────────────

function SuggestionsTable({
  suggestions,
  onSaveAll,
  isSaving,
  currency,
}: {
  suggestions: MappingSuggestion[];
  onSaveAll: () => void;
  isSaving: boolean;
  currency: string;
}) {
  const columns: Column<MappingSuggestion>[] = [
    {
      key: "source_account_code",
      header: "Source Code",
      width: "120px",
      render: (row) => (
        <span className="font-mono text-xs">{row.source_account_code}</span>
      ),
    },
    {
      key: "source_account_name",
      header: "Source Name",
      render: (row) => (
        <span className="truncate max-w-xs block" title={row.source_account_name}>
          {row.source_account_name}
        </span>
      ),
    },
    {
      key: "suggested_target_code",
      header: "Target Code",
      width: "120px",
      render: (row) => (
        <span className="font-mono text-xs">
          {row.suggested_target_code || "-"}
        </span>
      ),
    },
    {
      key: "suggested_target_name_ko",
      header: "Target Name",
      render: (row) => row.suggested_target_name_ko || "-",
    },
    {
      key: "confidence",
      header: "Confidence",
      align: "center",
      width: "100px",
      render: (row) => (
        <Badge variant={CONFIDENCE_VARIANTS[row.confidence]}>
          {row.confidence}
        </Badge>
      ),
    },
    {
      key: "match_score",
      header: "Score",
      align: "right",
      width: "80px",
      mono: true,
      render: (row) => `${row.match_score}%`,
    },
    {
      key: "affected_amount",
      header: "Amount",
      align: "right",
      width: "120px",
      mono: true,
      render: (row) => formatAmount(row.affected_amount, currency),
    },
  ];

  return (
    <Card
      title={`Mapping Suggestions (${suggestions.length})`}
      headerBar
      padding="none"
      actions={
        <Button
          variant="secondary"
          size="sm"
          icon={Save}
          onClick={onSaveAll}
          loading={isSaving}
          disabled={suggestions.length === 0}
          className="bg-white/10 border-white/30 text-white hover:bg-white/20"
        >
          Save All as Proposed
        </Button>
      }
    >
      <DataTable
        columns={columns}
        data={suggestions}
        keyField="source_account_code"
        striped
        compact
        emptyMessage="No suggestions generated yet"
      />
    </Card>
  );
}

// ── Saved Mappings Table ──────────────────────────────────

function MappingsTable({
  mappings,
  onApprove,
  onApproveAll,
  isApproving,
  currency,
}: {
  mappings: AccountMappingRead[];
  onApprove: (mappingId: string) => void;
  onApproveAll: () => void;
  isApproving: boolean;
  currency: string;
}) {
  const proposed = mappings.filter((m) => m.status === "PROPOSED");

  const columns: Column<AccountMappingRead>[] = [
    {
      key: "source_account_code",
      header: "Source Code",
      width: "120px",
      render: (row) => (
        <span className="font-mono text-xs">{row.source_account_code}</span>
      ),
    },
    {
      key: "source_account_name",
      header: "Source Name",
      render: (row) => (
        <span className="truncate max-w-xs block" title={row.source_account_name}>
          {row.source_account_name}
        </span>
      ),
    },
    {
      key: "target_line_item_code",
      header: "Target Code",
      width: "120px",
      render: (row) => (
        <span className="font-mono text-xs">{row.target_line_item_code}</span>
      ),
    },
    {
      key: "confidence",
      header: "Confidence",
      align: "center",
      width: "100px",
      render: (row) => (
        <Badge variant={CONFIDENCE_VARIANTS[row.confidence]}>
          {row.confidence}
        </Badge>
      ),
    },
    {
      key: "status",
      header: "Status",
      align: "center",
      width: "100px",
      render: (row) => (
        <Badge variant={STATUS_VARIANTS[row.status] ?? "neutral"}>
          {row.status}
        </Badge>
      ),
    },
    {
      key: "affected_amount",
      header: "Amount",
      align: "right",
      width: "120px",
      mono: true,
      render: (row) => formatAmount(row.affected_amount, currency),
    },
    {
      key: "actions",
      header: "Actions",
      width: "100px",
      render: (row) =>
        row.status === "PROPOSED" ? (
          <Button
            variant="accent"
            size="sm"
            icon={CheckCircle}
            onClick={() => onApprove(row.id)}
            disabled={isApproving}
          >
            Approve
          </Button>
        ) : null,
    },
  ];

  return (
    <Card
      title={`Saved Mappings (${mappings.length})`}
      headerBar
      padding="none"
      actions={
        proposed.length > 0 ? (
          <Button
            variant="secondary"
            size="sm"
            icon={CheckCheck}
            onClick={onApproveAll}
            loading={isApproving}
            className="bg-white/10 border-white/30 text-white hover:bg-white/20"
          >
            Approve All ({proposed.length})
          </Button>
        ) : undefined
      }
    >
      <DataTable
        columns={columns}
        data={mappings}
        keyField="id"
        striped
        compact
        emptyMessage="No mappings saved yet"
      />
    </Card>
  );
}

// ── Tie-out Results ─────────────────────────────────────

function TieOutSection({ dealId, currency }: { dealId: string; currency: string }) {
  const { data: results } = useTieOutResults(dealId);

  if (!results || results.length === 0) {
    return (
      <Card title="Tie-out Validation" headerBar>
        <EmptyState
          icon={AlertTriangle}
          title="No tie-out results"
          description="Approve mappings and run tie-out validation to verify data integrity."
        />
      </Card>
    );
  }

  return (
    <Card title="Tie-out Validation" headerBar padding="none">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 p-4">
        {results.map((r) => {
          const isPassing = r.status === "PASS";
          const isWarning = r.status === "WARNING";

          return (
            <div
              key={r.id}
              className={`border-l-4 rounded-lg p-4 ${
                isPassing
                  ? "border-positive bg-bg-light-green/30"
                  : isWarning
                    ? "border-caution bg-amber-50/30"
                    : "border-negative bg-red-50/30"
              }`}
            >
              <div className="flex justify-between items-center mb-3">
                <h4 className="font-heading font-semibold text-text-dark">
                  {r.statement_type === "IS" ? "Income Statement" : "Balance Sheet"}
                </h4>
                <Badge
                  variant={isPassing ? "success" : isWarning ? "warning" : "error"}
                >
                  {r.status}
                </Badge>
              </div>
              <dl className="grid grid-cols-2 gap-3 text-sm">
                <div>
                  <dt className="text-text-secondary">TB Total</dt>
                  <dd className="font-mono tabular-nums font-medium">
                    {formatAmount(r.tb_total, currency)}
                  </dd>
                </div>
                <div>
                  <dt className="text-text-secondary">Reconstructed</dt>
                  <dd className="font-mono tabular-nums font-medium">
                    {formatAmount(r.reconstructed_total, currency)}
                  </dd>
                </div>
                <div>
                  <dt className="text-text-secondary">Variance</dt>
                  <dd className="font-mono tabular-nums font-medium">
                    {formatAmount(r.variance, currency)}
                  </dd>
                </div>
                <div>
                  <dt className="text-text-secondary">Variance %</dt>
                  <dd className="font-mono tabular-nums font-medium">
                    {r.variance_percentage}%
                  </dd>
                </div>
                <div>
                  <dt className="text-text-secondary">Unmapped Accounts</dt>
                  <dd className="font-medium">{r.unmapped_account_count}</dd>
                </div>
                <div>
                  <dt className="text-text-secondary">Unmapped Total</dt>
                  <dd className="font-mono tabular-nums font-medium">
                    {formatAmount(r.unmapped_total, currency)}
                  </dd>
                </div>
              </dl>
            </div>
          );
        })}
      </div>
    </Card>
  );
}

// ── Main Page ────────────────────────────────────────────

export default function MappingPage() {
  const { dealId } = useParams<{ dealId: string }>();
  const { user } = useAuth();
  const { data: deal } = useDeal(dealId!);
  const currency = deal?.base_currency ?? "KRW";
  const [suggestions, setSuggestions] = useState<MappingSuggestion[]>([]);

  const { data: mappings = [], isLoading } = useMappings(dealId!);
  const { data: lineItems } = useStandardLineItems();
  const suggestMutation = useSuggestMappings(dealId!);
  const saveMutation = useSaveMappings(dealId!);
  const approveMutation = useApproveMapping(dealId!);
  const approveAllMutation = useApproveAllMappings(dealId!);

  const handleSuggest = async () => {
    try {
      const result = await suggestMutation.mutateAsync();
      setSuggestions(result);
      toast.success(`Generated ${result.length} mapping suggestions`);
    } catch {
      toast.error("Failed to generate suggestions");
    }
  };

  const handleSaveAll = async () => {
    const validSuggestions = suggestions.filter(
      (s) => s.suggested_target_code !== ""
    );
    if (validSuggestions.length === 0) return;

    try {
      await saveMutation.mutateAsync({
        mappings: validSuggestions.map((s) => ({
          source_account_code: s.source_account_code,
          source_account_name: s.source_account_name,
          target_line_item_code: s.suggested_target_code,
          confidence: s.confidence,
          match_score: s.match_score,
          algorithm: s.algorithm,
          affected_amount: s.affected_amount,
        })),
      });
      setSuggestions([]);
      toast.success(`Saved ${validSuggestions.length} mappings`);
    } catch {
      toast.error("Failed to save mappings");
    }
  };

  const handleApprove = async (mappingId: string) => {
    try {
      await approveMutation.mutateAsync({
        mappingId,
        body: { approved_by: user?.email ?? "unknown" },
      });
      toast.success("Mapping approved");
    } catch {
      toast.error("Failed to approve mapping");
    }
  };

  const handleApproveAll = async () => {
    try {
      await approveAllMutation.mutateAsync({ approved_by: user?.email ?? "unknown" });
      toast.success("All mappings approved");
    } catch {
      toast.error("Failed to approve all mappings");
    }
  };

  // KPI 계산
  const approvedCount = mappings.filter((m) => m.status === "APPROVED").length;
  const proposedCount = mappings.filter((m) => m.status === "PROPOSED").length;
  const highConfidenceCount = mappings.filter((m) => m.confidence === "HIGH").length;

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
      <PageHero
        title="Account Mapping"
        subtitle={`${lineItems?.length ?? 0} standard line items available`}
        compact
        backgroundImage={heroImg}
        backgroundOpacity={0.18}
        actions={
          <Button
            variant="accent"
            icon={Wand2}
            onClick={handleSuggest}
            loading={suggestMutation.isPending}
          >
            Auto-Suggest Mappings
          </Button>
        }
      />

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard
          label="Total Mappings"
          value={String(mappings.length)}
          icon={GitMerge}
        />
        <KpiCard
          label="Approved"
          value={String(approvedCount)}
          variant="positive"
        />
        <KpiCard
          label="Pending"
          value={String(proposedCount)}
          variant="caution"
        />
        <KpiCard
          label="High Confidence"
          value={String(highConfidenceCount)}
          subtitle={`${mappings.length > 0 ? Math.round((highConfidenceCount / mappings.length) * 100) : 0}% of total`}
        />
      </div>

      {/* Error display */}
      {suggestMutation.isError && (
        <div className="bg-red-50 border border-negative/20 rounded-lg p-4 text-sm text-negative">
          {suggestMutation.error?.message || "Failed to generate suggestions"}
        </div>
      )}

      {/* Suggestions section */}
      {suggestions.length > 0 && (
        <SuggestionsTable
          suggestions={suggestions}
          onSaveAll={handleSaveAll}
          isSaving={saveMutation.isPending}
          currency={currency}
        />
      )}

      {/* Saved mappings section */}
      {mappings.length > 0 && (
        <MappingsTable
          mappings={mappings}
          onApprove={handleApprove}
          onApproveAll={handleApproveAll}
          isApproving={approveMutation.isPending || approveAllMutation.isPending}
          currency={currency}
        />
      )}

      {/* Empty state */}
      {mappings.length === 0 && suggestions.length === 0 && (
        <Card>
          <EmptyState
            icon={GitMerge}
            title="No Mappings"
            description="Upload a Trial Balance file first, then click 'Auto-Suggest Mappings' to start."
          />
        </Card>
      )}

      {/* Tie-out Results */}
      <TieOutSection dealId={dealId!} currency={currency} />
    </div>
  );
}

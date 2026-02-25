import { useCallback, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import {
  AlertTriangle,
  AlertCircle,
  CheckCircle,
  XCircle,
  ChevronDown,
  ChevronUp,
  Search,
  ScanLine,
} from "lucide-react";
import { toast } from "sonner";
import { useAuth } from "@/hooks/useAuth";
import {
  useIssues,
  useIssueSummary,
  useRunAnomalyDetection,
  useResolveIssue,
  useDismissIssue,
} from "@/modules/fdd/hooks/useIssues";
import type { IssueRead, IssueSeverity, IssueStatus } from "@/modules/fdd/types/issue";
import {
  Card,
  KpiCard,
  Button,
  Badge,
  Select,
  Spinner,
  EmptyState,
  PageHero,
} from "@/components/ui";
import type { SelectOption } from "@/components/ui";
import { CommentThread } from "@/components/collaboration/CommentThread";
import heroImg from "@/assets/images/heroes/hero-arch-wave.jpg";

const SEVERITY_VARIANTS: Record<IssueSeverity, "error" | "warning" | "info" | "success"> = {
  CRITICAL: "error",
  HIGH: "error",
  MEDIUM: "warning",
  LOW: "success",
};

const SEVERITY_ICONS: Record<IssueSeverity, typeof AlertCircle> = {
  CRITICAL: XCircle,
  HIGH: AlertCircle,
  MEDIUM: AlertTriangle,
  LOW: CheckCircle,
};

const STATUS_VARIANTS: Record<IssueStatus, "success" | "warning" | "error" | "info" | "neutral"> = {
  OPEN: "info",
  UNDER_REVIEW: "warning",
  RESOLVED: "success",
  FALSE_POSITIVE: "neutral",
  ACKNOWLEDGED: "neutral",
};

const SEVERITY_OPTIONS: SelectOption[] = [
  { value: "", label: "All Severities" },
  { value: "CRITICAL", label: "Critical" },
  { value: "HIGH", label: "High" },
  { value: "MEDIUM", label: "Medium" },
  { value: "LOW", label: "Low" },
];

const STATUS_OPTIONS: SelectOption[] = [
  { value: "", label: "All Statuses" },
  { value: "OPEN", label: "Open" },
  { value: "UNDER_REVIEW", label: "Under Review" },
  { value: "RESOLVED", label: "Resolved" },
  { value: "FALSE_POSITIVE", label: "False Positive" },
  { value: "ACKNOWLEDGED", label: "Acknowledged" },
];

const CATEGORY_OPTIONS: SelectOption[] = [
  { value: "", label: "All Categories" },
  { value: "ANOMALY", label: "Anomaly" },
  { value: "DATA_QUALITY", label: "Data Quality" },
  { value: "MAPPING", label: "Mapping" },
  { value: "CALCULATION", label: "Calculation" },
  { value: "AI_SUGGESTION", label: "AI Suggestion" },
];

function formatRiskScore(raw: string | null): string {
  if (!raw) return "-";
  const n = parseFloat(raw);
  return Number.isNaN(n) ? "-" : `${n.toFixed(1)}%`;
}

// ── Issue Row ────────────────────────────────────────────

function IssueRow({
  issue,
  onResolve,
  onDismiss,
  isProcessing,
}: {
  issue: IssueRead;
  onResolve: (issueId: string) => void;
  onDismiss: (issueId: string) => void;
  isProcessing: boolean;
}) {
  const [expanded, setExpanded] = useState(false);
  const SeverityIcon = SEVERITY_ICONS[issue.severity];

  return (
    <div className="border-b border-gray-border last:border-b-0">
      <div
        className="flex items-center gap-4 p-4 hover:bg-bg-cool cursor-pointer transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        {/* Severity */}
        <div className="w-24 flex items-center gap-2">
          <SeverityIcon
            className={`h-4 w-4 ${
              issue.severity === "CRITICAL" || issue.severity === "HIGH"
                ? "text-negative"
                : issue.severity === "MEDIUM"
                  ? "text-caution"
                  : "text-positive"
            }`}
          />
          <Badge variant={SEVERITY_VARIANTS[issue.severity]} className="text-xs">
            {issue.severity}
          </Badge>
        </div>

        {/* Issue Info */}
        <div className="flex-1 min-w-0">
          <div className="font-medium text-text-dark truncate">{issue.title}</div>
          <div className="text-xs text-text-secondary">{issue.category}</div>
        </div>

        {/* Status */}
        <div className="w-24">
          <Badge variant={STATUS_VARIANTS[issue.status]}>
            {issue.status.replace("_", " ")}
          </Badge>
        </div>

        {/* Detection Method */}
        <div className="w-32 text-sm text-text-secondary hidden md:block">
          {issue.detection_method}
        </div>

        {/* Risk Score */}
        <div className="w-20 text-sm font-mono tabular-nums text-right">
          {formatRiskScore(issue.risk_score)}
        </div>

        {/* Expand Icon */}
        <div className="w-8 flex justify-center">
          {expanded ? (
            <ChevronUp className="h-5 w-5 text-text-secondary" />
          ) : (
            <ChevronDown className="h-5 w-5 text-text-secondary" />
          )}
        </div>
      </div>

      {/* Expanded Details */}
      {expanded && (
        <div className="px-4 pb-4 bg-bg-cool">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
            <div>
              <h4 className="text-xs font-heading font-semibold text-text-dark mb-1">
                Description
              </h4>
              <p className="text-sm text-text-body">{issue.description}</p>
            </div>
            <div>
              <h4 className="text-xs font-heading font-semibold text-text-dark mb-1">
                Source
              </h4>
              <p className="text-sm text-text-body">
                {issue.source_type
                  ? `${issue.source_type}: ${issue.source_id || "N/A"}`
                  : "N/A"}
              </p>
            </div>
          </div>

          {issue.detection_factors && issue.detection_factors.length > 0 && (
            <div className="mb-4">
              <h4 className="text-xs font-heading font-semibold text-text-dark mb-2">
                Detection Factors
              </h4>
              <div className="flex flex-wrap gap-2">
                {issue.detection_factors.map((factor, idx) => (
                  <span
                    key={idx}
                    className="px-2 py-1 bg-bg-cool border border-gray-border rounded text-xs text-text-body"
                  >
                    {Object.entries(factor)
                      .map(([k, v]) => `${k}: ${String(v)}`)
                      .join(", ")}
                  </span>
                ))}
              </div>
            </div>
          )}

          {issue.resolution_note && (
            <div className="mb-4">
              <h4 className="text-xs font-heading font-semibold text-text-dark mb-1">
                Resolution Note
              </h4>
              <p className="text-sm text-text-body">{issue.resolution_note}</p>
            </div>
          )}

          {issue.status === "OPEN" && (
            <div className="flex gap-2 mb-4">
              <Button
                variant="accent"
                size="sm"
                icon={CheckCircle}
                onClick={(e) => {
                  e.stopPropagation();
                  onResolve(issue.id);
                }}
                disabled={isProcessing}
              >
                Resolve
              </Button>
              <Button
                variant="ghost"
                size="sm"
                icon={XCircle}
                onClick={(e) => {
                  e.stopPropagation();
                  onDismiss(issue.id);
                }}
                disabled={isProcessing}
              >
                Dismiss
              </Button>
            </div>
          )}

          {/* Comments */}
          <div
            className="border-t border-gray-border pt-4 mt-2"
            onClick={(e) => e.stopPropagation()}
          >
            <CommentThread entityType="issue" entityId={issue.id} />
          </div>
        </div>
      )}
    </div>
  );
}

// ── Main Component ───────────────────────────────────────

export default function IssuesPage() {
  const { dealId } = useParams<{ dealId: string }>();
  const { user } = useAuth();
  const [filters, setFilters] = useState({
    severity: "",
    status: "",
    category: "",
  });

  const issueFilters = useMemo(
    () => ({
      severity: filters.severity || undefined,
      status: filters.status || undefined,
      category: filters.category || undefined,
      limit: 100,
    }),
    [filters.severity, filters.status, filters.category],
  );

  const {
    data: issuesData,
    isLoading: issuesLoading,
    error: issuesError,
  } = useIssues(dealId!, issueFilters);

  const { data: summary, isLoading: summaryLoading } = useIssueSummary(dealId!);

  const runDetection = useRunAnomalyDetection(dealId!);
  const resolveIssue = useResolveIssue(dealId!);
  const dismissIssue = useDismissIssue(dealId!);

  const handleFilterChange = (key: string, value: string) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
  };

  const handleRunDetection = async () => {
    try {
      await runDetection.mutateAsync({ threshold: "50.0" });
      toast.success("Anomaly detection completed");
    } catch (err) {
      console.error("Anomaly detection failed:", err);
      toast.error("Failed to run anomaly detection");
    }
  };

  const handleResolve = useCallback(async (issueId: string) => {
    try {
      await resolveIssue.mutateAsync({
        issueId,
        resolved_by: user?.email ?? "unknown",
      });
      toast.success("Issue resolved");
    } catch (err) {
      console.error("Resolve issue failed:", err);
      toast.error("Failed to resolve issue");
    }
  }, [resolveIssue, user?.email]);

  const handleDismiss = useCallback(async (issueId: string) => {
    try {
      await dismissIssue.mutateAsync({
        issueId,
        resolution_note: `Dismissed by ${user?.email ?? "unknown"}`,
      });
      toast.success("Issue dismissed");
    } catch (err) {
      console.error("Dismiss issue failed:", err);
      toast.error("Failed to dismiss issue");
    }
  }, [dismissIssue, user?.email]);

  if (!dealId) {
    return (
      <div className="p-4 text-negative">Deal ID not found</div>
    );
  }

  if (issuesLoading || summaryLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Spinner size="lg" />
      </div>
    );
  }

  // KPI 계산
  const totalCount = summary?.total ?? 0;
  const criticalHighCount =
    (summary?.by_severity?.["CRITICAL"] ?? 0) +
    (summary?.by_severity?.["HIGH"] ?? 0);
  const openCount = summary?.by_status?.["OPEN"] ?? 0;
  const resolvedCount = summary?.by_status?.["RESOLVED"] ?? 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <PageHero
        title="Issue Log"
        subtitle="Track and manage FDD findings"
        compact
        backgroundImage={heroImg}
        backgroundOpacity={0.18}
        actions={
          <Button
            variant="accent"
            icon={ScanLine}
            onClick={handleRunDetection}
            loading={runDetection.isPending}
          >
            Run Anomaly Detection
          </Button>
        }
      />

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard
          label="Total Issues"
          value={String(totalCount)}
          icon={AlertTriangle}
        />
        <KpiCard
          label="Critical/High"
          value={String(criticalHighCount)}
          variant={criticalHighCount > 0 ? "negative" : "default"}
          icon={AlertCircle}
        />
        <KpiCard
          label="Open"
          value={String(openCount)}
          variant={openCount > 0 ? "caution" : "default"}
          icon={Search}
        />
        <KpiCard
          label="Resolved"
          value={String(resolvedCount)}
          variant="positive"
          icon={CheckCircle}
        />
      </div>

      {/* Filters */}
      <Card padding="sm">
        <div className="flex flex-wrap gap-4">
          <div className="w-40">
            <Select
              value={filters.severity}
              onChange={(e) => handleFilterChange("severity", e.target.value)}
              options={SEVERITY_OPTIONS}
            />
          </div>
          <div className="w-40">
            <Select
              value={filters.status}
              onChange={(e) => handleFilterChange("status", e.target.value)}
              options={STATUS_OPTIONS}
            />
          </div>
          <div className="w-48">
            <Select
              value={filters.category}
              onChange={(e) => handleFilterChange("category", e.target.value)}
              options={CATEGORY_OPTIONS}
            />
          </div>
        </div>
      </Card>

      {/* Issues Table */}
      <Card padding="none">
        {/* Table Header */}
        <div className="flex items-center gap-4 p-4 border-b border-gray-border bg-table-header text-white text-sm font-heading font-semibold rounded-t-lg">
          <div className="w-24">Severity</div>
          <div className="flex-1">Issue</div>
          <div className="w-24">Status</div>
          <div className="w-32 hidden md:block">Detection</div>
          <div className="w-20 text-right">Risk</div>
          <div className="w-8"></div>
        </div>

        {/* Error State */}
        {issuesError && (
          <div className="p-8 text-center text-negative">
            Failed to load issues
          </div>
        )}

        {/* Empty State */}
        {!issuesError && issuesData?.items.length === 0 && (
          <EmptyState
            icon={AlertTriangle}
            title="No issues found"
            description="Run anomaly detection to scan for potential issues in the financial data."
            actionLabel="Run Anomaly Detection"
            onAction={handleRunDetection}
          />
        )}

        {/* Issue Rows */}
        {issuesData?.items.map((issue) => (
          <IssueRow
            key={issue.id}
            issue={issue}
            onResolve={handleResolve}
            onDismiss={handleDismiss}
            isProcessing={resolveIssue.isPending || dismissIssue.isPending}
          />
        ))}
      </Card>

      {/* Pagination Info */}
      {issuesData && issuesData.items.length > 0 && (
        <div className="text-sm text-text-secondary">
          Showing {issuesData.items.length} of {issuesData.total} issues
        </div>
      )}
    </div>
  );
}

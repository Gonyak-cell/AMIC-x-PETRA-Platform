import { useState } from "react";
import { ShieldAlert, Search, PlayCircle } from "lucide-react";
import { toast } from "sonner";
import {
  useClassifiedSanctions,
  useSanctionSummary,
  useClassifySanctions,
} from "@/modules/kiis/hooks/useSanctions";
import {
  Card,
  KpiCard,
  DataTable,
  Input,
  Button,
  Badge,
  EmptyState,
  Spinner,
} from "@/components/ui";
import type { Column } from "@/components/ui";
import type { ClassifiedSanctionItem } from "@/modules/kiis/types/sanction";
import { formatDate } from "@/lib/format";

const severityVariant: Record<string, "error" | "warning" | "info"> = {
  critical: "error",
  warning: "warning",
  caution: "info",
};

const columns: Column<ClassifiedSanctionItem>[] = [
  {
    key: "sanctions_type",
    header: "Type",
    render: (row) => (
      <span className="font-medium text-text-dark">{row.sanctions_type}</span>
    ),
  },
  { key: "sanctions_detail", header: "Detail" },
  { key: "sanctions_agency", header: "Agency", width: "140px" },
  {
    key: "sanctions_date",
    header: "Date",
    align: "center",
    width: "120px",
    render: (row) => formatDate(row.sanctions_date, "short"),
  },
  {
    key: "severity",
    header: "Severity",
    align: "center",
    width: "100px",
    render: (row) => (
      <Badge variant={severityVariant[row.severity] ?? "neutral"}>
        {row.severity}
      </Badge>
    ),
  },
  {
    key: "category",
    header: "Category",
    width: "120px",
    render: (row) => row.category ?? "-",
  },
];

export default function SanctionListPage() {
  const [corpCode, setCorpCode] = useState("");
  const [searchInput, setSearchInput] = useState("");

  const { data: sanctions, isLoading } = useClassifiedSanctions(corpCode);
  const { data: summary } = useSanctionSummary(corpCode);
  const classify = useClassifySanctions(corpCode);

  const handleSearch = () => {
    setCorpCode(searchInput.trim());
  };

  const handleClassify = () => {
    if (!corpCode) return;
    classify.mutate(undefined, {
      onSuccess: () => toast.success("Classification completed"),
      onError: () => toast.error("Classification failed"),
    });
  };

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-heading font-bold text-text-dark">
        Sanctions
      </h1>

      {/* Search */}
      <div className="flex gap-3 items-end">
        <div className="flex-1 max-w-sm">
          <Input
            label="Company Code / Name"
            placeholder="Enter corp code..."
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSearch()}
          />
        </div>
        <Button variant="primary" icon={Search} onClick={handleSearch}>
          Search
        </Button>
        {corpCode && (
          <Button
            variant="secondary"
            icon={PlayCircle}
            onClick={handleClassify}
            loading={classify.isPending}
          >
            Classify
          </Button>
        )}
      </div>

      {/* Summary KPIs */}
      {corpCode && summary && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <KpiCard
            label="Caution"
            value={String(summary.caution_count)}
            icon={ShieldAlert}
          />
          <KpiCard
            label="Warning"
            value={String(summary.warning_count)}
            icon={ShieldAlert}
            variant="caution"
          />
          <KpiCard
            label="Critical"
            value={String(summary.critical_count)}
            icon={ShieldAlert}
            variant="negative"
          />
        </div>
      )}

      {/* Table */}
      <Card padding="none">
        {!corpCode ? (
          <EmptyState
            icon={ShieldAlert}
            title="Search for a company"
            description="Enter a company code or name to view sanctions."
          />
        ) : isLoading ? (
          <Spinner />
        ) : !sanctions?.length ? (
          <EmptyState
            icon={ShieldAlert}
            title="No sanctions found"
            description="No classified sanctions for this company."
          />
        ) : (
          <DataTable
            columns={columns}
            data={sanctions}
            keyField="id"
            striped
          />
        )}
      </Card>
    </div>
  );
}

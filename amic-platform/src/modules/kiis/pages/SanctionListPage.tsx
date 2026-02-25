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
  Pagination,
  PageHero,
} from "@/components/ui";
import type { Column } from "@/components/ui";
import type { ClassifiedSanctionListItem } from "@/modules/kiis/types/sanction";
import { formatDate } from "@/lib/format";
import { SEVERITY_VARIANT } from "@/modules/kiis/constants/variants";
import heroImg from "@/assets/images/heroes/forestgp-nature.jpg";

const columns: Column<ClassifiedSanctionListItem>[] = [
  {
    key: "sanctions_type",
    header: "Type",
    render: (row) => (
      <span className="font-medium text-text-dark">{row.sanctions_type}</span>
    ),
  },
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
      <Badge variant={SEVERITY_VARIANT[row.severity] ?? "neutral"}>
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
  const [page, setPage] = useState(1);

  const { data: sanctions, isLoading } = useClassifiedSanctions(corpCode, { page, size: 20 });
  const { data: summary } = useSanctionSummary(corpCode);
  const classify = useClassifySanctions(corpCode);

  const totalPages = sanctions ? Math.ceil(sanctions.total / 20) : 0;

  const handleSearch = () => {
    setCorpCode(searchInput.trim());
    setPage(1);
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
      <PageHero title="Sanctions" subtitle="Search and classify company sanctions" compact backgroundImage={heroImg} backgroundOpacity={0.18} />

      {/* Search */}
      <div className="flex gap-3 items-end">
        <div className="flex-1 max-w-sm">
          <Input
            label="Company Code"
            placeholder="Enter corp code (e.g. 00126380)..."
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
            description="Enter a company code to view sanctions."
          />
        ) : isLoading ? (
          <Spinner />
        ) : !sanctions?.items.length ? (
          <EmptyState
            icon={ShieldAlert}
            title="No sanctions found"
            description="No classified sanctions for this company."
          />
        ) : (
          <DataTable
            columns={columns}
            data={sanctions.items}
            keyField="id"
            striped
          />
        )}
      </Card>

      {corpCode && totalPages > 1 && (
        <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />
      )}
    </div>
  );
}

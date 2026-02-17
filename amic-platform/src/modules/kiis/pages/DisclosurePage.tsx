import { useState } from "react";
import { ScrollText, RefreshCw, ExternalLink } from "lucide-react";
import { toast } from "sonner";
import {
  useDisclosures,
  useSyncDartDisclosures,
  useSyncKofiaDisclosures,
} from "@/modules/kiis/hooks/useDisclosures";
import {
  Card,
  DataTable,
  Select,
  Button,
  Badge,
  EmptyState,
  Spinner,
  Pagination,
  PageHero,
} from "@/components/ui";
import type { Column } from "@/components/ui";
import type {
  DisclosureItem,
  DisclosureType,
} from "@/modules/kiis/types/disclosure";
import { formatDate } from "@/lib/format";
import CorpCodeInput from "@/modules/kiis/components/CorpCodeInput";

const TYPE_OPTIONS = [
  { value: "", label: "All Types" },
  { value: "annual_report", label: "Annual Report" },
  { value: "audit_report", label: "Audit Report" },
  { value: "quarterly", label: "Quarterly" },
  { value: "semi_annual", label: "Semi-annual" },
  { value: "material", label: "Material" },
  { value: "sanction", label: "Sanction" },
  { value: "other", label: "Other" },
];

const typeVariant: Record<string, "info" | "success" | "warning" | "error" | "neutral"> = {
  annual_report: "info",
  audit_report: "success",
  quarterly: "info",
  semi_annual: "info",
  material: "warning",
  sanction: "error",
  other: "neutral",
};

const columns: Column<DisclosureItem>[] = [
  {
    key: "report_nm",
    header: "Report",
    render: (row) => (
      <span className="font-medium text-text-dark">{row.report_nm}</span>
    ),
  },
  {
    key: "rcept_no",
    header: "Receipt No.",
    width: "140px",
    render: (row) => <span className="font-mono text-xs">{row.rcept_no}</span>,
  },
  {
    key: "rcept_dt",
    header: "Date",
    align: "center",
    width: "120px",
    render: (row) => formatDate(row.rcept_dt, "short"),
  },
  {
    key: "disclosure_type",
    header: "Type",
    align: "center",
    width: "120px",
    render: (row) => (
      <Badge variant={typeVariant[row.disclosure_type ?? ""] ?? "neutral"}>
        {row.disclosure_type ?? "-"}
      </Badge>
    ),
  },
  {
    key: "source",
    header: "Source",
    align: "center",
    width: "80px",
    render: (row) => (
      <Badge variant={row.source === "dart" ? "info" : "neutral"}>
        {(row.source ?? "").toUpperCase() || "-"}
      </Badge>
    ),
  },
  {
    key: "dart_viewer_url",
    header: "Link",
    align: "center",
    width: "80px",
    render: (row) => {
      const url = row.dart_viewer_url || row.kofia_url;
      if (!url) return "-";
      return (
        <a
          href={url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-accent hover:text-accent-hover"
          onClick={(e) => e.stopPropagation()}
        >
          <ExternalLink className="h-4 w-4 inline" />
        </a>
      );
    },
  },
];

export default function DisclosurePage() {
  const [corpCode, setCorpCode] = useState("");
  const [disclosureType, setDisclosureType] = useState("");
  const [page, setPage] = useState(1);

  const { data, isLoading, isError } = useDisclosures(corpCode, {
    disclosure_type: (disclosureType as DisclosureType) || undefined,
    page,
    size: 20,
  });
  const syncDart = useSyncDartDisclosures(corpCode);
  const syncKofia = useSyncKofiaDisclosures(corpCode);

  const handleSearch = (code: string) => {
    setCorpCode(code);
    setPage(1);
  };

  const handleSyncDart = () => {
    if (!corpCode) return;
    syncDart.mutate(undefined, {
      onSuccess: (res) =>
        toast.success(`DART: synced ${res.synced_count}, skipped ${res.skipped_count}`),
      onError: () => toast.error("DART sync failed"),
    });
  };

  const handleSyncKofia = () => {
    if (!corpCode) return;
    syncKofia.mutate(undefined, {
      onSuccess: (res) =>
        toast.success(`KOFIA: synced ${res.synced_count}, skipped ${res.skipped_count}`),
      onError: () => toast.error("KOFIA sync failed"),
    });
  };

  const totalPages = data ? Math.ceil(data.total / 20) : 0;

  return (
    <div className="space-y-6">
      <PageHero
        title="Disclosures"
        subtitle="DART and KOFIA disclosure filings"
        compact
      />

      <div className="flex gap-3 items-end flex-wrap">
        <CorpCodeInput onSearch={handleSearch} />
        <div className="w-48">
          <Select
            label="Type"
            options={TYPE_OPTIONS}
            value={disclosureType}
            onChange={(e) => {
              setDisclosureType(e.target.value);
              setPage(1);
            }}
          />
        </div>
        {corpCode && (
          <>
            <Button
              variant="secondary"
              icon={RefreshCw}
              onClick={handleSyncDart}
              loading={syncDart.isPending}
            >
              Sync DART
            </Button>
            <Button
              variant="secondary"
              icon={RefreshCw}
              onClick={handleSyncKofia}
              loading={syncKofia.isPending}
            >
              Sync KOFIA
            </Button>
          </>
        )}
      </div>

      <Card padding="none">
        {!corpCode ? (
          <EmptyState
            icon={ScrollText}
            title="Search for a company"
            description="Enter a company code to view disclosures."
          />
        ) : isLoading ? (
          <Spinner />
        ) : isError ? (
          <EmptyState
            icon={ScrollText}
            title="Failed to load disclosures"
            description="An error occurred while fetching disclosures."
          />
        ) : !data?.items.length ? (
          <EmptyState
            icon={ScrollText}
            title="No disclosures found"
            description="No disclosures for this company."
          />
        ) : (
          <DataTable
            columns={columns}
            data={data.items}
            keyField="id"
            striped
          />
        )}
      </Card>

      {corpCode && (
        <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />
      )}
    </div>
  );
}

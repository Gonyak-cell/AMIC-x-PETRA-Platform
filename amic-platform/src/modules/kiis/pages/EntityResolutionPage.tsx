import { useState } from "react";
import { GitCompare, Search, Trash2, CheckCircle } from "lucide-react";
import { toast } from "sonner";
import {
  useResolveEntity,
  useAliases,
  useCreateAlias,
  useDeleteAlias,
} from "@/modules/kiis/hooks/useEntities";
import {
  Card,
  DataTable,
  Input,
  Button,
  Badge,
  EmptyState,
  Spinner,
  PageHero,
} from "@/components/ui";
import type { Column } from "@/components/ui";
import type {
  EntityResolveResponse,
  EntityMatchItem,
  AliasItem,
} from "@/modules/kiis/types/entity";
import AliasCreateForm from "@/modules/kiis/components/AliasCreateForm";

const candidateColumns: Column<EntityMatchItem>[] = [
  {
    key: "corp_name",
    header: "Company",
    render: (row) => (
      <span className="font-medium text-text-dark">{row.corp_name}</span>
    ),
  },
  {
    key: "corp_code",
    header: "Code",
    width: "120px",
    render: (row) => <span className="font-mono text-xs">{row.corp_code}</span>,
  },
  {
    key: "similarity",
    header: "Similarity",
    align: "center",
    width: "100px",
    render: (row) => `${(row.similarity * 100).toFixed(1)}%`,
  },
  {
    key: "matched_by",
    header: "Method",
    align: "center",
    width: "100px",
    render: (row) => (
      <Badge variant={row.matched_by === "exact" ? "success" : "info"}>
        {row.matched_by ?? "-"}
      </Badge>
    ),
  },
];

export default function EntityResolutionPage() {
  const [nameInput, setNameInput] = useState("");
  const [resolveResult, setResolveResult] =
    useState<EntityResolveResponse | null>(null);
  const [aliasFilter, setAliasFilter] = useState("");

  const resolveEntity = useResolveEntity();
  const { data: aliases, isLoading: aliasesLoading } = useAliases({
    corp_code: aliasFilter || undefined,
  });
  const createAlias = useCreateAlias();
  const deleteAlias = useDeleteAlias();
  const [deletingId, setDeletingId] = useState<number | null>(null);

  const handleResolve = () => {
    const name = nameInput.trim();
    if (!name) return;
    resolveEntity.mutate(
      { name },
      {
        onSuccess: (res) => setResolveResult(res),
        onError: () => toast.error("Resolution failed"),
      },
    );
  };

  const handleCreateAlias = (aliasName: string, corpCode: string) => {
    createAlias.mutate(
      { alias_name: aliasName, corp_code: corpCode },
      {
        onSuccess: () => toast.success("Alias created"),
        onError: () => toast.error("Failed to create alias"),
      },
    );
  };

  const handleDeleteAlias = (aliasId: number) => {
    setDeletingId(aliasId);
    deleteAlias.mutate(aliasId, {
      onSuccess: () => { toast.success("Alias deleted"); setDeletingId(null); },
      onError: () => { toast.error("Failed to delete alias"); setDeletingId(null); },
    });
  };

  const aliasColumns: Column<AliasItem>[] = [
    {
      key: "alias_name",
      header: "Alias",
      render: (row) => (
        <span className="font-medium text-text-dark">{row.alias_name}</span>
      ),
    },
    {
      key: "corp_name",
      header: "Company",
      render: (row) => row.corp_name ?? "-",
    },
    {
      key: "corp_code",
      header: "Code",
      width: "120px",
      render: (row) => (
        <span className="font-mono text-xs">{row.corp_code ?? "-"}</span>
      ),
    },
    {
      key: "is_manual",
      header: "Type",
      align: "center",
      width: "80px",
      render: (row) => (
        <Badge variant={row.is_manual ? "info" : "neutral"}>
          {row.is_manual ? "Manual" : "Auto"}
        </Badge>
      ),
    },
    {
      key: "id",
      header: "",
      align: "center",
      width: "60px",
      render: (row) => (
        <Button
          variant="ghost"
          size="sm"
          aria-label={`Delete alias: ${row.alias_name}`}
          onClick={(e) => {
            e.stopPropagation();
            handleDeleteAlias(row.id);
          }}
          loading={deletingId === row.id}
          className="text-negative hover:text-red-700"
        >
          <Trash2 className="h-4 w-4" />
        </Button>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <PageHero title="Entity Resolution" subtitle="Resolve company names and manage aliases" compact />

      {/* Resolve Section */}
      <Card>
        <h2 className="text-base font-heading font-semibold text-text-dark mb-4">
          Resolve Company Name
        </h2>
        <div className="flex gap-3 items-end">
          <div className="flex-1 max-w-md">
            <Input
              label="Company Name"
              placeholder="e.g. 삼성전자, 삼전, Samsung"
              value={nameInput}
              onChange={(e) => setNameInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleResolve()}
            />
          </div>
          <Button
            variant="primary"
            icon={Search}
            onClick={handleResolve}
            loading={resolveEntity.isPending}
          >
            Resolve
          </Button>
        </div>

        {resolveResult && (
          <div className="mt-4 space-y-3">
            <div className="text-sm text-text-secondary">
              Query: <strong>{resolveResult.query}</strong> → Normalized:{" "}
              <strong>{resolveResult.normalized}</strong>
            </div>

            {resolveResult.match ? (
              <div className="flex items-center gap-3 p-3 bg-bg-light-green/30 rounded-lg border border-amic-200">
                <CheckCircle className="h-5 w-5 text-positive shrink-0" />
                <div>
                  <span className="font-medium text-text-dark">
                    {resolveResult.match.corp_name}
                  </span>
                  <span className="ml-2 font-mono text-xs text-text-secondary">
                    {resolveResult.match.corp_code}
                  </span>
                  <span className="ml-2 text-sm text-text-secondary">
                    ({(resolveResult.match.similarity * 100).toFixed(1)}% by{" "}
                    {resolveResult.match.matched_by})
                  </span>
                </div>
              </div>
            ) : (
              <div className="p-3 bg-amber-50 rounded-lg border border-amber-200 text-sm text-text-body">
                No exact match found.
              </div>
            )}

            {resolveResult.candidates.length > 0 && (
              <div>
                <h3 className="text-sm font-medium text-text-body mb-2">
                  Candidates
                </h3>
                <DataTable
                  columns={candidateColumns}
                  data={resolveResult.candidates}
                  keyField="corp_code"
                  compact
                  striped
                />
              </div>
            )}
          </div>
        )}
      </Card>

      {/* Alias Management Section */}
      <Card padding="none">
        <div className="px-5 py-3 border-b border-gray-border space-y-3">
          <h2 className="text-base font-heading font-semibold text-text-dark">
            Alias Management
          </h2>
          <AliasCreateForm
            onSubmit={handleCreateAlias}
            isPending={createAlias.isPending}
          />
          <div className="max-w-xs">
            <Input
              placeholder="Filter by corp code..."
              value={aliasFilter}
              onChange={(e) => setAliasFilter(e.target.value)}
            />
          </div>
        </div>

        {aliasesLoading ? (
          <Spinner />
        ) : !aliases?.items.length ? (
          <EmptyState
            icon={GitCompare}
            title="No aliases"
            description="No aliases registered yet."
          />
        ) : (
          <DataTable
            columns={aliasColumns}
            data={aliases.items}
            keyField="id"
            striped
          />
        )}
      </Card>
    </div>
  );
}

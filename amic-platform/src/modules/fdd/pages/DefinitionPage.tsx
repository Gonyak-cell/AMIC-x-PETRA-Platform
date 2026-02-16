import { useState } from "react";
import { useParams } from "react-router-dom";
import {
  FileText,
  Plus,
  Check,
  X,
  Lock,
  Hash,
} from "lucide-react";
import { toast } from "sonner";
import { useAuth } from "@/hooks/useAuth";
import {
  useDefinitions,
  useCreateDefinition,
  useApproveDefinition,
} from "@/modules/fdd/hooks/useDefinitions";
import type { DealDefinition, DefinitionData } from "@/modules/fdd/types/deal";
import {
  Card,
  Button,
  Badge,
  Input,
  Select,
  Spinner,
  EmptyState,
  PageHero,
} from "@/components/ui";
import type { SelectOption } from "@/components/ui";

const DEFAULT_DEFINITION: DefinitionData = {
  cash: { include: [], exclude: [] },
  debt: { include: [], exclude: [] },
  debt_like: [],
  cash_like: [],
  nwc: { include: [], exclude: [] },
  target_nwc: { method: "LTM_AVERAGE", value: null },
  lease_ifrs16: { include_in_debt: false },
};

const NWC_METHOD_OPTIONS: SelectOption[] = [
  { value: "LTM_AVERAGE", label: "LTM Average (12M)" },
  { value: "TTM", label: "TTM" },
  { value: "LAST_MONTH", label: "Last Month" },
  { value: "MAX", label: "Maximum" },
  { value: "MIN", label: "Minimum" },
  { value: "CUSTOM", label: "Custom" },
];

const STATUS_VARIANTS: Record<string, "success" | "warning" | "error"> = {
  DRAFT: "warning",
  APPROVED: "success",
  LOCKED: "error",
};

// ── Tag Input ────────────────────────────────────────────

function TagInput({
  label,
  values,
  onChange,
}: {
  label: string;
  values: string[];
  onChange: (v: string[]) => void;
}) {
  const [input, setInput] = useState("");

  const add = () => {
    const trimmed = input.trim();
    if (trimmed && !values.includes(trimmed)) {
      onChange([...values, trimmed]);
    }
    setInput("");
  };

  return (
    <div>
      <label className="block text-xs font-medium text-text-secondary mb-1.5">
        {label}
      </label>
      <div className="flex flex-wrap gap-1.5 mb-2 min-h-[28px]">
        {values.map((v) => (
          <span
            key={v}
            className="bg-amic-50 text-amic text-xs px-2 py-1 rounded-md flex items-center gap-1.5"
          >
            {v}
            <button
              type="button"
              onClick={() => onChange(values.filter((x) => x !== v))}
              className="text-amic hover:text-negative transition-colors"
              aria-label={`Remove ${v}`}
            >
              <X className="h-3 w-3" />
            </button>
          </span>
        ))}
        {values.length === 0 && (
          <span className="text-xs text-text-secondary italic">
            No items added
          </span>
        )}
      </div>
      <div className="flex gap-2">
        <Input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), add())}
          placeholder="Account code or name..."
          className="flex-1"
        />
        <Button variant="secondary" size="sm" onClick={add} icon={Plus}>
          Add
        </Button>
      </div>
    </div>
  );
}

// ── Definition Form ──────────────────────────────────────

function DefinitionForm({
  onSubmit,
  onCancel,
  isSubmitting,
}: {
  onSubmit: (data: DefinitionData) => void;
  onCancel: () => void;
  isSubmitting: boolean;
}) {
  const [form, setForm] = useState<DefinitionData>(DEFAULT_DEFINITION);

  const updateField = (
    category: "cash" | "debt" | "nwc",
    field: "include" | "exclude",
    values: string[]
  ) => {
    setForm({ ...form, [category]: { ...form[category], [field]: values } });
  };

  return (
    <Card title="New Definition Version" headerBar padding="lg">
      <form
        onSubmit={(e) => {
          e.preventDefault();
          onSubmit(form);
        }}
        className="space-y-6"
      >
        {/* Cash Definition */}
        <div className="border-t border-gray-border pt-4">
          <h4 className="text-sm font-heading font-semibold text-text-dark mb-4">
            Cash Definition
          </h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <TagInput
              label="Include Patterns"
              values={form.cash.include}
              onChange={(v) => updateField("cash", "include", v)}
            />
            <TagInput
              label="Exclude Patterns"
              values={form.cash.exclude}
              onChange={(v) => updateField("cash", "exclude", v)}
            />
          </div>
        </div>

        {/* Debt Definition */}
        <div className="border-t border-gray-border pt-4">
          <h4 className="text-sm font-heading font-semibold text-text-dark mb-4">
            Debt Definition
          </h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <TagInput
              label="Include Patterns"
              values={form.debt.include}
              onChange={(v) => updateField("debt", "include", v)}
            />
            <TagInput
              label="Exclude Patterns"
              values={form.debt.exclude}
              onChange={(v) => updateField("debt", "exclude", v)}
            />
          </div>
        </div>

        {/* NWC Definition */}
        <div className="border-t border-gray-border pt-4">
          <h4 className="text-sm font-heading font-semibold text-text-dark mb-4">
            NWC Definition
          </h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <TagInput
              label="Include Patterns"
              values={form.nwc.include}
              onChange={(v) => updateField("nwc", "include", v)}
            />
            <TagInput
              label="Exclude Patterns"
              values={form.nwc.exclude}
              onChange={(v) => updateField("nwc", "exclude", v)}
            />
          </div>
        </div>

        {/* Target NWC */}
        <div className="border-t border-gray-border pt-4">
          <h4 className="text-sm font-heading font-semibold text-text-dark mb-4">
            Target NWC (Peg)
          </h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Select
              label="Calculation Method"
              value={form.target_nwc.method}
              onChange={(e) =>
                setForm({
                  ...form,
                  target_nwc: { ...form.target_nwc, method: e.target.value },
                })
              }
              options={NWC_METHOD_OPTIONS}
            />
            <Input
              label="Custom Value (optional)"
              type="number"
              value={form.target_nwc.value ?? ""}
              onChange={(e) =>
                setForm({
                  ...form,
                  target_nwc: {
                    ...form.target_nwc,
                    value: e.target.value ? Number(e.target.value) : null,
                  },
                })
              }
              placeholder="Enter custom NWC value"
            />
          </div>
        </div>

        {/* IFRS 16 */}
        <div className="border-t border-gray-border pt-4">
          <label className="flex items-center gap-3 text-sm text-text-body cursor-pointer">
            <input
              type="checkbox"
              checked={form.lease_ifrs16.include_in_debt}
              onChange={(e) =>
                setForm({
                  ...form,
                  lease_ifrs16: { include_in_debt: e.target.checked },
                })
              }
              className="rounded border-gray-border text-amic focus:ring-amic h-4 w-4"
            />
            Include IFRS 16 lease liabilities in Net Debt calculation
          </label>
        </div>

        {/* Actions */}
        <div className="flex justify-end gap-3 pt-4 border-t border-gray-border">
          <Button variant="ghost" onClick={onCancel}>
            Cancel
          </Button>
          <Button
            variant="accent"
            type="submit"
            loading={isSubmitting}
            icon={Plus}
          >
            Create Definition
          </Button>
        </div>
      </form>
    </Card>
  );
}

// ── Definition Card ──────────────────────────────────────

function DefinitionCard({
  definition,
  onApprove,
  isApproving,
}: {
  definition: DealDefinition;
  onApprove: (version: number) => void;
  isApproving: boolean;
}) {
  return (
    <div className="bg-white border border-gray-border rounded-lg p-4 shadow-card">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5">
            <FileText className="h-4 w-4 text-amic" />
            <span className="font-heading font-semibold text-text-dark">
              v{definition.version}
            </span>
          </div>
          <Badge variant={STATUS_VARIANTS[definition.status]}>
            {definition.status === "LOCKED" && <Lock className="h-3 w-3 mr-1" />}
            {definition.status}
          </Badge>
          <div className="flex items-center gap-1 text-xs text-text-secondary font-mono">
            <Hash className="h-3 w-3" />
            {definition.hash.slice(0, 12)}...
          </div>
        </div>
        {definition.status === "DRAFT" && (
          <Button
            variant="accent"
            size="sm"
            icon={Check}
            onClick={() => onApprove(definition.version)}
            loading={isApproving}
          >
            Approve
          </Button>
        )}
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs">
        <div>
          <span className="text-text-secondary">NWC Method:</span>
          <span className="ml-1 font-medium text-text-body">
            {definition.definition_data.target_nwc?.method || "N/A"}
          </span>
        </div>
        <div>
          <span className="text-text-secondary">IFRS 16 in Debt:</span>
          <span className="ml-1 font-medium text-text-body">
            {definition.definition_data.lease_ifrs16?.include_in_debt ? "Yes" : "No"}
          </span>
        </div>
        <div>
          <span className="text-text-secondary">Created:</span>
          <span className="ml-1 font-medium text-text-body">
            {new Date(definition.created_at).toLocaleDateString("ko-KR")}
          </span>
        </div>
        {definition.approved_by && (
          <div>
            <span className="text-text-secondary">Approved by:</span>
            <span className="ml-1 font-medium text-text-body">
              {definition.approved_by}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Main Page ────────────────────────────────────────────

export default function DefinitionPage() {
  const { dealId } = useParams<{ dealId: string }>();
  const { user } = useAuth();
  const [showForm, setShowForm] = useState(false);

  const { data: definitions, isLoading, isError } = useDefinitions(dealId!);
  const createDef = useCreateDefinition(dealId!);
  const approveDef = useApproveDefinition(dealId!);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Spinner size="lg" />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="bg-red-50 border border-negative/20 rounded-lg p-4 text-sm text-negative">
        Failed to load definitions.
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <PageHero
        title="Deal Definitions"
        subtitle="Configure FDD analysis parameters"
        compact
        actions={
          !showForm ? (
            <Button
              variant="accent"
              icon={Plus}
              onClick={() => setShowForm(true)}
            >
              New Version
            </Button>
          ) : undefined
        }
      />

      {/* Create Form */}
      {showForm && (
        <DefinitionForm
          onSubmit={async (data) => {
            try {
              await createDef.mutateAsync(data);
              setShowForm(false);
              toast.success("Definition created successfully");
            } catch {
              toast.error("Failed to create definition");
            }
          }}
          onCancel={() => setShowForm(false)}
          isSubmitting={createDef.isPending}
        />
      )}

      {/* Definition List */}
      {!definitions?.length ? (
        <Card>
          <EmptyState
            icon={FileText}
            title="No Definitions"
            description="Create the first definition version to configure FDD analysis parameters."
            actionLabel="Create Definition"
            onAction={() => setShowForm(true)}
          />
        </Card>
      ) : (
        <div className="space-y-3">
          <h3 className="text-sm font-heading font-semibold text-text-dark">
            Definition Versions ({definitions.length})
          </h3>
          {definitions.map((def) => (
            <DefinitionCard
              key={def.id}
              definition={def}
              onApprove={async (version) => {
                try {
                  await approveDef.mutateAsync({
                    version,
                    approved_by: user?.email ?? "unknown",
                  });
                  toast.success("Definition approved");
                } catch {
                  toast.error("Failed to approve definition");
                }
              }}
              isApproving={approveDef.isPending}
            />
          ))}
        </div>
      )}
    </div>
  );
}

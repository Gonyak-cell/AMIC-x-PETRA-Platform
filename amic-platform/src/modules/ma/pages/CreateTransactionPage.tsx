import { useEffect, useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { ArrowLeft, ChevronDown } from "lucide-react";
import { toast } from "sonner";
import { useAuth } from "@/hooks/useAuth";
import { Button, Card, Input, Select, PageHero } from "@/components/ui";
import heroImg from "@/assets/images/heroes/hero-arch-blue-wave.jpg";
import { useCreateTransaction } from "@/modules/ma/hooks/useTransactions";
import {
  buildProjectName,
  getProjectSuffix,
  normalizeProjectSuffix,
  previewProjectCode,
} from "@/modules/ma/utils/projectName";
import { getTransactionTextError } from "@/modules/ma/utils/transactionText";
import type {
  DealStructure,
  DealType,
  InvestmentType,
  TransactionCreate,
} from "@/modules/ma/types/transaction";
import {
  CURRENCY_OPTIONS,
  DEAL_STRUCTURE_OPTIONS,
  DEAL_TYPE_OPTIONS,
  INVESTMENT_TYPE_OPTIONS,
} from "@/modules/ma/constants";

const INITIAL: TransactionCreate = {
  name: "Project ",
  deal_type: "SE",
  side: "SELL",
  target_company_name: "",
  client_name: "",
  lead_advisor_email: "",
};

export default function CreateTransactionPage() {
  const navigate = useNavigate();
  const { isClient, user } = useAuth();
  const createTxn = useCreateTransaction();
  const [form, setForm] = useState<TransactionCreate>(INITIAL);
  const [showOptional, setShowOptional] = useState(false);
  const [projectNameInput, setProjectNameInput] = useState(() =>
    getProjectSuffix(INITIAL.name),
  );
  const [isProjectNameComposing, setIsProjectNameComposing] = useState(false);

  useEffect(() => {
    if (!user?.email) return;
    setForm((prev) =>
      prev.lead_advisor_email.trim()
        ? prev
        : { ...prev, lead_advisor_email: user.email },
    );
  }, [user?.email]);

  if (isClient) return <Navigate to="/ma/transactions" replace />;

  const set = <K extends keyof TransactionCreate>(
    key: K,
    val: TransactionCreate[K],
  ) => setForm((prev) => ({ ...prev, [key]: val }));

  const syncProjectName = (raw: string) => {
    const normalized = normalizeProjectSuffix(raw);
    setProjectNameInput(normalized);
    set("name", buildProjectName(normalized));
  };

  const handleProjectNameChange = (value: string) => {
    if (isProjectNameComposing) {
      setProjectNameInput(value);
      return;
    }
    syncProjectName(value);
  };

  const normalizedProjectName = normalizeProjectSuffix(projectNameInput);
  const email = form.lead_advisor_email.trim();
  const targetCompanyError = getTransactionTextError(form.target_company_name);
  const clientNameError = getTransactionTextError(form.client_name);
  const transactionTextError = targetCompanyError ?? clientNameError;
  const canSubmit =
    normalizedProjectName.length > 0 &&
    Boolean(form.deal_type) &&
    form.target_company_name.trim().length > 0 &&
    form.client_name.trim().length > 0 &&
    !transactionTextError &&
    /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (transactionTextError) {
      toast.error(transactionTextError);
      return;
    }
    if (!canSubmit) return;

    createTxn.mutate(
      {
        ...form,
        name: buildProjectName(projectNameInput),
        target_company_name: form.target_company_name.trim(),
        client_name: form.client_name.trim(),
        lead_advisor_email: email,
        target_corp_code: form.target_corp_code?.trim() || undefined,
        industry: form.industry?.trim() || undefined,
        deal_captain_email: form.deal_captain_email?.trim() || undefined,
        estimated_deal_value: form.estimated_deal_value?.trim() || undefined,
      },
      {
        onSuccess: (txn) => navigate(`/ma/transactions/${txn.id}`),
      },
    );
  };

  const preview = previewProjectCode(form.deal_type, projectNameInput);

  return (
    <div className="space-y-6">
      <PageHero
        title="New Transaction"
        subtitle="Create a new M&A transaction"
        backgroundImage={heroImg}
        backgroundOpacity={0.18}
        compact
      />

      <div className="max-w-2xl mx-auto">
        <Button
          variant="ghost"
          icon={ArrowLeft}
          onClick={() => navigate("/ma/transactions")}
          className="mb-4"
        >
          Back to list
        </Button>

        <Card title="Basic Information" headerBar>
          <form
            id="create-txn"
            onSubmit={handleSubmit}
            className="space-y-5 p-1"
          >
            <fieldset className="space-y-4">
              <legend className="text-xs font-semibold uppercase tracking-wider text-text-muted mb-1">
                Required
              </legend>

              <Select
                label="Deal Type"
                options={DEAL_TYPE_OPTIONS}
                value={form.deal_type}
                onChange={(e) => set("deal_type", e.target.value as DealType)}
              />

              <div>
                <label className="block text-sm font-medium text-text-secondary mb-1.5">
                  Project Name<span className="text-destructive">*</span>
                </label>
                <div className="flex">
                  <span className="inline-flex items-center px-3 rounded-l-md border border-r-0 border-border bg-surface-subtle text-sm font-medium text-text-muted select-none">
                    Project
                  </span>
                  <input
                    type="text"
                    required
                    className="flex-1 min-w-0 px-3 py-2 rounded-r-md border border-border bg-surface text-sm focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent"
                    placeholder="Edward"
                    value={projectNameInput}
                    onChange={(e) => handleProjectNameChange(e.target.value)}
                    onBlur={() => syncProjectName(projectNameInput)}
                    onCompositionStart={() => setIsProjectNameComposing(true)}
                    onCompositionEnd={(e) => {
                      setIsProjectNameComposing(false);
                      syncProjectName(e.currentTarget.value);
                    }}
                  />
                </div>
                {preview && (
                  <p className="mt-1.5 text-xs text-text-muted">
                    Expected code:{" "}
                    <code className="font-mono font-semibold text-accent">
                      {preview}
                    </code>
                  </p>
                )}
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <Input
                  label="Target Company"
                  required
                  error={targetCompanyError}
                  value={form.target_company_name}
                  onChange={(e) => set("target_company_name", e.target.value)}
                  placeholder="Target company name"
                />
                <Input
                  label="Client"
                  required
                  error={clientNameError}
                  value={form.client_name}
                  onChange={(e) => set("client_name", e.target.value)}
                  placeholder="Client name"
                />
              </div>

              <Input
                label="Lead Advisor Email"
                type="email"
                required
                value={form.lead_advisor_email}
                onChange={(e) => set("lead_advisor_email", e.target.value)}
                placeholder="advisor@company.com"
              />
            </fieldset>

            <button
              type="button"
              aria-expanded={showOptional}
              onClick={() => setShowOptional(!showOptional)}
              className="flex items-center gap-1.5 text-sm font-medium text-accent hover:text-accent/80 transition-colors"
            >
              <ChevronDown
                size={16}
                className={`transition-transform ${showOptional ? "rotate-180" : ""}`}
              />
              {showOptional ? "Hide optional fields" : "Add more details"}
            </button>

            {showOptional && (
              <fieldset className="space-y-4 animate-fade-in">
                <legend className="text-xs font-semibold uppercase tracking-wider text-text-muted mb-1">
                  Optional
                </legend>

                <Input
                  label="DART Corp Code"
                  value={form.target_corp_code ?? ""}
                  onChange={(e) =>
                    set("target_corp_code", e.target.value || undefined)
                  }
                  placeholder="8-digit corp code"
                />

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <Select
                    label="Deal Structure"
                    options={DEAL_STRUCTURE_OPTIONS}
                    value={form.deal_structure ?? ""}
                    onChange={(e) =>
                      set(
                        "deal_structure",
                        (e.target.value || undefined) as DealStructure | undefined,
                      )
                    }
                  />
                  <Select
                    label="Investment Type"
                    options={INVESTMENT_TYPE_OPTIONS}
                    value={form.investment_type ?? ""}
                    onChange={(e) =>
                      set(
                        "investment_type",
                        (e.target.value || undefined) as InvestmentType | undefined,
                      )
                    }
                  />
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <Input
                    label="Estimated Deal Value"
                    type="number"
                    value={
                      form.estimated_deal_value != null
                        ? String(form.estimated_deal_value)
                        : ""
                    }
                    onChange={(e) =>
                      set("estimated_deal_value", e.target.value || undefined)
                    }
                    placeholder="0"
                  />
                  <Select
                    label="Currency"
                    options={CURRENCY_OPTIONS}
                    value={form.currency ?? "KRW"}
                    onChange={(e) =>
                      set(
                        "currency",
                        e.target.value as TransactionCreate["currency"],
                      )
                    }
                  />
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <Input
                    label="Industry"
                    value={form.industry ?? ""}
                    onChange={(e) => set("industry", e.target.value || undefined)}
                    placeholder="Industry"
                  />
                  <Input
                    label="Target Close Date"
                    type="date"
                    value={form.target_close_date ?? ""}
                    onChange={(e) =>
                      set("target_close_date", e.target.value || undefined)
                    }
                  />
                </div>

                <Input
                  label="Deal Captain Email"
                  type="email"
                  value={form.deal_captain_email ?? ""}
                  onChange={(e) =>
                    set("deal_captain_email", e.target.value || undefined)
                  }
                  placeholder="captain@company.com"
                />
              </fieldset>
            )}

            <div className="flex justify-end gap-3 pt-4 border-t">
              <Button
                variant="ghost"
                type="button"
                onClick={() => navigate("/ma/transactions")}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={!canSubmit}
                loading={createTxn.isPending}
              >
                Create transaction
              </Button>
            </div>
          </form>
        </Card>
      </div>
    </div>
  );
}

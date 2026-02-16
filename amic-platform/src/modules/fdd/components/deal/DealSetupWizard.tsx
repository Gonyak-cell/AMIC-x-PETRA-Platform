import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { Button, Card, Input, Select } from "@/components/ui";
import { useCreateDeal } from "@/modules/fdd/hooks/useDeals";
import ScopeSelector from "./ScopeSelector";
import type { DealType, IndustryType } from "@/modules/fdd/types/deal";
import { FDD_INDUSTRY_OPTIONS } from "@/types/industry";
import { DEAL_TYPE_OPTIONS, CURRENCY_OPTIONS } from "@/modules/fdd/constants";

interface FormData {
  name: string;
  deal_type: DealType;
  base_currency: string;
  reference_date: string;
  period_start: string;
  period_end: string;
  client_name: string;
  client_contact_name: string;
  client_contact_email: string;
  target_company_name: string;
  industry: IndustryType;
  scope_qoe: boolean;
  scope_nwc: boolean;
  scope_debt: boolean;
}

const INITIAL_FORM: FormData = {
  name: "",
  deal_type: "COMPLETION_ACCOUNTS",
  base_currency: "KRW",
  reference_date: "",
  period_start: "",
  period_end: "",
  client_name: "",
  client_contact_name: "",
  client_contact_email: "",
  target_company_name: "",
  industry: "general",
  scope_qoe: true,
  scope_nwc: true,
  scope_debt: true,
};

const STEP_TITLES = [
  "Basic Info",
  "Client & Target",
  "Team",
  "FDD Scope",
];

export default function DealSetupWizard() {
  const [step, setStep] = useState(0);
  const [formData, setFormData] = useState<FormData>(INITIAL_FORM);
  const createDeal = useCreateDeal();
  const navigate = useNavigate();

  const updateField = <K extends keyof FormData>(field: K, value: FormData[K]) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  const validateStep = (s: number): boolean => {
    if (s === 0) {
      if (!formData.name || !formData.reference_date || !formData.period_start || !formData.period_end) {
        toast.error("Please fill in all required fields");
        return false;
      }
    }
    return true;
  };

  const handleNext = () => {
    if (!validateStep(step)) return;
    setStep((s) => Math.min(s + 1, 3));
  };
  const handleBack = () => setStep((s) => Math.max(s - 1, 0));

  const handleSubmit = async () => {
    // Client-side date validation
    if (formData.period_start && formData.period_end && formData.period_end < formData.period_start) {
      toast.error("Period End must be on or after Period Start");
      return;
    }
    if (formData.reference_date && formData.period_end && formData.reference_date < formData.period_end) {
      toast.error("Reference Date must be on or after Period End");
      return;
    }

    try {
      const result = await createDeal.mutateAsync({
        name: formData.name,
        deal_type: formData.deal_type,
        base_currency: formData.base_currency,
        reference_date: formData.reference_date,
        period_start: formData.period_start,
        period_end: formData.period_end,
        client_name: formData.client_name || undefined,
        client_contact_name: formData.client_contact_name || undefined,
        client_contact_email: formData.client_contact_email || undefined,
        target_company_name: formData.target_company_name || undefined,
        industry: formData.industry,
        scope_qoe: formData.scope_qoe,
        scope_nwc: formData.scope_nwc,
        scope_debt: formData.scope_debt,
      });
      toast.success("Deal created successfully");
      navigate(`/deals/${result.id}`);
    } catch {
      toast.error("Failed to create deal");
    }
  };

  return (
    <Card>
      {/* Step indicator */}
      <div className="flex items-center gap-2 mb-6">
        {STEP_TITLES.map((title, i) => (
          <div key={title} className="flex items-center gap-2">
            <div
              className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
                i === step
                  ? "bg-amic text-white"
                  : i < step
                    ? "bg-positive text-white"
                    : "bg-gray-100 text-text-secondary"
              }`}
            >
              {i + 1}
            </div>
            <span
              className={`text-sm hidden sm:inline ${
                i === step ? "text-text-dark font-medium" : "text-text-secondary"
              }`}
            >
              {title}
            </span>
            {i < STEP_TITLES.length - 1 && (
              <div className="w-8 h-px bg-gray-200 hidden sm:block" />
            )}
          </div>
        ))}
      </div>

      {/* Step 1: Basic Info */}
      {step === 0 && (
        <div className="space-y-4">
          <Input
            label="Deal Name"
            value={formData.name}
            onChange={(e) => updateField("name", e.target.value)}
            placeholder="Enter deal name"
            required
          />
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <Select
              label="Deal Type"
              options={DEAL_TYPE_OPTIONS}
              value={formData.deal_type}
              onChange={(e) => updateField("deal_type", e.target.value as DealType)}
            />
            <Select
              label="Industry"
              options={FDD_INDUSTRY_OPTIONS}
              value={formData.industry}
              onChange={(e) => updateField("industry", e.target.value as IndustryType)}
            />
            <Select
              label="Base Currency"
              options={CURRENCY_OPTIONS}
              value={formData.base_currency}
              onChange={(e) => updateField("base_currency", e.target.value)}
            />
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <Input
              label="Reference Date"
              type="date"
              value={formData.reference_date}
              onChange={(e) => updateField("reference_date", e.target.value)}
              required
            />
            <Input
              label="Period Start"
              type="date"
              value={formData.period_start}
              onChange={(e) => updateField("period_start", e.target.value)}
              required
            />
            <Input
              label="Period End"
              type="date"
              value={formData.period_end}
              onChange={(e) => updateField("period_end", e.target.value)}
              required
            />
          </div>
        </div>
      )}

      {/* Step 2: Client & Target */}
      {step === 1 && (
        <div className="space-y-4">
          <Input
            label="Client Name"
            value={formData.client_name}
            onChange={(e) => updateField("client_name", e.target.value)}
            placeholder="Enter client company name"
          />
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Input
              label="Client Contact Name"
              value={formData.client_contact_name}
              onChange={(e) => updateField("client_contact_name", e.target.value)}
              placeholder="Contact person name"
            />
            <Input
              label="Client Contact Email"
              type="email"
              value={formData.client_contact_email}
              onChange={(e) => updateField("client_contact_email", e.target.value)}
              placeholder="contact@example.com"
            />
          </div>
          <Input
            label="Target Company Name"
            value={formData.target_company_name}
            onChange={(e) => updateField("target_company_name", e.target.value)}
            placeholder="Enter target company name"
          />
        </div>
      )}

      {/* Step 3: Team */}
      {step === 2 && (
        <div className="py-8 text-center">
          <p className="text-text-secondary text-sm">
            Team selection will be added in a future update.
          </p>
          <p className="text-text-secondary text-xs mt-2">
            Partner and Manager assignment will be available once team management is implemented.
          </p>
        </div>
      )}

      {/* Step 4: FDD Scope */}
      {step === 3 && (
        <div className="space-y-4">
          <h4 className="text-sm font-heading font-semibold text-text-dark">
            Select FDD Scope
          </h4>
          <ScopeSelector
            scopeQoe={formData.scope_qoe}
            scopeNwc={formData.scope_nwc}
            scopeDebt={formData.scope_debt}
            onScopeChange={(field, value) => updateField(field, value)}
          />
        </div>
      )}

      {/* Navigation buttons */}
      <div className="flex justify-between mt-8 pt-4 border-t border-gray-border">
        <Button
          variant="ghost"
          onClick={handleBack}
          disabled={step === 0}
        >
          Back
        </Button>
        {step < 3 ? (
          <Button variant="primary" onClick={handleNext}>
            Next
          </Button>
        ) : (
          <Button
            variant="accent"
            onClick={handleSubmit}
            loading={createDeal.isPending}
            disabled={!formData.name || !formData.reference_date || !formData.period_start || !formData.period_end}
          >
            Create Deal
          </Button>
        )}
      </div>
    </Card>
  );
}

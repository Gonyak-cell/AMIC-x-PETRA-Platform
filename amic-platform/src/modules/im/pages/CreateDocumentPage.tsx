import { useState, useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { toast } from "sonner";
import {
  Building2,
  Loader2,
  CheckCircle,
  AlertCircle,
} from "lucide-react";
import { Button, Card, Input, Select, Spinner } from "@/components/ui";
import { useCreateDocument } from "@/modules/im/hooks/useDocuments";
import { useCompany, useFetchCompany } from "@/modules/im/hooks/useCompanies";
import type { IMStyle } from "@/modules/im/types/document";

const STYLE_OPTIONS = [
  { value: "TITAN", label: "Titan - Concise Summary" },
  { value: "COVENANT", label: "Covenant - Financial Focus" },
  { value: "FULL", label: "Full - Comprehensive" },
  { value: "CUSTOM", label: "Custom - Select Sections" },
];

const INDUSTRY_OPTIONS = [
  { value: "general", label: "General" },
  { value: "finance", label: "Finance" },
  { value: "technology", label: "Technology" },
  { value: "manufacturing", label: "Manufacturing" },
  { value: "healthcare", label: "Healthcare" },
  { value: "real_estate", label: "Real Estate" },
  { value: "energy", label: "Energy" },
  { value: "consumer", label: "Consumer" },
];

const AVAILABLE_SECTIONS = [
  "Cover",
  "Executive Summary",
  "Company Overview",
  "Industry Analysis",
  "Financial Analysis",
  "Management Team",
  "Market Position",
  "Growth Strategy",
  "Risk Factors",
  "Debt Structure",
  "Covenant Compliance",
  "Projections",
  "Appendix",
];

const STEP_TITLES = ["Company", "IM Settings", "Confirm"];

interface FormData {
  corp_code: string;
  project_name: string;
  im_style: IMStyle;
  industry: string;
  sections: string[];
  pdf_password: string;
}

const INITIAL_FORM: FormData = {
  corp_code: "",
  project_name: "",
  im_style: "FULL",
  industry: "general",
  sections: [],
  pdf_password: "",
};

export default function CreateDocumentPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const initialStyle = (searchParams.get("style") as IMStyle) || "FULL";
  const urlCorpCode = searchParams.get("corpCode") || "";

  const [step, setStep] = useState(0);
  const [formData, setFormData] = useState<FormData>({
    ...INITIAL_FORM,
    im_style: initialStyle,
  });
  const [corpCodeInput, setCorpCodeInput] = useState(urlCorpCode);

  const createDocument = useCreateDocument();
  const fetchCompany = useFetchCompany();
  const { data: company, isLoading: companyLoading } = useCompany(formData.corp_code);

  // Auto-fetch company when corpCode is provided via URL (cross-module navigation)
  useEffect(() => {
    if (urlCorpCode && urlCorpCode.length === 8) {
      fetchCompany
        .mutateAsync(urlCorpCode)
        .then(() => {
          setFormData((prev) => ({ ...prev, corp_code: urlCorpCode }));
          toast.success("Company data fetch initiated");
        })
        .catch(() => {
          toast.error("Failed to fetch company data");
        });
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const updateField = <K extends keyof FormData>(field: K, value: FormData[K]) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  const handleFetchCompany = async () => {
    if (!corpCodeInput || corpCodeInput.length !== 8) {
      toast.error("Please enter a valid 8-digit corp code");
      return;
    }
    try {
      await fetchCompany.mutateAsync(corpCodeInput);
      setFormData((prev) => ({ ...prev, corp_code: corpCodeInput }));
      toast.success("Company data fetch initiated");
    } catch {
      toast.error("Failed to fetch company data");
    }
  };

  const handleNext = () => setStep((s) => Math.min(s + 1, 2));
  const handleBack = () => setStep((s) => Math.max(s - 1, 0));

  const handleSubmit = async () => {
    try {
      const result = await createDocument.mutateAsync({
        corp_code: formData.corp_code,
        project_name: formData.project_name || undefined,
        im_style: formData.im_style,
        sections: formData.im_style === "CUSTOM" ? formData.sections : undefined,
        industry: formData.industry || undefined,
        pdf_password: formData.pdf_password || undefined,
      });
      toast.success("IM generation started");
      navigate(`/im/documents/${result.id}`);
    } catch {
      toast.error("Failed to create IM document");
    }
  };

  // Auto-populate industry from company data
  useEffect(() => {
    if (company?.industry && formData.industry === "general") {
      const match = INDUSTRY_OPTIONS.find(
        (opt) => opt.value === company.industry || opt.label === company.industry,
      );
      if (match) {
        updateField("industry", match.value);
      }
    }
  }, [company?.industry]); // eslint-disable-line react-hooks/exhaustive-deps

  const canProceedStep0 = formData.corp_code && company?.fetch_status === "COMPLETED";
  const canProceedStep1 =
    formData.im_style &&
    (formData.im_style !== "CUSTOM" || formData.sections.length > 0);

  const toggleSection = (section: string) => {
    setFormData((prev) => ({
      ...prev,
      sections: prev.sections.includes(section)
        ? prev.sections.filter((s) => s !== section)
        : [...prev.sections, section],
    }));
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-heading font-bold text-text-dark">
          Create New IM
        </h1>
        <p className="mt-1 text-sm text-text-secondary">
          Generate an Investment Memorandum in 3 simple steps.
        </p>
      </div>

      <Card>
        {/* Step indicator */}
        <div className="flex items-center gap-2 mb-6" role="list" aria-label="Creation steps">
          {STEP_TITLES.map((title, i) => (
            <div
              key={title}
              className="flex items-center gap-2"
              role="listitem"
              aria-current={i === step ? "step" : undefined}
            >
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
                  i === step
                    ? "bg-amic text-white"
                    : i < step
                      ? "bg-positive text-white"
                      : "bg-gray-100 text-text-secondary"
                }`}
                aria-label={`Step ${i + 1}: ${title}${i < step ? " (completed)" : i === step ? " (current)" : ""}`}
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
                <div className="w-8 h-px bg-gray-200 hidden sm:block" aria-hidden="true" />
              )}
            </div>
          ))}
        </div>

        {/* Step 1: Company Selection */}
        {step === 0 && (
          <div className="space-y-4">
            <div className="flex gap-3 items-end">
              <div className="flex-1">
                <Input
                  label="Corp Code (8-digit)"
                  value={corpCodeInput}
                  onChange={(e) => setCorpCodeInput(e.target.value)}
                  placeholder="e.g. 00126380"
                  maxLength={8}
                />
              </div>
              <Button
                variant="primary"
                onClick={handleFetchCompany}
                loading={fetchCompany.isPending}
                disabled={corpCodeInput.length !== 8}
              >
                Fetch
              </Button>
            </div>

            {/* Company preview */}
            {formData.corp_code && (
              <div className="border border-gray-border rounded-lg p-4">
                {companyLoading ? (
                  <div className="flex items-center justify-center py-4">
                    <Spinner size="sm" />
                    <span className="ml-2 text-sm text-text-secondary">
                      Loading company data...
                    </span>
                  </div>
                ) : company ? (
                  <div className="space-y-3">
                    <div className="flex items-center gap-3">
                      <Building2 className="h-5 w-5 text-amic flex-shrink-0" />
                      <div>
                        <h3 className="font-medium text-text-dark">
                          {company.corp_name}
                        </h3>
                        {company.corp_name_en && (
                          <p className="text-xs text-text-secondary">
                            {company.corp_name_en}
                          </p>
                        )}
                      </div>
                    </div>
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
                      <div>
                        <span className="text-text-secondary">Code</span>
                        <p className="font-mono text-text-dark">{company.corp_code}</p>
                      </div>
                      {company.stock_code && (
                        <div>
                          <span className="text-text-secondary">Stock</span>
                          <p className="font-mono text-text-dark">{company.stock_code}</p>
                        </div>
                      )}
                      {company.industry && (
                        <div>
                          <span className="text-text-secondary">Industry</span>
                          <p className="text-text-dark">{company.industry}</p>
                        </div>
                      )}
                      <div>
                        <span className="text-text-secondary">Status</span>
                        <p className="flex items-center gap-1">
                          {company.fetch_status === "COMPLETED" ? (
                            <>
                              <CheckCircle className="h-3.5 w-3.5 text-positive" />
                              <span className="text-positive">Ready</span>
                            </>
                          ) : company.fetch_status === "FAILED" ? (
                            <>
                              <AlertCircle className="h-3.5 w-3.5 text-negative" />
                              <span className="text-negative">Failed</span>
                            </>
                          ) : (
                            <>
                              <Loader2 className="h-3.5 w-3.5 text-amic animate-spin" />
                              <span className="text-amic">Fetching...</span>
                            </>
                          )}
                        </p>
                      </div>
                    </div>
                  </div>
                ) : (
                  <p className="text-sm text-text-secondary text-center py-4">
                    Company not found
                  </p>
                )}
              </div>
            )}
          </div>
        )}

        {/* Step 2: IM Settings */}
        {step === 1 && (
          <div className="space-y-4">
            <Input
              label="Project Name (Optional)"
              value={formData.project_name}
              onChange={(e) => updateField("project_name", e.target.value)}
              placeholder="e.g. Q4 2025 IM Report"
            />
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Select
                label="IM Style"
                options={STYLE_OPTIONS}
                value={formData.im_style}
                onChange={(e) => updateField("im_style", e.target.value as IMStyle)}
              />
              <Select
                label="Industry"
                options={INDUSTRY_OPTIONS}
                value={formData.industry}
                onChange={(e) => updateField("industry", e.target.value)}
              />
            </div>

            {/* Custom section selector */}
            {formData.im_style === "CUSTOM" && (
              <div>
                <label className="block text-sm font-medium text-text-dark mb-2">
                  Select Sections
                </label>
                <div
                  className="grid grid-cols-2 sm:grid-cols-3 gap-2"
                  role="group"
                  aria-label="IM document sections"
                >
                  {AVAILABLE_SECTIONS.map((section) => (
                    <button
                      key={section}
                      type="button"
                      onClick={() => toggleSection(section)}
                      aria-pressed={formData.sections.includes(section)}
                      className={`px-3 py-2 text-sm rounded-lg border transition-colors text-left ${
                        formData.sections.includes(section)
                          ? "border-amic bg-amic/10 text-amic font-medium"
                          : "border-gray-border bg-white text-text-secondary hover:border-amic/50"
                      }`}
                    >
                      {section}
                    </button>
                  ))}
                </div>
                {formData.sections.length > 0 && (
                  <p className="mt-2 text-xs text-text-secondary">
                    {formData.sections.length} section(s) selected
                  </p>
                )}
              </div>
            )}
          </div>
        )}

        {/* Step 3: Confirmation */}
        {step === 2 && (
          <div className="space-y-4">
            <h4 className="text-sm font-heading font-semibold text-text-dark">
              Review & Confirm
            </h4>
            <div className="bg-bg-cool rounded-lg p-4 space-y-3 text-sm">
              <div className="flex justify-between">
                <span className="text-text-secondary">Company</span>
                <span className="text-text-dark font-medium">
                  {company?.corp_name ?? formData.corp_code}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-text-secondary">Corp Code</span>
                <span className="font-mono text-text-dark">{formData.corp_code}</span>
              </div>
              {formData.project_name && (
                <div className="flex justify-between">
                  <span className="text-text-secondary">Project Name</span>
                  <span className="text-text-dark">{formData.project_name}</span>
                </div>
              )}
              <div className="flex justify-between">
                <span className="text-text-secondary">IM Style</span>
                <span className="text-text-dark">{formData.im_style}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-text-secondary">Industry</span>
                <span className="text-text-dark">{formData.industry}</span>
              </div>
              {formData.im_style === "CUSTOM" && (
                <div>
                  <span className="text-text-secondary">Sections</span>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {formData.sections.map((s) => (
                      <span
                        key={s}
                        className="px-2 py-0.5 text-xs rounded bg-white text-text-dark"
                      >
                        {s}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>

            <Input
              label="PDF Password (Optional)"
              type="password"
              value={formData.pdf_password}
              onChange={(e) => updateField("pdf_password", e.target.value)}
              placeholder="Min 4 characters"
              error={
                formData.pdf_password.length > 0 && formData.pdf_password.length < 4
                  ? "Password must be at least 4 characters"
                  : undefined
              }
            />
          </div>
        )}

        {/* Navigation */}
        <div className="flex justify-between mt-8 pt-4 border-t border-gray-border">
          <Button
            variant="ghost"
            onClick={step === 0 ? () => navigate("/im") : handleBack}
          >
            {step === 0 ? "Cancel" : "Back"}
          </Button>
          {step < 2 ? (
            <Button
              variant="primary"
              onClick={handleNext}
              disabled={step === 0 ? !canProceedStep0 : !canProceedStep1}
            >
              Next
            </Button>
          ) : (
            <Button
              variant="accent"
              onClick={handleSubmit}
              loading={createDocument.isPending}
              disabled={
                !formData.corp_code ||
                (formData.pdf_password.length > 0 && formData.pdf_password.length < 4)
              }
            >
              Generate IM
            </Button>
          )}
        </div>
      </Card>
    </div>
  );
}

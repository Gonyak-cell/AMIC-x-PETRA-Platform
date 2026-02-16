import { useState, useEffect, useRef } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { toast } from "sonner";
import {
  Building2,
  Loader2,
  CheckCircle,
  AlertCircle,
} from "lucide-react";
import { Button, Card, Input, PageHero, Select, Spinner } from "@/components/ui";
import { cn } from "@/lib/cn";
import { useCreateDocument } from "@/modules/im/hooks/useDocuments";
import { useCompany, useFetchCompany } from "@/modules/im/hooks/useCompanies";
import type { IMStyle, IndustryId, SectionId } from "@/modules/im/types/document";
import {
  CONTENT_SECTIONS,
  STRUCTURAL_SECTIONS,
  SECTION_LABEL_MAP,
  isIMStyle,
} from "@/modules/im/types/document";
import { INDUSTRY_OPTIONS, isIndustryId } from "@/types/industry";

const STYLE_OPTIONS = [
  { value: "TITAN", label: "Titan - Concise Summary" },
  { value: "COVENANT", label: "Covenant - Financial Focus" },
  { value: "FULL", label: "Full - Comprehensive" },
  { value: "CUSTOM", label: "Custom - Select Sections" },
];

/** DART 산업명 → 백엔드 industry ID 매핑 (정확 매칭 + 부분 매칭 지원) */
const DART_INDUSTRY_MAP: Record<string, IndustryId> = {
  소프트웨어: "tech",
  "정보통신업": "tech",
  "정보통신": "tech",
  IT: "tech",
  제조: "manufacturing",
  "제조업": "manufacturing",
  의료: "healthcare",
  "제약": "healthcare",
  바이오: "healthcare",
  운송: "logistics",
  물류: "logistics",
  "운수업": "logistics",
  금융: "financial_services",
  은행: "financial_services",
  보험: "financial_services",
  증권: "financial_services",
  "금융업": "financial_services",
  부동산: "real_estate",
  "부동산업": "real_estate",
  에너지: "energy",
  유통: "consumer",
  소비재: "consumer",
};

/** DART 산업명을 IndustryId로 매핑 — 정확 매칭 우선, 실패 시 키워드 포함 여부로 부분 매칭 */
function matchDartIndustry(dartIndustry: string): IndustryId | undefined {
  const exact = DART_INDUSTRY_MAP[dartIndustry];
  if (exact) return exact;
  // 길이 내림차순 정렬 → 더 구체적인 키워드 우선 매칭 (e.g. "정보통신업" > "IT")
  const sorted = Object.entries(DART_INDUSTRY_MAP).sort(
    ([a], [b]) => b.length - a.length,
  );
  for (const [keyword, id] of sorted) {
    if (dartIndustry.includes(keyword)) return id;
  }
  return undefined;
}


const STEP_TITLES = ["Company", "IM Settings", "Confirm"];

interface FormData {
  corp_code: string;
  project_name: string;
  im_style: IMStyle;
  industry: IndustryId;
  sections: SectionId[];
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
  const styleParam = searchParams.get("style");
  const initialStyle: IMStyle = styleParam && isIMStyle(styleParam) ? styleParam : "FULL";
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
  const lastFetchedCorpCode = useRef("");
  const fetchCompanyMutate = fetchCompany.mutateAsync;
  useEffect(() => {
    if (!urlCorpCode || !/^\d{8}$/.test(urlCorpCode)) return;
    if (urlCorpCode === lastFetchedCorpCode.current) return;
    lastFetchedCorpCode.current = urlCorpCode;
    let cancelled = false;
    fetchCompanyMutate(urlCorpCode)
      .then(() => {
        if (cancelled) return;
        setFormData((prev) => ({ ...prev, corp_code: urlCorpCode, industry: "general" }));
        toast.success("Company data fetch initiated");
      })
      .catch(() => {
        if (cancelled) return;
        toast.error("Failed to fetch company data");
      });
    return () => { cancelled = true; };
  }, [urlCorpCode, fetchCompanyMutate]);

  const updateField = <K extends keyof FormData>(field: K, value: FormData[K]) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  const handleFetchCompany = async () => {
    if (!corpCodeInput || !/^\d{8}$/.test(corpCodeInput)) {
      toast.error("Please enter a valid 8-digit numeric corp code");
      return;
    }
    try {
      await fetchCompany.mutateAsync(corpCodeInput);
      setFormData((prev) => ({ ...prev, corp_code: corpCodeInput, industry: "general" }));
      toast.success("Company data fetch initiated");
    } catch {
      toast.error("Failed to fetch company data");
    }
  };

  const handleNext = () => setStep((s) => Math.min(s + 1, 2));
  const handleBack = () => setStep((s) => Math.max(s - 1, 0));

  const handleSubmit = async () => {
    try {
      // For CUSTOM style, always include structural sections alongside user picks
      const sections =
        formData.im_style === "CUSTOM"
          ? [
              ...STRUCTURAL_SECTIONS,
              ...formData.sections.filter(
                (s) => !(STRUCTURAL_SECTIONS as string[]).includes(s),
              ),
            ]
          : undefined;

      const result = await createDocument.mutateAsync({
        corp_code: formData.corp_code,
        project_name: formData.project_name || undefined,
        im_style: formData.im_style,
        sections,
        industry: formData.industry || undefined,
        pdf_password: formData.pdf_password || undefined,
      });
      toast.success("IM generation started");
      navigate(`/im/documents/${result.id}`);
    } catch {
      toast.error("Failed to create IM document");
    }
  };

  // Auto-populate industry from company data (DART 산업명 → backend ID 매핑)
  // Track which corp_code's industry was already auto-set to allow re-population on company change
  const industrySetForCorpCode = useRef("");
  useEffect(() => {
    if (!company?.industry || !formData.corp_code) return;
    if (industrySetForCorpCode.current === formData.corp_code) return;
    // Only auto-populate when industry is still default
    if (formData.industry !== "general") return;
    // 1. INDUSTRY_OPTIONS value/label 직접 매칭
    const directMatch = INDUSTRY_OPTIONS.find(
      (opt) => opt.value === company.industry || opt.label === company.industry,
    );
    if (directMatch && isIndustryId(directMatch.value)) {
      industrySetForCorpCode.current = formData.corp_code;
      updateField("industry", directMatch.value);
      return;
    }
    // 2. DART 산업명 매핑 (정확 매칭 + 부분 매칭)
    const mapped = matchDartIndustry(company.industry);
    if (mapped) {
      industrySetForCorpCode.current = formData.corp_code;
      updateField("industry", mapped);
    } else {
      // 매핑 실패 — ref 업데이트로 재시도 방지 (사용자가 수동 선택)
      industrySetForCorpCode.current = formData.corp_code;
    }
  }, [company?.industry, formData.corp_code, formData.industry]);

  const canProceedStep0 =
    formData.corp_code &&
    (company?.fetch_status === "COMPLETED" || company?.fetch_status === "REFRESHING");
  const canProceedStep1 =
    formData.im_style &&
    (formData.im_style !== "CUSTOM" || formData.sections.length > 0);

  const toggleSection = (section: SectionId) => {
    setFormData((prev) => ({
      ...prev,
      sections: prev.sections.includes(section)
        ? prev.sections.filter((s) => s !== section)
        : [...prev.sections, section],
    }));
  };

  return (
    <div className="space-y-6">
      <PageHero
        title="Create New IM"
        subtitle="Generate an Investment Memorandum in 3 simple steps"
        compact
      />

      <Card>
        {/* Step indicator */}
        <ol className="flex items-center gap-2 mb-6 list-none p-0 m-0" aria-label="Creation steps">
          {STEP_TITLES.map((title, i) => (
            <li
              key={title}
              className="flex items-center gap-2"
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
            </li>
          ))}
        </ol>

        {/* Step 1: Company Selection */}
        {step === 0 && (
          <div className="space-y-4">
            <div className="flex gap-3 items-end">
              <div className="flex-1">
                <Input
                  label="Corp Code (8-digit)"
                  value={corpCodeInput}
                  onChange={(e) => setCorpCodeInput(e.target.value.replace(/\D/g, ""))}
                  placeholder="e.g. 00126380"
                  maxLength={8}
                  inputMode="numeric"
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
                          <p className="text-text-dark">
                            {company.industry}
                            {formData.industry === "general" && (
                              <span className={cn(
                                "ml-2 text-xs",
                                company.fetch_status === "COMPLETED"
                                  ? "text-text-secondary"
                                  : "text-amic animate-pulse",
                              )}>
                                {company.fetch_status === "COMPLETED"
                                  ? "Select industry manually"
                                  : "Detecting industry..."}
                              </span>
                            )}
                          </p>
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
                onChange={(e) => {
                  const v = e.target.value;
                  if (isIMStyle(v)) updateField("im_style", v);
                }}
              />
              <Select
                label="Industry"
                options={INDUSTRY_OPTIONS}
                value={formData.industry}
                onChange={(e) => {
                  const v = e.target.value;
                  if (isIndustryId(v)) updateField("industry", v);
                }}
              />
            </div>

            {/* Custom section selector */}
            {formData.im_style === "CUSTOM" && (
              <div>
                <label className="block text-sm font-medium text-text-dark mb-2">
                  Select Sections
                </label>
                <p className="text-xs text-text-secondary mb-3">
                  Cover, Disclaimer, Table of Contents, and Contact are always
                  included.
                </p>
                <div
                  className="grid grid-cols-2 sm:grid-cols-3 gap-2"
                  role="group"
                  aria-label="IM document sections"
                >
                  {CONTENT_SECTIONS.map(({ id, label }) => (
                    <button
                      key={id}
                      type="button"
                      onClick={() => toggleSection(id)}
                      aria-pressed={formData.sections.includes(id)}
                      className={`px-3 py-2 text-sm rounded-lg border transition-colors text-left ${
                        formData.sections.includes(id)
                          ? "border-amic bg-amic/10 text-amic font-medium"
                          : "border-gray-border bg-white text-text-secondary hover:border-amic/50"
                      }`}
                    >
                      {label}
                    </button>
                  ))}
                </div>
                {formData.sections.length > 0 && (
                  <p className="mt-2 text-xs text-text-secondary">
                    {formData.sections.length} content section(s) +{" "}
                    {STRUCTURAL_SECTIONS.length} structural ={" "}
                    {formData.sections.length + STRUCTURAL_SECTIONS.length} total
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
                        {SECTION_LABEL_MAP[s] ?? s}
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

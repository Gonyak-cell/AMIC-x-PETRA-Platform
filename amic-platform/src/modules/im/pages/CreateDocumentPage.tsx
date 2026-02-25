import { useState, useEffect, useRef } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { toast } from "sonner";
import {
  Building2,
  Loader2,
  CheckCircle,
  AlertCircle,
  FileSpreadsheet,
  Database,
  PenLine,
} from "lucide-react";
import { Button, Card, Input, PageHero, Select, Spinner } from "@/components/ui";
import { useCreateDocument, useUploadFinancials } from "@/modules/im/hooks/useDocuments";
import { useCompany, useFetchCompany } from "@/modules/im/hooks/useCompanies";
import type { IMStyle, IndustryId, SectionId, DataSource } from "@/modules/im/types/document";
import {
  CONTENT_SECTIONS,
  STRUCTURAL_SECTIONS,
  SECTION_LABEL_MAP,
  isIMStyle,
} from "@/modules/im/types/document";
import { INDUSTRY_OPTIONS, isIndustryId } from "@/types/industry";
import heroImg from "@/assets/images/heroes/hero-arch-mono.jpg";

const STYLE_OPTIONS = [
  { value: "TITAN", label: "Titan - Concise Summary" },
  { value: "COVENANT", label: "Covenant - Financial Focus" },
  { value: "FULL", label: "Full - Comprehensive" },
  { value: "TEASER", label: "Teaser - One-pager" },
  { value: "CUSTOM", label: "Custom - Select Sections" },
];

/** DART 산업명 → 백엔드 industry ID 매핑 */
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

function matchDartIndustry(dartIndustry: string): IndustryId | undefined {
  const exact = DART_INDUSTRY_MAP[dartIndustry];
  if (exact) return exact;
  const sorted = Object.entries(DART_INDUSTRY_MAP).sort(
    ([a], [b]) => b.length - a.length,
  );
  for (const [keyword, id] of sorted) {
    if (dartIndustry.includes(keyword)) return id;
  }
  return undefined;
}

const STEP_TITLES = ["Project & Company", "IM Settings & Confirm"];

interface FormData {
  company_name: string;
  project_name: string;
  corp_code: string;
  data_source: DataSource;
  im_style: IMStyle;
  industry: IndustryId;
  sections: SectionId[];
  pdf_password: string;
  excel_file: File | null;
}

const INITIAL_FORM: FormData = {
  company_name: "",
  project_name: "",
  corp_code: "",
  data_source: "MANUAL",
  im_style: "FULL",
  industry: "general",
  sections: [],
  pdf_password: "",
  excel_file: null,
};

export default function CreateDocumentPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const styleParam = searchParams.get("style");
  const initialStyle: IMStyle = styleParam && isIMStyle(styleParam) ? styleParam : "FULL";

  const [step, setStep] = useState(0);
  const [formData, setFormData] = useState<FormData>({
    ...INITIAL_FORM,
    im_style: initialStyle,
  });
  const [corpCodeInput, setCorpCodeInput] = useState("");
  const [showDartPanel, setShowDartPanel] = useState(false);

  const createDocument = useCreateDocument();
  const uploadFinancials = useUploadFinancials();
  const fetchCompany = useFetchCompany();
  const { data: company, isLoading: companyLoading } = useCompany(formData.corp_code);

  const fileInputRef = useRef<HTMLInputElement>(null);

  const updateField = <K extends keyof FormData>(field: K, value: FormData[K]) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  // DART 자동 수집 핸들러
  const handleFetchDart = async () => {
    if (!corpCodeInput || !/^\d{8}$/.test(corpCodeInput)) {
      toast.error("8자리 숫자 Corp Code를 입력해주세요");
      return;
    }
    try {
      await fetchCompany.mutateAsync(corpCodeInput);
      setFormData((prev) => ({
        ...prev,
        corp_code: corpCodeInput,
        data_source: "DART",
      }));
      toast.success("DART 데이터 수집을 시작했습니다");
    } catch {
      toast.error("DART 데이터 수집에 실패했습니다");
    }
  };

  // DART에서 industry 자동 매핑
  const industrySetForCorpCode = useRef("");
  useEffect(() => {
    if (!company?.industry || !formData.corp_code) return;
    if (industrySetForCorpCode.current === formData.corp_code) return;
    if (formData.industry !== "general") return;

    const directMatch = INDUSTRY_OPTIONS.find(
      (opt) => opt.value === company.industry || opt.label === company.industry,
    );
    if (directMatch && isIndustryId(directMatch.value)) {
      industrySetForCorpCode.current = formData.corp_code;
      updateField("industry", directMatch.value);
      return;
    }
    const mapped = matchDartIndustry(company.industry);
    if (mapped) {
      industrySetForCorpCode.current = formData.corp_code;
      updateField("industry", mapped);
    } else {
      industrySetForCorpCode.current = formData.corp_code;
    }
  }, [company?.industry, formData.corp_code, formData.industry]);

  // DART에서 회사명 자동 채우기
  useEffect(() => {
    if (
      company?.corp_name &&
      formData.data_source === "DART" &&
      !formData.company_name
    ) {
      updateField("company_name", company.corp_name);
    }
  }, [company?.corp_name, formData.data_source, formData.company_name]);

  // Excel 파일 선택 핸들러
  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const ext = file.name.split(".").pop()?.toLowerCase();
    if (!ext || !["xlsx", "xlsm", "csv"].includes(ext)) {
      toast.error("Excel (.xlsx) 또는 CSV 파일만 지원합니다");
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      toast.error("파일 크기는 10MB 이하여야 합니다");
      return;
    }
    setFormData((prev) => ({ ...prev, excel_file: file, data_source: "EXCEL" }));
    toast.success(`${file.name} 선택됨`);
  };

  const handleRemoveFile = () => {
    setFormData((prev) => ({
      ...prev,
      excel_file: null,
      data_source: prev.corp_code ? "DART" : "MANUAL",
    }));
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  // DART 연동 해제
  const handleRemoveDart = () => {
    setFormData((prev) => ({
      ...prev,
      corp_code: "",
      data_source: prev.excel_file ? "EXCEL" : "MANUAL",
    }));
    setCorpCodeInput("");
    setShowDartPanel(false);
    industrySetForCorpCode.current = "";
  };

  const handleNext = () => setStep((s) => Math.min(s + 1, 1));
  const handleBack = () => setStep((s) => Math.max(s - 1, 0));

  const handleSubmit = async () => {
    try {
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
        company_name: formData.company_name,
        project_name: formData.project_name,
        corp_code: formData.corp_code || undefined,
        data_source: formData.data_source,
        im_style: formData.im_style,
        sections,
        industry: formData.industry || undefined,
        pdf_password: formData.pdf_password || undefined,
      });

      // Excel 파일 업로드 (data_source === "EXCEL")
      if (formData.data_source === "EXCEL" && formData.excel_file) {
        try {
          await uploadFinancials.mutateAsync({
            documentId: result.id,
            file: formData.excel_file,
          });
        } catch {
          toast.error("재무데이터 업로드 실패 — 문서는 생성되었습니다");
        }
      }

      toast.success("IM 생성이 시작되었습니다");
      navigate(`/im/documents/${result.id}`);
    } catch {
      toast.error("IM 문서 생성에 실패했습니다");
    }
  };

  const canProceedStep0 =
    formData.company_name.trim().length > 0 &&
    formData.project_name.trim().length > 0;

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

  const dataSourceLabel =
    formData.data_source === "DART"
      ? "DART 자동 수집"
      : formData.data_source === "EXCEL"
        ? "Excel 업로드"
        : "수동 입력";

  return (
    <div className="space-y-6">
      <PageHero
        title="Create New IM"
        subtitle="Generate an Investment Memorandum"
        backgroundImage={heroImg}
        backgroundOpacity={0.18}
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

        {/* ── Step 0: Project & Company ── */}
        {step === 0 && (
          <div className="space-y-5">
            {/* 필수 입력 */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Input
                label="Project Name *"
                value={formData.project_name}
                onChange={(e) => updateField("project_name", e.target.value)}
                placeholder="e.g. Project TITAN"
              />
              <Input
                label="Company Name *"
                value={formData.company_name}
                onChange={(e) => updateField("company_name", e.target.value)}
                placeholder="e.g. (주)샘플테크"
              />
            </div>

            {/* 데이터 소스 옵션 */}
            <div className="space-y-3">
              <label className="block text-sm font-medium text-text-dark">
                Data Source (Optional)
              </label>
              <p className="text-xs text-text-secondary">
                DART 연동이나 Excel 업로드 없이도 IM을 생성할 수 있습니다.
                LLM이 입력된 정보를 기반으로 정성적 내러티브를 생성합니다.
              </p>

              <div className="flex flex-wrap gap-2">
                {/* DART 연동 버튼 */}
                {!formData.corp_code ? (
                  <Button
                    variant="ghost"
                    onClick={() => setShowDartPanel(!showDartPanel)}
                    className="gap-2"
                  >
                    <Database className="h-4 w-4" />
                    DART 자동 수집
                  </Button>
                ) : (
                  <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-positive/10 text-positive text-sm">
                    <CheckCircle className="h-4 w-4" />
                    DART 연동됨 ({formData.corp_code})
                    <button
                      type="button"
                      onClick={handleRemoveDart}
                      className="ml-1 text-text-secondary hover:text-negative text-xs"
                    >
                      ✕
                    </button>
                  </div>
                )}

                {/* Excel 업로드 버튼 */}
                {!formData.excel_file ? (
                  <Button
                    variant="ghost"
                    onClick={() => fileInputRef.current?.click()}
                    className="gap-2"
                  >
                    <FileSpreadsheet className="h-4 w-4" />
                    Excel 업로드
                  </Button>
                ) : (
                  <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-amic/10 text-amic text-sm">
                    <FileSpreadsheet className="h-4 w-4" />
                    {formData.excel_file.name}
                    <button
                      type="button"
                      onClick={handleRemoveFile}
                      className="ml-1 text-text-secondary hover:text-negative text-xs"
                    >
                      ✕
                    </button>
                  </div>
                )}

                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".xlsx,.xlsm,.csv"
                  onChange={handleFileSelect}
                  className="hidden"
                />
              </div>

              {/* DART Corp Code 입력 패널 */}
              {showDartPanel && !formData.corp_code && (
                <div className="border border-gray-border rounded-lg p-4 space-y-3">
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
                      onClick={handleFetchDart}
                      loading={fetchCompany.isPending}
                      disabled={corpCodeInput.length !== 8}
                    >
                      Fetch
                    </Button>
                  </div>
                  <p className="text-xs text-text-secondary">
                    상장사인 경우 DART에서 재무데이터와 기업 정보를 자동으로 수집합니다.
                  </p>
                </div>
              )}

              {/* DART Company 프리뷰 */}
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

              {/* 데이터 소스 상태 표시 */}
              <div className="flex items-center gap-2 text-xs text-text-secondary">
                {formData.data_source === "DART" && <Database className="h-3.5 w-3.5" />}
                {formData.data_source === "EXCEL" && <FileSpreadsheet className="h-3.5 w-3.5" />}
                {formData.data_source === "MANUAL" && <PenLine className="h-3.5 w-3.5" />}
                Data source: {dataSourceLabel}
              </div>
            </div>
          </div>
        )}

        {/* ── Step 1: IM Settings + Confirm ── */}
        {step === 1 && (
          <div className="space-y-5">
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

            {/* CUSTOM 모드 — 섹션 선택 */}
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

            {/* Review 요약 */}
            <div>
              <h4 className="text-sm font-heading font-semibold text-text-dark mb-2">
                Review & Confirm
              </h4>
              <div className="bg-bg-cool rounded-lg p-4 space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-text-secondary">Project</span>
                  <span className="text-text-dark font-medium">{formData.project_name}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-text-secondary">Company</span>
                  <span className="text-text-dark font-medium">{formData.company_name}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-text-secondary">Data Source</span>
                  <span className="text-text-dark">{dataSourceLabel}</span>
                </div>
                {formData.corp_code && (
                  <div className="flex justify-between">
                    <span className="text-text-secondary">Corp Code</span>
                    <span className="font-mono text-text-dark">{formData.corp_code}</span>
                  </div>
                )}
                {formData.excel_file && (
                  <div className="flex justify-between">
                    <span className="text-text-secondary">Excel File</span>
                    <span className="text-text-dark">{formData.excel_file.name}</span>
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
                {formData.im_style === "CUSTOM" && formData.sections.length > 0 && (
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
          {step < 1 ? (
            <Button
              variant="primary"
              onClick={handleNext}
              disabled={!canProceedStep0}
            >
              Next
            </Button>
          ) : (
            <Button
              variant="accent"
              onClick={handleSubmit}
              loading={createDocument.isPending || uploadFinancials.isPending}
              disabled={
                !canProceedStep1 ||
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

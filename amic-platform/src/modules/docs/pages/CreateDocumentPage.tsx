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
  BarChart2,
} from "lucide-react";
import { Button, Card, Input, PageHero, Select, Spinner } from "@/components/ui";
import { useCreateDocument, useUploadFinancials } from "@/modules/docs/hooks/useDocuments";
import { useCompany, useFetchCompany } from "@/modules/docs/hooks/useCompanies";
import { useCreateFDDDocument } from "@/modules/docs/hooks/useFDDDocuments";
import { DocumentTypePicker } from "@/modules/docs/components/DocumentTypePicker";
import { PPTStylePicker } from "@/modules/docs/components/PPTStylePicker";
import type { DocumentType, IMStyle, IndustryId, SectionId, DataSource, PPTDesignStyle } from "@/modules/docs/types/document";
import {
  CONTENT_SECTIONS,
  STRUCTURAL_SECTIONS,
  SECTION_LABEL_MAP,
  isIMStyle,
} from "@/modules/docs/types/document";
import { INDUSTRY_OPTIONS, isIndustryId } from "@/types/industry";
import { maApi } from "@/api/maClient";
import heroImg from "@/assets/images/heroes/hero-arch-silver.jpg";

const IM_STYLE_OPTIONS = [
  { value: "TITAN", label: "Titan - Concise Summary" },
  { value: "COVENANT", label: "Covenant - Financial Focus" },
  { value: "FULL", label: "Full - Comprehensive" },
  { value: "CUSTOM", label: "Custom - Select Sections" },
];

const FILE_FORMAT_OPTIONS = [
  { value: "pptx", label: "PowerPoint (.pptx)" },
  { value: "docx", label: "Word (.docx)" },
];

const DART_INDUSTRY_MAP: Record<string, IndustryId> = {
  "소프트웨어": "tech",
  "정보통신업": "tech",
  "정보통신": "tech",
  IT: "tech",
  "제조": "manufacturing",
  "제조업": "manufacturing",
  "의료": "healthcare",
  "제약": "healthcare",
  "바이오": "healthcare",
  "운송": "logistics",
  "물류": "logistics",
  "운수업": "logistics",
  "금융": "financial_services",
  "은행": "financial_services",
  "보험": "financial_services",
  "증권": "financial_services",
  "금융업": "financial_services",
  "부동산": "real_estate",
  "부동산업": "real_estate",
  "에너지": "energy",
  "유통": "consumer",
  "소비재": "consumer",
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

interface FormData {
  docType: DocumentType | null;
  // IM/TM 공통
  company_name: string;
  project_name: string;
  corp_code: string;
  data_source: DataSource;
  im_style: IMStyle;
  industry: IndustryId;
  sections: SectionId[];
  pdf_password: string;
  excel_file: File | null;
  // PPT 디자인 스타일 (IM/TM 전용)
  ppt_design_style: PPTDesignStyle;
  ppt_collab_partner_name: string;
  // FDD 전용
  fdd_deal_name: string;
  fdd_target_company: string;
  fdd_include_qoe: boolean;
  fdd_include_nwc: boolean;
  fdd_include_debt: boolean;
  fdd_file_format: "pptx" | "docx";
}

const INITIAL_FORM: FormData = {
  docType: null,
  company_name: "",
  project_name: "",
  corp_code: "",
  data_source: "MANUAL",
  im_style: "FULL",
  industry: "general",
  sections: [],
  pdf_password: "",
  excel_file: null,
  ppt_design_style: "AMIC",
  ppt_collab_partner_name: "",
  fdd_deal_name: "",
  fdd_target_company: "",
  fdd_include_qoe: true,
  fdd_include_nwc: true,
  fdd_include_debt: true,
  fdd_file_format: "pptx",
};

interface CreateDocumentPageProps {
  defaultType?: DocumentType;
}

export default function CreateDocumentPage({ defaultType }: CreateDocumentPageProps = {}) {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const _typeRaw = searchParams.get("type") ?? defaultType ?? null;
  const typeParam: DocumentType | null =
    _typeRaw === "teaser" || _typeRaw === "im" || _typeRaw === "fdd"
      ? _typeRaw
      : null;
  const txnId = searchParams.get("txn_id");
  const companyParam = searchParams.get("company") ?? "";
  const projectParam = searchParams.get("project") ?? "";
  const industryParam = searchParams.get("industry") ?? "";
  const returnUrl = searchParams.get("return_url");

  // Step 구조:
  //   0 = 문서 유형 선택 (모든 문서)
  //   1 = PPT 디자인 스타일 선택 (IM/TM 전용, FDD 건너뜀)
  //   2 = 회사/프로젝트 정보 (모든 문서)
  //   3 = 섹션/설정 확인 (모든 문서)
  // FDD 흐름: 0 → 2 → 3
  // IM/TM 흐름: 0 → 1 → 2 → 3
  const [step, setStep] = useState(() => {
    if (!typeParam) return 0;
    if (typeParam === "fdd") return 2; // FDD: 디자인 단계 건너뜀
    return 1; // IM/TM: 디자인 선택부터 시작
  });

  const [formData, setFormData] = useState<FormData>(() => {
    const initial = { ...INITIAL_FORM };
    if (typeParam === "teaser") {
      initial.docType = "teaser";
      initial.im_style = "TEASER";
    } else if (typeParam === "im") {
      initial.docType = "im";
    } else if (typeParam === "fdd") {
      initial.docType = "fdd";
    }
    // URL params 자동 채움
    if (companyParam) {
      initial.company_name = companyParam;
      initial.fdd_target_company = companyParam;
    }
    if (projectParam) {
      initial.project_name = projectParam;
      initial.fdd_deal_name = projectParam;
    }
    if (industryParam && isIndustryId(industryParam)) {
      initial.industry = industryParam;
    }
    return initial;
  });
  const [corpCodeInput, setCorpCodeInput] = useState("");
  const [showDartPanel, setShowDartPanel] = useState(false);

  const createDocument = useCreateDocument();
  const uploadFinancials = useUploadFinancials();
  const fetchCompany = useFetchCompany();
  const createFDDDocument = useCreateFDDDocument();
  const { data: company, isLoading: companyLoading } = useCompany(formData.corp_code);

  const fileInputRef = useRef<HTMLInputElement>(null);

  const updateField = <K extends keyof FormData>(field: K, value: FormData[K]) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  // Document type selection handler
  const handleTypeSelect = (type: DocumentType) => {
    setFormData((prev) => ({
      ...prev,
      docType: type,
      im_style:
        type === "teaser"
          ? "TEASER"
          : type === "fdd"
            ? prev.im_style
            : prev.im_style === "TEASER"
              ? "FULL"
              : prev.im_style,
    }));
  };

  // DART
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

  // DART industry auto-mapping
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

  // Auto-fill company name from DART
  useEffect(() => {
    if (
      company?.corp_name &&
      formData.data_source === "DART" &&
      !formData.company_name
    ) {
      updateField("company_name", company.corp_name);
    }
  }, [company?.corp_name, formData.data_source, formData.company_name]);

  // Excel file handling
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

  const isFDD = formData.docType === "fdd";
  const isTeaser = formData.docType === "teaser";

  const handleNext = () => {
    if (step === 0 && isFDD) {
      setStep(2); // FDD: 디자인 단계 건너뜀
    } else {
      setStep((s) => Math.min(s + 1, 3));
    }
  };

  const handleBack = () => {
    if (step === 2 && isFDD) {
      setStep(0); // FDD 역방향: 디자인 단계 건너뜀
    } else {
      setStep((s) => Math.max(s - 1, 0));
    }
  };

  const handleSubmit = async () => {
    try {
      if (formData.docType === "fdd") {
        // FDD 분기: Deal 생성 + 보고서 버전 생성
        const result = await createFDDDocument.mutateAsync({
          deal_name: formData.fdd_deal_name,
          target_company_name: formData.fdd_target_company,
          industry: formData.industry,
          include_qoe: formData.fdd_include_qoe,
          include_nwc: formData.fdd_include_nwc,
          include_debt: formData.fdd_include_debt,
          file_format: formData.fdd_file_format,
        });

        // MA Transaction 연결
        if (txnId) {
          try {
            await maApi.patch(`/transactions/${txnId}`, {
              fdd_deal_id: result.deal.id,
            });
          } catch {
            toast.warning("거래와의 연결에 실패했습니다. MA 워크스페이스에서 수동으로 연결해 주세요.");
          }
        }

        // FDD 워크스페이스로 이동 (상세 분석 계속)
        navigate(returnUrl ?? `/fdd/deals/${result.deal.id}`);
      } else {
        // IM/TM 분기 (기존 로직 + PPT 디자인 스타일 추가)
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
          ppt_design_style: formData.ppt_design_style,
          collab_partner_name:
            formData.ppt_design_style === "AMIC_COLLAB"
              ? formData.ppt_collab_partner_name || undefined
              : undefined,
        });

        if (formData.data_source === "EXCEL" && formData.excel_file) {
          try {
            await uploadFinancials.mutateAsync({
              documentId: result.id,
              file: formData.excel_file,
            });
          } catch {
            toast.error("재무데이터 업로드 실패 - 문서는 생성되었습니다");
          }
        }

        // MA Transaction 연결
        if (txnId) {
          try {
            await maApi.patch(`/transactions/${txnId}`, {
              im_document_id: result.id,
            });
          } catch {
            toast.warning("거래와의 연결에 실패했습니다. MA 워크스페이스에서 수동으로 연결해 주세요.");
          }
        }

        const typeLabel = formData.docType === "teaser" ? "TM" : "IM";
        toast.success(`${typeLabel} 생성이 시작되었습니다`);

        if (returnUrl) {
          navigate(returnUrl);
        } else {
          navigate(`/docs/documents/${result.id}`);
        }
      }
    } catch {
      toast.error("문서 생성에 실패했습니다");
    }
  };

  // ─── Step 진행 조건 ────────────────────────────────────────
  const canProceedStep0 = formData.docType !== null;

  // Step 1 (PPT 디자인 스타일) — IM/TM 전용
  const canProceedStep1 =
    formData.ppt_design_style !== null &&
    (formData.ppt_design_style !== "AMIC_COLLAB" ||
      formData.ppt_collab_partner_name.trim().length > 0);

  // Step 2 (회사/프로젝트 정보)
  const canProceedStep2 = isFDD
    ? formData.fdd_deal_name.trim().length > 0 && formData.fdd_target_company.trim().length > 0
    : formData.company_name.trim().length > 0 && formData.project_name.trim().length > 0;

  // Step 3 (설정 확인)
  const canProceedStep3 = isFDD
    ? true
    : formData.im_style &&
      (formData.im_style !== "CUSTOM" || formData.sections.length > 0);

  // 현재 step → 진행 조건 매핑
  const canProceedCurrent =
    step === 0 ? canProceedStep0
    : step === 1 ? canProceedStep1
    : step === 2 ? canProceedStep2
    : canProceedStep3;

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

  const isSubmitting =
    createDocument.isPending ||
    uploadFinancials.isPending ||
    createFDDDocument.isPending;

  // ─── Step 인디케이터 ──────────────────────────────────────
  // FDD: 3단계, IM/TM: 4단계
  const stepLabels = isFDD
    ? ["유형 선택", "프로젝트 정보", "설정 확인"]
    : ["유형 선택", "디자인 스타일", "프로젝트 정보", "설정 확인"];

  // 내부 step → 표시용 index 변환
  const displayStepIndex = isFDD && step >= 2 ? step - 1 : step;

  return (
    <div className="space-y-6">
      <PageHero
        title="Create New Document"
        backgroundImage={heroImg}
        backgroundOpacity={0.18}
        subtitle={
          isFDD
            ? "Financial Due Diligence 보고서 생성"
            : isTeaser
              ? "Teaser Memorandum 생성"
              : formData.docType === "im"
                ? "Information Memorandum 생성"
                : "문서 유형을 선택하세요"
        }
        compact
      />

      <Card>
        {/* Step indicator */}
        <ol className="flex items-center gap-2 mb-6 list-none p-0 m-0" aria-label="Creation steps">
          {stepLabels.map((title, i) => (
            <li
              key={title}
              className="flex items-center gap-2"
              aria-current={i === displayStepIndex ? "step" : undefined}
            >
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
                  i === displayStepIndex
                    ? "bg-amic text-white"
                    : i < displayStepIndex
                      ? "bg-positive text-white"
                      : "bg-gray-100 text-text-secondary"
                }`}
                aria-label={`Step ${i + 1}: ${title}${i < displayStepIndex ? " (completed)" : i === displayStepIndex ? " (current)" : ""}`}
              >
                {i + 1}
              </div>
              <span
                className={`text-sm hidden sm:inline ${
                  i === displayStepIndex ? "text-text-dark font-medium" : "text-text-secondary"
                }`}
              >
                {title}
              </span>
              {i < stepLabels.length - 1 && (
                <div className="w-8 h-px bg-gray-200 hidden sm:block" aria-hidden="true" />
              )}
            </li>
          ))}
        </ol>

        {/* Step 0: Document Type */}
        {step === 0 && (
          <div className="space-y-5">
            <label className="block text-sm font-medium text-text-dark mb-2">
              문서 유형 선택
            </label>
            <DocumentTypePicker
              selected={formData.docType}
              onSelect={handleTypeSelect}
            />
          </div>
        )}

        {/* Step 1: PPT 디자인 스타일 (IM/TM 전용) */}
        {step === 1 && !isFDD && (
          <div className="space-y-4">
            <div>
              <h3 className="text-sm font-medium text-text-dark mb-1">PPT 디자인 스타일 선택</h3>
              <p className="text-xs text-text-secondary">
                생성될 PPTX 파일에 적용할 브랜딩 스타일을 선택하세요.
              </p>
            </div>
            <PPTStylePicker
              selected={formData.ppt_design_style}
              partnerName={formData.ppt_collab_partner_name}
              onSelect={(style) => updateField("ppt_design_style", style)}
              onPartnerNameChange={(name) => updateField("ppt_collab_partner_name", name)}
            />
          </div>
        )}

        {/* Step 2: Project & Company */}
        {step === 2 && (
          <div className="space-y-5">
            {isFDD ? (
              /* FDD 전용 입력 폼 */
              <div className="space-y-4">
                <div className="flex items-center gap-2 p-3 rounded-lg bg-emerald-50 border border-emerald-200">
                  <BarChart2 className="h-4 w-4 text-emerald-600 flex-shrink-0" />
                  <p className="text-xs text-emerald-700">
                    FDD가 생성되고 보고서 초안이 자동 작성됩니다. 상세 분석(QoE/NWC/Net Debt)은 FDD 워크스페이스에서 이어서 진행하세요.
                  </p>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <Input
                    label="Deal Name *"
                    value={formData.fdd_deal_name}
                    onChange={(e) => updateField("fdd_deal_name", e.target.value)}
                    placeholder="e.g. Project ATLAS"
                  />
                  <Input
                    label="Target Company Name *"
                    value={formData.fdd_target_company}
                    onChange={(e) => updateField("fdd_target_company", e.target.value)}
                    placeholder="e.g. (주)샘플테크"
                  />
                </div>
              </div>
            ) : (
              /* IM/TM 입력 폼 (기존) */
              <div className="space-y-5">
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

                {/* Data Source Options */}
                <div className="space-y-3">
                  <label className="block text-sm font-medium text-text-dark">
                    Data Source (Optional)
                  </label>
                  <p className="text-xs text-text-secondary">
                    DART 연동이나 Excel 업로드 없이도 문서를 생성할 수 있습니다.
                  </p>

                  <div className="flex flex-wrap gap-2">
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
                          &#x2715;
                        </button>
                      </div>
                    )}

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
                          &#x2715;
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

                  <div className="flex items-center gap-2 text-xs text-text-secondary">
                    {formData.data_source === "DART" && <Database className="h-3.5 w-3.5" />}
                    {formData.data_source === "EXCEL" && <FileSpreadsheet className="h-3.5 w-3.5" />}
                    {formData.data_source === "MANUAL" && <PenLine className="h-3.5 w-3.5" />}
                    Data source: {dataSourceLabel}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Step 3: Settings & Confirm */}
        {step === 3 && (
          <div className="space-y-5">
            {isFDD ? (
              /* FDD 설정 */
              <div className="space-y-5">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <Select
                    label="Industry"
                    options={INDUSTRY_OPTIONS}
                    value={formData.industry}
                    onChange={(e) => {
                      const v = e.target.value;
                      if (isIndustryId(v)) updateField("industry", v);
                    }}
                  />
                  <Select
                    label="Output Format"
                    options={FILE_FORMAT_OPTIONS}
                    value={formData.fdd_file_format}
                    onChange={(e) =>
                      updateField("fdd_file_format", e.target.value as "pptx" | "docx")
                    }
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-text-dark mb-3">
                    Analysis Scope
                  </label>
                  <div className="space-y-2">
                    {[
                      { field: "fdd_include_qoe" as const, label: "Quality of Earnings (QoE)", desc: "수익의 질 분석 — 조정 EBITDA 및 일회성 항목" },
                      { field: "fdd_include_nwc" as const, label: "Net Working Capital (NWC)", desc: "순운전자본 분석 — 계절성 및 정상화" },
                      { field: "fdd_include_debt" as const, label: "Net Debt", desc: "순차입금 분석 — 차입금 및 현금성 자산" },
                    ].map(({ field, label, desc }) => (
                      <label
                        key={field}
                        className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${
                          formData[field]
                            ? "border-emerald-200 bg-emerald-50"
                            : "border-gray-border bg-white hover:bg-bg-cool"
                        }`}
                      >
                        <input
                          type="checkbox"
                          checked={formData[field] as boolean}
                          onChange={(e) => updateField(field, e.target.checked)}
                          className="mt-0.5"
                        />
                        <div>
                          <p className="text-sm font-medium text-text-dark">{label}</p>
                          <p className="text-xs text-text-secondary">{desc}</p>
                        </div>
                      </label>
                    ))}
                  </div>
                </div>
              </div>
            ) : isTeaser ? (
              /* TM mode: TEASER style fixed */
              <div className="space-y-4">
                <div className="p-4 rounded-lg bg-violet-50 border border-violet-200">
                  <h4 className="text-sm font-heading font-semibold text-violet-800 mb-2">
                    Teaser Memorandum
                  </h4>
                  <p className="text-xs text-violet-600 mb-3">
                    4개 그룹의 고정 구조로 생성됩니다:
                  </p>
                  <div className="grid grid-cols-2 gap-2">
                    {[
                      { group: "(1) Executive Summary", items: ["Executive Summary", "Deal Overview"] },
                      { group: "(2) Market Opportunity", items: ["Target Positioning", "Market Outlook", "Demand/Supply Driver"] },
                      { group: "(3) Target Highlights", items: ["Target Overview", "Target Highlights"] },
                      { group: "(4) Financial Summary", items: ["Pro-Forma Plan", "Pro-Forma Financials"] },
                    ].map((g) => (
                      <div key={g.group} className="text-xs">
                        <p className="font-medium text-violet-800">{g.group}</p>
                        <ul className="text-violet-600 ml-3">
                          {g.items.map((item) => (
                            <li key={item}>- {item}</li>
                          ))}
                        </ul>
                      </div>
                    ))}
                  </div>
                </div>

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
            ) : (
              /* IM mode: style selection */
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <Select
                  label="IM Style"
                  options={IM_STYLE_OPTIONS}
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
            )}

            {/* CUSTOM mode: section selection */}
            {!isTeaser && !isFDD && formData.im_style === "CUSTOM" && (
              <div>
                <label className="block text-sm font-medium text-text-dark mb-2">
                  Select Sections
                </label>
                <p className="text-xs text-text-secondary mb-3">
                  Cover, Disclaimer, Table of Contents, and Contact are always included.
                </p>
                <div
                  className="grid grid-cols-2 sm:grid-cols-3 gap-2"
                  role="group"
                  aria-label="Document sections"
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

            {/* Review summary */}
            <div>
              <h4 className="text-sm font-heading font-semibold text-text-dark mb-2">
                Review & Confirm
              </h4>
              <div className="bg-bg-cool rounded-lg p-4 space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-text-secondary">Document Type</span>
                  <span className="text-text-dark font-medium">
                    {isFDD ? "Financial Due Diligence" : isTeaser ? "Teaser Memorandum" : "Information Memorandum"}
                  </span>
                </div>
                {isFDD ? (
                  <>
                    <div className="flex justify-between">
                      <span className="text-text-secondary">Deal Name</span>
                      <span className="text-text-dark font-medium">{formData.fdd_deal_name}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-text-secondary">Target Company</span>
                      <span className="text-text-dark font-medium">{formData.fdd_target_company}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-text-secondary">Analysis Scope</span>
                      <span className="text-text-dark">
                        {[
                          formData.fdd_include_qoe && "QoE",
                          formData.fdd_include_nwc && "NWC",
                          formData.fdd_include_debt && "Net Debt",
                        ]
                          .filter(Boolean)
                          .join(" · ") || "없음"}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-text-secondary">Output Format</span>
                      <span className="text-text-dark">{formData.fdd_file_format.toUpperCase()}</span>
                    </div>
                  </>
                ) : (
                  <>
                    {/* PPT 디자인 스타일 표시 */}
                    <div className="flex justify-between">
                      <span className="text-text-secondary">PPT 디자인</span>
                      <span className="text-text-dark font-medium">
                        {formData.ppt_design_style === "AMIC_COLLAB"
                          ? `AMIC x ${formData.ppt_collab_partner_name}`
                          : "AMIC 스타일"}
                      </span>
                    </div>
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
                      <span className="text-text-secondary">Style</span>
                      <span className="text-text-dark">{formData.im_style}</span>
                    </div>
                  </>
                )}
                <div className="flex justify-between">
                  <span className="text-text-secondary">Industry</span>
                  <span className="text-text-dark">{formData.industry}</span>
                </div>
                {!isTeaser && !isFDD && formData.im_style === "CUSTOM" && formData.sections.length > 0 && (
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
                {txnId && (
                  <div className="flex justify-between pt-1 border-t border-gray-200 mt-1">
                    <span className="text-text-secondary">M&A Transaction 연결</span>
                    <span className="text-positive text-xs font-medium">자동 연결됨</span>
                  </div>
                )}
              </div>
            </div>

            {!isFDD && (
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
            )}
          </div>
        )}

        {/* Navigation */}
        <div className="flex justify-between mt-8 pt-4 border-t border-gray-border">
          <Button
            variant="ghost"
            onClick={step === 0 ? () => navigate(returnUrl ?? "/docs") : handleBack}
          >
            {step === 0 ? "Cancel" : "Back"}
          </Button>
          {step < 3 ? (
            <Button
              variant="primary"
              onClick={handleNext}
              disabled={!canProceedCurrent}
            >
              Next
            </Button>
          ) : (
            <Button
              variant="accent"
              onClick={handleSubmit}
              loading={isSubmitting}
              disabled={
                !canProceedStep3 ||
                (!isFDD &&
                  formData.pdf_password.length > 0 &&
                  formData.pdf_password.length < 4)
              }
            >
              {isFDD
                ? "Create FDD"
                : isTeaser
                  ? "Generate TM"
                  : "Generate IM"}
            </Button>
          )}
        </div>
      </Card>
    </div>
  );
}

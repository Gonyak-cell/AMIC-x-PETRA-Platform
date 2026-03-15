import { useState, useCallback, useRef } from "react";
import { toast } from "sonner";
import { useNavigate, Navigate } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";
import {
  ArrowLeft,
  Sparkles,
  PenLine,
  Upload,
  FileSpreadsheet,
  Loader2,
  CheckCircle2,
  ChevronDown,
} from "lucide-react";
import {
  Button,
  Card,
  Input,
  Select,
  Badge,
  Tabs,
  PageHero,
} from "@/components/ui";
import heroImg from "@/assets/images/heroes/hero-arch-blue-wave.jpg";

import { extractApiError } from "@/api/errors";
import { useCreateTransaction } from "@/modules/ma/hooks/useTransactions";
import {
  useDealSetupFromText,
  useDealSetupFromExcel,
  useConfirmDealSetup,
} from "@/modules/ma/hooks/useDealSetup";
import { koreanToEnglish } from "@/modules/ma/utils/koreanToEnglish";
import { formatKRW } from "@/modules/ma/utils/format";
import type {
  TransactionCreate,
  DealType,
  DealStructure,
  InvestmentType,
} from "@/modules/ma/types/transaction";
import type {
  DealSetupPreview,
  DealSetupConfirm,
} from "@/modules/ma/types/dealSetup";
import {
  CURRENCY_OPTIONS,
  DEAL_STRUCTURE_OPTIONS,
  INVESTMENT_TYPE_OPTIONS,
  DEAL_TYPE_OPTIONS,
  getDealTypeCodePrefix,
  getDealTypeLabel,
} from "@/modules/ma/constants";

// ── 상수 ──────────────────────────────────────────────────

const TAB_ITEMS = [
  { id: "manual", label: "수동 입력", icon: PenLine },
  { id: "ai", label: "AI 자동 설계", icon: Sparkles },
];

const INITIAL_MANUAL: TransactionCreate = {
  name: "Project ",
  deal_type: "SE",
  side: "SELL",
  target_company_name: "",
  client_name: "",
  lead_advisor_email: "",
};

function getSuffix(name: string): string {
  return name.startsWith("Project ") ? name.slice("Project ".length) : name;
}

function previewCode(dealType: DealType, name: string): string {
  const suffix = getSuffix(name).trim().slice(0, 3).toUpperCase();
  if (!suffix) return "";
  const yy = new Date().getFullYear().toString().slice(2);
  return `${getDealTypeCodePrefix(dealType)}${yy}-${suffix}-??`;
}

// ── 메인 컴포넌트 ────────────────────────────────────────

export default function DealSetupWizardPage() {
  const navigate = useNavigate();
  const { isClient } = useAuth();
  const [activeTab, setActiveTab] = useState("manual");

  if (isClient) return <Navigate to="/ma/transactions" replace />;

  return (
    <div className="space-y-6">
      <PageHero
        title="New Transaction"
        subtitle="새 M&A 거래 생성"
        backgroundImage={heroImg}
        backgroundOpacity={0.18}
        compact
      />

      <div className="max-w-3xl mx-auto">
        <Button
          variant="ghost"
          icon={ArrowLeft}
          onClick={() => navigate("/ma/transactions")}
          className="mb-4"
        >
          목록으로
        </Button>

        <Tabs
          tabs={TAB_ITEMS}
          activeTab={activeTab}
          onTabChange={setActiveTab}
          variant="pill"
          className="mb-6"
        />

        {activeTab === "manual" ? <ManualTab /> : <AITab />}
      </div>
    </div>
  );
}

// ── 수동 입력 탭 ─────────────────────────────────────────

function ManualTab() {
  const navigate = useNavigate();
  const createTxn = useCreateTransaction();
  const [form, setForm] = useState<TransactionCreate>(INITIAL_MANUAL);
  const [showOptional, setShowOptional] = useState(false);

  const set = <K extends keyof TransactionCreate>(
    key: K,
    val: TransactionCreate[K],
  ) => setForm((prev) => ({ ...prev, [key]: val }));

  const applyProjectName = (raw: string) => {
    const converted = koreanToEnglish(raw);
    const clean = converted.replace(/[^A-Za-z\s]/g, "");
    const capitalized =
      clean.length > 0 ? clean.charAt(0).toUpperCase() + clean.slice(1) : clean;
    set("name", `Project ${capitalized}`);
  };

  const suffix = getSuffix(form.name);
  const canSubmit =
    suffix.trim().length > 0 &&
    form.deal_type &&
    form.target_company_name.trim() &&
    form.client_name.trim() &&
    form.lead_advisor_email.trim() &&
    /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(form.lead_advisor_email.trim());

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!canSubmit) return;
    createTxn.mutate(form, {
      onSuccess: (txn) => navigate(`/ma/transactions/${txn.id}`),
    });
  };

  const preview = previewCode(form.deal_type, form.name);

  return (
    <Card title="기본 정보" headerBar>
      <form id="create-txn" onSubmit={handleSubmit} className="space-y-5 p-1">
        <fieldset className="space-y-4">
          <legend className="text-xs font-semibold uppercase tracking-wider text-text-muted mb-1">
            Required
          </legend>

          <Select
            label="딜 구조"
            options={DEAL_TYPE_OPTIONS}
            value={form.deal_type}
            onChange={(e) => set("deal_type", e.target.value as DealType)}
          />

          <div>
            <label className="block text-sm font-medium text-text-secondary mb-1.5">
              프로젝트명 <span className="text-destructive">*</span>
            </label>
            <div className="flex">
              <span className="inline-flex items-center px-3 rounded-l-md border border-r-0 border-border bg-surface-subtle text-sm font-medium text-text-muted select-none">
                Project
              </span>
              <input
                type="text"
                required
                className="flex-1 min-w-0 px-3 py-2 rounded-r-md border border-border bg-surface text-sm focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent"
                placeholder="Edward (한글 입력 시 자동 영문 변환)"
                value={suffix}
                onChange={(e) => {
                  applyProjectName(e.target.value);
                }}
              />
            </div>
            {preview && (
              <p className="mt-1.5 text-xs text-text-muted">
                예상 코드:{" "}
                <code className="font-mono font-semibold text-accent">
                  {preview}
                </code>
              </p>
            )}
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Input
              label="대상 기업"
              required
              value={form.target_company_name}
              onChange={(e) => set("target_company_name", e.target.value)}
              placeholder="인수/매각 대상 기업명"
            />
            <Input
              label="클라이언트"
              required
              value={form.client_name}
              onChange={(e) => set("client_name", e.target.value)}
              placeholder="의뢰인 명칭"
            />
          </div>

          <Input
            label="리드 어드바이저 이메일"
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
          {showOptional ? "옵션 접기" : "추가 정보 입력"}
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
              placeholder="8자리 기업 코드"
            />
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Select
                label="세부 거래 구조"
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
                label="투자 유형"
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
                label="예상 거래 금액"
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
                label="통화"
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
                label="산업"
                value={form.industry ?? ""}
                onChange={(e) => set("industry", e.target.value || undefined)}
                placeholder="산업 분류"
              />
              <Input
                label="목표 종결일"
                type="date"
                value={form.target_close_date ?? ""}
                onChange={(e) =>
                  set("target_close_date", e.target.value || undefined)
                }
              />
            </div>
            <Input
              label="딜 캡틴 이메일"
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
            취소
          </Button>
          <Button
            type="submit"
            disabled={!canSubmit}
            loading={createTxn.isPending}
          >
            거래 생성
          </Button>
        </div>
      </form>
    </Card>
  );
}

// ── AI 자동 설계 탭 ──────────────────────────────────────

function AITab() {
  const navigate = useNavigate();
  const setupFromText = useDealSetupFromText();
  const setupFromExcel = useDealSetupFromExcel();
  const confirmSetup = useConfirmDealSetup();

  const [inputMode, setInputMode] = useState<"text" | "excel">("text");
  const [description, setDescription] = useState("");
  const [leadEmail, setLeadEmail] = useState("");
  const [preview, setPreview] = useState<DealSetupPreview | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const isAnalyzing = setupFromText.isPending || setupFromExcel.isPending;

  const handleAnalyze = useCallback(() => {
    if (!leadEmail.trim() || !description.trim()) return;
    setupFromText.mutate(
      { description, lead_advisor_email: leadEmail },
      {
        onSuccess: (data) => setPreview(data),
        onError: (err) =>
          toast.error(
            extractApiError(err, "AI 분석에 실패했습니다. 다시 시도해 주세요."),
          ),
      },
    );
  }, [description, leadEmail, setupFromText]);

  const handleExcelUpload = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (!file) return;
      if (!leadEmail.trim()) {
        toast.error("리드 어드바이저 이메일을 먼저 입력해 주세요.");
        return;
      }
      setupFromExcel.mutate(file, {
        onSuccess: (data) => setPreview(data),
        onError: (err) =>
          toast.error(
            extractApiError(
              err,
              "엑셀 분석에 실패했습니다. 파일을 확인해 주세요.",
            ),
          ),
      });
    },
    [setupFromExcel, leadEmail],
  );

  const handleConfirm = useCallback(() => {
    if (!preview) return;
    const body: DealSetupConfirm = {
      transaction: preview.transaction,
      dd_checklist: preview.dd_checklist,
      timeline: preview.timeline,
      buyer_candidates: preview.buyer_candidates,
      lead_advisor_email: leadEmail,
    };
    confirmSetup.mutate(body, {
      onSuccess: (result) =>
        navigate(`/ma/transactions/${result.transaction_id}`),
      onError: (err) =>
        toast.error(
          extractApiError(err, "거래 생성에 실패했습니다. 다시 시도해 주세요."),
        ),
    });
  }, [preview, leadEmail, confirmSetup, navigate]);

  const handleReset = () => {
    setPreview(null);
    setupFromText.reset();
    setupFromExcel.reset();
  };

  // ── Step 2: 미리보기 ──────────────────────────────────
  if (preview) {
    const txn = preview.transaction;
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-text-primary">
            AI 분석 결과
          </h3>
          <div className="flex items-center gap-2 text-xs text-text-muted">
            <Badge variant="neutral">{preview.model_used}</Badge>
            <span>${preview.cost_usd.toFixed(4)}</span>
          </div>
        </div>

        {/* Transaction */}
        <Card title="거래 기본 정보" headerBar>
          <div className="grid grid-cols-2 gap-3 p-1 text-sm">
            <div>
              <span className="text-text-muted">프로젝트명</span>
              <p className="font-medium">{txn.name}</p>
            </div>
            <div>
              <span className="text-text-muted">딜 구조</span>
              <p className="font-medium">{getDealTypeLabel(txn.deal_type)}</p>
            </div>
            <div>
              <span className="text-text-muted">대상 기업</span>
              <p className="font-medium">{txn.target_company_name}</p>
            </div>
            <div>
              <span className="text-text-muted">클라이언트</span>
              <p className="font-medium">{txn.client_name}</p>
            </div>
            <div>
              <span className="text-text-muted">예상 거래 금액</span>
              <p className="font-medium">
                {formatKRW(txn.estimated_deal_value)}
              </p>
            </div>
            <div>
              <span className="text-text-muted">세부 거래 구조</span>
              <p className="font-medium">{txn.deal_structure ?? "-"}</p>
            </div>
            {txn.industry && (
              <div>
                <span className="text-text-muted">산업</span>
                <p className="font-medium">{txn.industry}</p>
              </div>
            )}
            {txn.target_close_date && (
              <div>
                <span className="text-text-muted">목표 종결일</span>
                <p className="font-medium">{txn.target_close_date}</p>
              </div>
            )}
          </div>
          {txn.notes && (
            <p className="text-xs text-text-muted mt-2 px-1 border-t pt-2">
              {txn.notes}
            </p>
          )}
        </Card>

        {/* DD Checklist */}
        <Card
          title={`DD 체크리스트 (${preview.dd_checklist.length}건)`}
          headerBar
        >
          <div className="divide-y divide-border">
            {preview.dd_checklist.map((item, i) => (
              <div key={i} className="py-2 px-1 flex items-start gap-3">
                <Badge variant="info" className="shrink-0 text-[10px]">
                  {item.workstream.replace(/^(FDD|LDD|TDD)_/, "$1 ")}
                </Badge>
                <div className="min-w-0">
                  <p className="text-sm font-medium text-text-primary">
                    {item.title}
                  </p>
                  {item.description && (
                    <p className="text-xs text-text-muted mt-0.5">
                      {item.description}
                    </p>
                  )}
                </div>
                {item.due_date && (
                  <span className="ml-auto text-xs text-text-muted shrink-0">
                    {item.due_date}
                  </span>
                )}
              </div>
            ))}
          </div>
        </Card>

        {/* Timeline */}
        <Card title={`타임라인 (${preview.timeline.length}건)`} headerBar>
          <div className="divide-y divide-border">
            {preview.timeline.map((item, i) => (
              <div key={i} className="py-2 px-1 flex items-center gap-3">
                <span className="text-xs text-text-muted shrink-0 w-24">
                  {item.event_date}
                </span>
                <p className="text-sm font-medium text-text-primary">
                  {item.title}
                </p>
              </div>
            ))}
          </div>
        </Card>

        {/* Buyers */}
        {preview.buyer_candidates.length > 0 && (
          <Card
            title={`매수 후보 (${preview.buyer_candidates.length}건)`}
            headerBar
          >
            <div className="divide-y divide-border">
              {preview.buyer_candidates.map((item, i) => (
                <div key={i} className="py-2 px-1 flex items-center gap-3">
                  <p className="text-sm font-medium text-text-primary">
                    {item.company_name}
                  </p>
                  {item.buyer_type && (
                    <Badge variant="neutral">{item.buyer_type}</Badge>
                  )}
                  {item.tier && <Badge variant="info">{item.tier}</Badge>}
                </div>
              ))}
            </div>
          </Card>
        )}

        {/* 액션 */}
        <div className="flex justify-end gap-3 pt-4 border-t">
          <Button variant="ghost" onClick={handleReset}>
            다시 분석
          </Button>
          <Button onClick={handleConfirm} loading={confirmSetup.isPending}>
            <CheckCircle2 size={16} className="mr-1.5" />
            확인 및 생성
          </Button>
        </div>
      </div>
    );
  }

  // ── Step 1: 입력 ──────────────────────────────────────
  return (
    <Card title="AI 딜 셋업" headerBar>
      <div className="space-y-5 p-1">
        <p className="text-sm text-text-muted">
          딜 설명을 자연어로 입력하거나, 딜 리스트 엑셀을 업로드하면 AI가 거래
          구조를 자동으로 설계합니다.
        </p>

        {/* 입력 모드 토글 */}
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => setInputMode("text")}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
              inputMode === "text"
                ? "bg-accent text-white"
                : "bg-surface-subtle text-text-secondary hover:bg-surface-hover"
            }`}
          >
            <PenLine size={14} />
            자연어 입력
          </button>
          <button
            type="button"
            onClick={() => setInputMode("excel")}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
              inputMode === "excel"
                ? "bg-accent text-white"
                : "bg-surface-subtle text-text-secondary hover:bg-surface-hover"
            }`}
          >
            <FileSpreadsheet size={14} />
            엑셀 업로드
          </button>
        </div>

        {/* 자연어 입력 */}
        {inputMode === "text" && (
          <div className="space-y-3">
            <textarea
              className="w-full h-40 px-3 py-2 rounded-md border border-border bg-surface text-sm focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent resize-y"
              placeholder={`예: "삼성전자 자회사 하만 매각 딜. 예상 거래금액 600억, Sell-side. 6개월 일정, FDD+LDD 필요. 매수 후보 3~5개사 타겟."`}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
            <p className="text-xs text-text-muted">
              딜 유형, 대상 기업, 거래 금액, 일정, 실사 범위, 매수 후보 등을
              자유롭게 기술해 주세요.
            </p>
          </div>
        )}

        {/* 엑셀 업로드 */}
        {inputMode === "excel" && (
          <div
            className="border-2 border-dashed border-border rounded-lg p-8 text-center hover:border-accent/50 transition-colors cursor-pointer"
            onClick={() => fileInputRef.current?.click()}
          >
            <Upload size={32} className="mx-auto mb-3 text-text-muted" />
            <p className="text-sm font-medium text-text-secondary mb-1">
              딜 리스트 엑셀 파일을 클릭하여 업로드
            </p>
            <p className="text-xs text-text-muted">.xlsx, .xls / 최대 10MB</p>
            <input
              ref={fileInputRef}
              type="file"
              accept=".xlsx,.xls"
              className="hidden"
              onChange={handleExcelUpload}
            />
          </div>
        )}

        {/* 리드 어드바이저 이메일 */}
        <Input
          label="리드 어드바이저 이메일"
          type="email"
          required
          value={leadEmail}
          onChange={(e) => setLeadEmail(e.target.value)}
          placeholder="advisor@company.com"
        />

        {/* 분석 버튼 */}
        {inputMode === "text" && (
          <div className="flex justify-end pt-2">
            <Button
              onClick={handleAnalyze}
              disabled={
                description.trim().length < 10 ||
                !leadEmail.trim() ||
                isAnalyzing
              }
              loading={isAnalyzing}
            >
              {isAnalyzing ? (
                <>
                  <Loader2 size={16} className="mr-1.5 animate-spin" />
                  AI 분석 중...
                </>
              ) : (
                <>
                  <Sparkles size={16} className="mr-1.5" />
                  AI 분석
                </>
              )}
            </Button>
          </div>
        )}

        {isAnalyzing && (
          <div className="flex items-center justify-center gap-2 py-6 text-sm text-text-muted">
            <Loader2 size={20} className="animate-spin text-accent" />
            AI가 딜 구조를 설계하고 있습니다...
          </div>
        )}
      </div>
    </Card>
  );
}

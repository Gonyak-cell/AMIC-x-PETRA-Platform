import { useState, useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import {
  ArrowLeft,
  ArrowRight,
  CheckCircle,
  Download,
  Loader2,
  AlertCircle,
  FileCheck,
  ShieldAlert,
  Brain,
  PenTool,
  FolderOpen,
} from "lucide-react";
import { toast } from "sonner";
import { Button, PageHero, Spinner } from "@/components/ui";
import { LDDSectionForm } from "@/modules/docs/components/LDDSectionForm";
import RalphLoopProgress from "@/modules/docs/components/RalphLoopProgress";
import {
  useCreateLDDReport,
  useCreateLDDReportAuto,
  useDefaultLDDSections,
  getLDDReportDownloadUrl,
} from "@/modules/docs/hooks/useLDDReports";
import type { LDDReportType, LDDSection } from "@/modules/docs/types/ldd_report";
import { LDD_REPORT_TYPE_LABELS } from "@/modules/docs/types/ldd_report";
import { useTransaction } from "@/modules/ma/hooks/useTransactions";
import heroImg from "@/assets/images/heroes/hero-arch-white-round.jpg";

// ── Step 인디케이터 ───────────────────────────────────────────────────────────

function StepIndicator({ step }: { step: number }) {
  const steps = ["기본 정보", "체크리스트 작성", "확인 및 생성"];
  return (
    <ol className="flex items-center gap-2 list-none p-0 m-0" aria-label="LDD 보고서 생성 단계">
      {steps.map((label, i) => (
        <li key={i} className="flex items-center gap-2" aria-current={i === step ? "step" : undefined}>
          <div className="flex items-center gap-1.5">
            <div
              className={`flex h-6 w-6 items-center justify-center rounded-full text-xs font-medium ${
                i < step
                  ? "bg-accent-primary text-white"
                  : i === step
                    ? "bg-accent-primary text-white"
                    : "bg-white-elevated text-text-tertiary"
              }`}
            >
              {i < step ? <CheckCircle className="h-3.5 w-3.5" /> : i + 1}
            </div>
            <span
              className={`hidden text-xs sm:inline ${
                i === step ? "font-medium text-text-primary" : "text-text-tertiary"
              }`}
            >
              {label}
            </span>
          </div>
          {i < steps.length - 1 && (
            <div className={`h-px w-8 ${i < step ? "bg-accent-primary" : "bg-border"}`} />
          )}
        </li>
      ))}
    </ol>
  );
}

// ── 메인 페이지 ───────────────────────────────────────────────────────────────

type Mode = "select" | "manual" | "ai";

export default function CreateLDDReportPage() {
  const navigate      = useNavigate();
  const [searchParams] = useSearchParams();

  const txnId      = searchParams.get("txn_id") ?? "";
  const typeParam  = (searchParams.get("type") as LDDReportType | null) ?? "FULL";

  const [mode, setMode]             = useState<Mode>("select");
  const [step, setStep]             = useState<0 | 1 | 2>(0);
  const [reportType, setReportType] = useState<LDDReportType>(typeParam);
  const [title, setTitle]           = useState("");
  const [targetCompany, setTargetCompany] = useState("");
  const [ddPeriod, setDdPeriod]     = useState("");
  const [lawFirm, setLawFirm]       = useState("");
  const [preparedBy, setPreparedBy] = useState("");
  const [sections, setSections]     = useState<LDDSection[]>([]);

  // AI 모드 상태
  const [sourceDir, setSourceDir]   = useState("");
  const [aiStep, setAiStep]         = useState<"input" | "running" | "done">("input");

  // 생성 결과
  const [createdId,     setCreatedId]     = useState<string | null>(null);
  const [createdStatus, setCreatedStatus] = useState<string | null>(null);
  const [createdError,  setCreatedError]  = useState<string | null>(null);

  // 기존 데이터 로드
  const { data: txn } = useTransaction(txnId);
  const { data: defaultSections, isLoading: isLoadingSections } = useDefaultLDDSections();

  // 자동 채우기
  useEffect(() => {
    if (!txn) return;
    if (txn.target_company_name && !targetCompany) setTargetCompany(txn.target_company_name);
    if (txn.name && !title) {
      const typeLabel = LDD_REPORT_TYPE_LABELS[reportType];
      setTitle(`[${typeLabel}] ${txn.target_company_name ?? txn.name} 법률실사보고서`);
    }
  }, [txn]);

  useEffect(() => {
    if (defaultSections && sections.length === 0) {
      setSections(defaultSections);
    }
  }, [defaultSections]);

  const createMut = useCreateLDDReport(txnId);
  const createAutoMut = useCreateLDDReportAuto(txnId);

  const handleBack = () => {
    if (step === 1) setStep(0);
    else if (step === 2) setStep(1);
  };

  const handleToStep1 = () => {
    if (!title.trim() || !txnId) return;
    setStep(1);
  };

  const handleToConfirm = () => {
    const invalid = sections.flatMap((s) =>
      s.items.filter((item) => item.status === "ISSUE" && !item.issue_level),
    );
    if (invalid.length > 0) {
      toast.error(
        `ISSUE 항목 ${invalid.length}건의 이슈 등급이 미선택입니다. (${invalid.map((i) => i.item_id || i.name).join(", ")})`,
      );
      return;
    }
    setStep(2);
  };

  const handleGenerate = async () => {
    if (!txnId) return;
    try {
      const report = await createMut.mutateAsync({
        title:          title.trim(),
        report_type:    reportType,
        target_company: targetCompany.trim() || undefined,
        dd_period:      ddPeriod.trim() || undefined,
        law_firm:       lawFirm.trim() || undefined,
        prepared_by:    preparedBy.trim() || undefined,
        sections:       sections.length > 0 ? sections : undefined,
      });
      setCreatedId(report.id);
      setCreatedStatus(report.status);
      if (report.error_message) setCreatedError(report.error_message);
    } catch {
      // 에러는 useMutation onError에서 toast 처리
    }
  };

  const handleDone = () => {
    if (txnId) {
      navigate(`/ma/transactions/${txnId}?tab=ldd`);
    } else {
      navigate("/docs");
    }
  };

  const handleAiGenerate = async () => {
    if (!txnId || !sourceDir.trim()) return;
    setAiStep("running");
    try {
      const report = await createAutoMut.mutateAsync({
        title: title.trim() || `[AI 자동 분석] ${targetCompany || "대상회사"} 법률실사보고서`,
        report_type: reportType,
        source_dir: sourceDir.trim(),
        target_company: targetCompany.trim() || undefined,
        dd_period: ddPeriod.trim() || undefined,
        law_firm: lawFirm.trim() || undefined,
        prepared_by: preparedBy.trim() || undefined,
        max_iterations: 3,
        max_cost_usd: 10.0,
      });
      setCreatedId(report.id);
      setCreatedStatus(report.status);
      if (report.error_message) setCreatedError(report.error_message);
      setAiStep("done");
    } catch {
      setAiStep("input");
    }
  };

  // 이슈 카운트 계산 (미리보기용)
  const issueCount = sections.reduce(
    (acc, sec) => acc + sec.items.filter((i) => i.status === "ISSUE").length,
    0
  );
  const criticalCount = sections.reduce(
    (acc, sec) =>
      acc + sec.items.filter((i) => i.status === "ISSUE" && i.issue_level === "CRITICAL").length,
    0
  );

  return (
    <div className="space-y-6">
      <PageHero
        title="LDD 보고서 생성"
        subtitle="DDRL 체크리스트를 기반으로 법률실사보고서 .docx를 자동 생성합니다"
        backgroundImage={heroImg}
        backgroundOpacity={0.18}
        compact
        actions={
          <Button variant="ghost" icon={ArrowLeft} onClick={() => navigate(-1)}>
            뒤로
          </Button>
        }
      />

      {/* ── 모드 선택 ── */}
      {mode === "select" && (
        <div className="space-y-5">
          <div className="rounded-xl border border-border bg-white p-5 space-y-4">
            <h2 className="text-sm font-semibold text-text-primary">작성 방법 선택</h2>
            <p className="text-xs text-text-secondary">
              DDRL 체크리스트를 직접 작성하거나, 실사자료를 AI가 자동 분석하여 보고서를 생성할 수 있습니다.
            </p>
            <div className="grid grid-cols-2 gap-4">
              <button
                type="button"
                onClick={() => setMode("manual")}
                className="flex flex-col items-center gap-3 rounded-xl border-2 border-border p-6 text-center transition-all hover:border-accent-primary hover:bg-accent-primary/5"
              >
                <div className="flex h-12 w-12 items-center justify-center rounded-full bg-white-elevated">
                  <PenTool className="h-6 w-6 text-text-secondary" />
                </div>
                <div>
                  <p className="text-sm font-semibold text-text-primary">수동 작성</p>
                  <p className="text-xs text-text-tertiary mt-1">
                    DDRL 체크리스트를 항목별로 직접 검토하고 이슈를 기재합니다
                  </p>
                </div>
              </button>
              <button
                type="button"
                onClick={() => setMode("ai")}
                className="flex flex-col items-center gap-3 rounded-xl border-2 border-border p-6 text-center transition-all hover:border-emerald-500 hover:bg-emerald-50"
              >
                <div className="flex h-12 w-12 items-center justify-center rounded-full bg-emerald-100">
                  <Brain className="h-6 w-6 text-emerald-600" />
                </div>
                <div>
                  <p className="text-sm font-semibold text-text-primary">AI 자동 분석</p>
                  <p className="text-xs text-text-tertiary mt-1">
                    실사자료 폴더를 지정하면 AI가 52개 항목을 자동 분석합니다
                  </p>
                </div>
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-700 font-medium">
                  Ralph Loop
                </span>
              </button>
            </div>
          </div>

          {!txnId && (
            <div className="flex items-center gap-2 rounded-lg border border-yellow-200 bg-yellow-50 px-4 py-3 text-sm text-yellow-700">
              <AlertCircle className="h-4 w-4 flex-shrink-0" />
              <span>거래(Transaction)가 선택되지 않았습니다.</span>
            </div>
          )}
        </div>
      )}

      {/* ── AI 모드 ── */}
      {mode === "ai" && (
        <div className="space-y-5">
          {aiStep === "input" && (
            <div className="space-y-5">
              <div className="rounded-xl border border-border bg-white p-5 space-y-4">
                <h2 className="text-sm font-semibold text-text-primary flex items-center gap-2">
                  <Brain className="h-4 w-4 text-emerald-600" />
                  AI 자동 분석 설정
                </h2>

                {/* 보고서 유형 */}
                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-text-secondary">보고서 유형</label>
                  <div className="flex gap-3">
                    {(["FULL", "REDFLAG"] as LDDReportType[]).map((type) => (
                      <button
                        key={type}
                        type="button"
                        onClick={() => setReportType(type)}
                        className={`flex-1 rounded-lg border px-3 py-2 text-sm font-medium transition-all ${
                          reportType === type
                            ? "border-accent-primary bg-accent-primary/5 text-accent-primary"
                            : "border-border text-text-secondary hover:border-foreground/30"
                        }`}
                      >
                        {LDD_REPORT_TYPE_LABELS[type]}
                      </button>
                    ))}
                  </div>
                </div>

                {/* 실사자료 경로 */}
                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-text-secondary">
                    실사자료 폴더 경로 <span className="text-negative">*</span>
                  </label>
                  <div className="flex gap-2">
                    <div className="relative flex-1">
                      <FolderOpen className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-text-tertiary" />
                      <input
                        value={sourceDir}
                        onChange={(e) => setSourceDir(e.target.value)}
                        placeholder="/data/dd-materials/project-green"
                        className="w-full rounded-lg border border-border bg-white pl-9 pr-3 py-2 text-sm focus:border-accent-primary focus:outline-none focus:ring-1 focus:ring-accent-primary"
                      />
                    </div>
                  </div>
                  <p className="text-[11px] text-text-tertiary">
                    Excel, PDF, DOCX, HWP 파일이 포함된 실사자료 폴더 경로를 입력하세요
                  </p>
                </div>

                {/* 기본 정보 (축약) */}
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <label className="text-xs font-medium text-text-secondary">대상회사</label>
                    <input
                      value={targetCompany}
                      onChange={(e) => setTargetCompany(e.target.value)}
                      placeholder="(주)대상회사"
                      className="w-full rounded-lg border border-border bg-white px-3 py-1.5 text-sm focus:border-accent-primary focus:outline-none"
                    />
                  </div>
                  <div className="space-y-1">
                    <label className="text-xs font-medium text-text-secondary">법무법인</label>
                    <input
                      value={lawFirm}
                      onChange={(e) => setLawFirm(e.target.value)}
                      placeholder="법무법인 ○○"
                      className="w-full rounded-lg border border-border bg-white px-3 py-1.5 text-sm focus:border-accent-primary focus:outline-none"
                    />
                  </div>
                </div>
              </div>

              <div className="flex justify-between">
                <Button variant="ghost" icon={ArrowLeft} onClick={() => setMode("select")}>
                  돌아가기
                </Button>
                <Button
                  icon={Brain}
                  onClick={handleAiGenerate}
                  loading={createAutoMut.isPending}
                  disabled={!sourceDir.trim() || !txnId || createAutoMut.isPending}
                  className="bg-emerald-600 hover:bg-emerald-700 text-white"
                >
                  {createAutoMut.isPending ? "분석 중..." : "AI 자동 분석 시작"}
                </Button>
              </div>
            </div>
          )}

          {aiStep === "running" && (
            <div className="space-y-4 py-6">
              <div className="flex flex-col items-center gap-3 text-center">
                <Loader2 className="h-8 w-8 animate-spin text-emerald-600" />
                <div>
                  <p className="text-sm font-medium text-text-primary">Ralph Loop AI 분석 진행 중...</p>
                  <p className="text-xs text-text-tertiary mt-1">
                    실사자료를 파싱하고 52개 DDRL 항목을 자동 분석합니다
                  </p>
                </div>
              </div>
              {createdId && (
                <RalphLoopProgress sessionId={createdId} />
              )}
            </div>
          )}

          {aiStep === "done" && createdId && createdStatus === "READY" && (
            <div className="flex flex-col items-center gap-4 py-10 text-center">
              <div className="flex h-16 w-16 items-center justify-center rounded-full bg-emerald-100">
                <CheckCircle className="h-8 w-8 text-emerald-600" />
              </div>
              <div>
                <p className="text-base font-semibold text-text-primary">AI 자동 분석 완료</p>
                <p className="text-sm text-text-secondary">Ralph Loop이 실사자료를 분석하여 LDD 보고서를 생성했습니다</p>
              </div>
              <div className="flex gap-3">
                <a
                  href={getLDDReportDownloadUrl(txnId, createdId)}
                  download={`LDD_AI_${createdId}.docx`}
                  className="flex items-center gap-1.5 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700"
                >
                  <Download className="h-4 w-4" />
                  다운로드 (.docx)
                </a>
                <Button variant="ghost" onClick={handleDone}>
                  완료
                </Button>
              </div>
            </div>
          )}

          {aiStep === "done" && createdId && createdStatus === "FAILED" && (
            <div className="flex flex-col items-center gap-4 py-10 text-center">
              <div className="flex h-16 w-16 items-center justify-center rounded-full bg-negative-light">
                <AlertCircle className="h-8 w-8 text-negative" />
              </div>
              <div>
                <p className="text-base font-semibold text-text-primary">AI 분석 실패</p>
                {createdError && <p className="text-sm text-text-secondary max-w-md">{createdError}</p>}
              </div>
              <Button icon={ArrowLeft} onClick={() => { setAiStep("input"); setCreatedId(null); }}>
                다시 시도
              </Button>
            </div>
          )}
        </div>
      )}

      {/* Step 인디케이터 (수동 모드에서만) */}
      {mode === "manual" && (
        <div className="px-1">
          <StepIndicator step={step} />
        </div>
      )}

      {/* ── Step 0: 기본 정보 (수동 모드) ── */}
      {mode === "manual" && step === 0 && (
        <div className="space-y-5">
          <div className="rounded-xl border border-border bg-white p-5 space-y-4">
            <h2 className="text-sm font-semibold text-text-primary">보고서 기본 정보</h2>

            {/* 보고서 유형 */}
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-text-secondary">
                보고서 유형 <span className="text-negative">*</span>
              </label>
              <div className="flex gap-3">
                {(["FULL", "REDFLAG"] as LDDReportType[]).map((type) => (
                  <button
                    key={type}
                    type="button"
                    onClick={() => setReportType(type)}
                    className={`flex-1 rounded-lg border px-4 py-3 text-sm font-medium transition-all ${
                      reportType === type
                        ? type === "REDFLAG"
                          ? "border-red-400 bg-negative-light text-negative"
                          : "border-accent-primary bg-accent-primary/5 text-accent-primary"
                        : "border-border text-text-secondary hover:border-foreground/30"
                    }`}
                  >
                    <div className="flex items-center justify-center gap-2">
                      {type === "REDFLAG" && <ShieldAlert className="h-4 w-4" />}
                      <span>{LDD_REPORT_TYPE_LABELS[type]}</span>
                    </div>
                    <p className="mt-1 text-xs font-normal text-text-tertiary">
                      {type === "FULL"
                        ? "10개 섹션 전체 보고서 (기재례 표준)"
                        : "Executive Summary + Red/Amber 이슈만 (Lucid KR 형식)"}
                    </p>
                  </button>
                ))}
              </div>
            </div>

            {/* 보고서 제목 */}
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-text-secondary">
                보고서 제목 <span className="text-negative">*</span>
              </label>
              <input
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="예: [정식 LDD] (주)대상회사 법률실사보고서"
                className="w-full rounded-lg border border-border bg-white px-3 py-2 text-sm focus:border-accent-primary focus:outline-none focus:ring-1 focus:ring-accent-primary"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              {/* 대상회사 */}
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-text-secondary">대상회사</label>
                <input
                  value={targetCompany}
                  onChange={(e) => setTargetCompany(e.target.value)}
                  placeholder="(주)대상회사"
                  className="w-full rounded-lg border border-border bg-white px-3 py-2 text-sm focus:border-accent-primary focus:outline-none focus:ring-1 focus:ring-accent-primary"
                />
              </div>

              {/* 실사기간 */}
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-text-secondary">실사기간</label>
                <input
                  value={ddPeriod}
                  onChange={(e) => setDdPeriod(e.target.value)}
                  placeholder="2026-03-01 ~ 2026-03-31"
                  className="w-full rounded-lg border border-border bg-white px-3 py-2 text-sm focus:border-accent-primary focus:outline-none focus:ring-1 focus:ring-accent-primary"
                />
              </div>

              {/* 법무법인 */}
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-text-secondary">법무법인</label>
                <input
                  value={lawFirm}
                  onChange={(e) => setLawFirm(e.target.value)}
                  placeholder="법무법인 ○○"
                  className="w-full rounded-lg border border-border bg-white px-3 py-2 text-sm focus:border-accent-primary focus:outline-none focus:ring-1 focus:ring-accent-primary"
                />
              </div>

              {/* 담당변호사 */}
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-text-secondary">담당변호사</label>
                <input
                  value={preparedBy}
                  onChange={(e) => setPreparedBy(e.target.value)}
                  placeholder="홍길동 변호사"
                  className="w-full rounded-lg border border-border bg-white px-3 py-2 text-sm focus:border-accent-primary focus:outline-none focus:ring-1 focus:ring-accent-primary"
                />
              </div>
            </div>
          </div>

          {!txnId && (
            <div className="flex items-center gap-2 rounded-lg border border-yellow-200 bg-yellow-50 px-4 py-3 text-sm text-yellow-700">
              <AlertCircle className="h-4 w-4 flex-shrink-0" />
              <span>거래(Transaction)가 선택되지 않았습니다. 보고서를 저장하려면 거래가 필요합니다.</span>
            </div>
          )}

          <div className="flex justify-end">
            <Button
              icon={ArrowRight}
              iconPosition="right"
              onClick={handleToStep1}
              disabled={!title.trim() || !txnId}
            >
              체크리스트 작성
            </Button>
          </div>
        </div>
      )}

      {/* ── Step 1: 체크리스트 작성 (수동 모드) ── */}
      {mode === "manual" && step === 1 && (
        <div className="space-y-5">
          {isLoadingSections ? (
            <div className="flex h-40 items-center justify-center">
              <Spinner />
            </div>
          ) : (
            <>
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-sm font-semibold text-text-primary">
                    DDRL 체크리스트 ({sections.length}개 섹션)
                  </h2>
                  <p className="text-xs text-text-secondary">
                    각 항목의 검토 결과를 입력하세요. ISSUE 선택 시 이슈 등급과 발견사항을 필수 기재하세요.
                  </p>
                </div>
                {issueCount > 0 && (
                  <div className="flex gap-2">
                    {criticalCount > 0 && (
                      <span className="text-xs px-2 py-1 rounded-full bg-negative-light text-negative font-medium">
                        Critical {criticalCount}
                      </span>
                    )}
                    <span className="text-xs px-2 py-1 rounded-full bg-caution-light text-amber-700 font-medium">
                      이슈 총 {issueCount}건
                    </span>
                  </div>
                )}
              </div>

              <LDDSectionForm sections={sections} onChange={setSections} />

              <div className="flex justify-between">
                <Button variant="ghost" icon={ArrowLeft} onClick={handleBack}>
                  기본 정보 수정
                </Button>
                <Button icon={ArrowRight} iconPosition="right" onClick={handleToConfirm}>
                  확인 및 생성
                </Button>
              </div>
            </>
          )}
        </div>
      )}

      {/* ── Step 2: 확인 및 생성 (수동 모드) ── */}
      {mode === "manual" && step === 2 && (
        <div className="space-y-6">
          {/* 생성 전 요약 */}
          {!createdId && (
            <>
              <div className="rounded-xl border border-border bg-white p-5 space-y-3">
                <h3 className="text-sm font-semibold text-text-primary">생성 정보 확인</h3>
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div>
                    <p className="text-xs text-text-tertiary">보고서 유형</p>
                    <p className="font-medium text-text-primary">
                      {LDD_REPORT_TYPE_LABELS[reportType]}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-text-tertiary">보고서 제목</p>
                    <p className="font-medium text-text-primary">{title}</p>
                  </div>
                  {targetCompany && (
                    <div>
                      <p className="text-xs text-text-tertiary">대상회사</p>
                      <p className="font-medium text-text-primary">{targetCompany}</p>
                    </div>
                  )}
                  {ddPeriod && (
                    <div>
                      <p className="text-xs text-text-tertiary">실사기간</p>
                      <p className="font-medium text-text-primary">{ddPeriod}</p>
                    </div>
                  )}
                  {lawFirm && (
                    <div>
                      <p className="text-xs text-text-tertiary">법무법인</p>
                      <p className="font-medium text-text-primary">{lawFirm}</p>
                    </div>
                  )}
                  {preparedBy && (
                    <div>
                      <p className="text-xs text-text-tertiary">담당변호사</p>
                      <p className="font-medium text-text-primary">{preparedBy}</p>
                    </div>
                  )}
                </div>

                {/* 체크리스트 요약 */}
                <div className="border-t border-border pt-3">
                  <p className="text-xs text-text-tertiary mb-2">체크리스트 요약</p>
                  <div className="grid grid-cols-4 gap-2">
                    {[
                      { label: "전체", value: sections.reduce((a, s) => a + s.items.length, 0), color: "text-text-primary" },
                      { label: "이슈", value: issueCount, color: "text-negative" },
                      {
                        label: "미검토",
                        value: sections.reduce((a, s) => a + s.items.filter((i) => i.status === "PENDING").length, 0),
                        color: "text-yellow-600",
                      },
                      {
                        label: "이상없음",
                        value: sections.reduce((a, s) => a + s.items.filter((i) => i.status === "OK").length, 0),
                        color: "text-positive",
                      },
                    ].map(({ label, value, color }) => (
                      <div key={label} className="rounded-lg border border-border p-2.5 text-center">
                        <p className={`text-lg font-bold ${color}`}>{value}</p>
                        <p className="text-xs text-text-tertiary">{label}</p>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              <div className="flex justify-between">
                <Button variant="ghost" icon={ArrowLeft} onClick={handleBack}>
                  수정
                </Button>
                <Button
                  icon={FileCheck}
                  onClick={handleGenerate}
                  loading={createMut.isPending}
                  disabled={createMut.isPending || !txnId}
                >
                  {createMut.isPending ? "생성 중..." : "보고서 생성"}
                </Button>
              </div>
            </>
          )}

          {/* 생성 중 */}
          {createMut.isPending && (
            <div className="flex flex-col items-center gap-3 py-10 text-center">
              <Loader2 className="h-10 w-10 animate-spin text-accent-primary" />
              <p className="text-sm font-medium text-text-primary">LDD 보고서를 생성하고 있습니다...</p>
              <p className="text-xs text-text-tertiary">잠시 기다려 주세요</p>
            </div>
          )}

          {/* 생성 완료 — READY */}
          {createdId && createdStatus === "READY" && (
            <div className="flex flex-col items-center gap-4 py-10 text-center">
              <div className="flex h-16 w-16 items-center justify-center rounded-full bg-emerald-100">
                <CheckCircle className="h-8 w-8 text-emerald-600" />
              </div>
              <div>
                <p className="text-base font-semibold text-text-primary">LDD 보고서 생성 완료</p>
                <p className="text-sm text-text-secondary">{title}</p>
                {issueCount > 0 && (
                  <p className="text-xs text-text-tertiary mt-1">
                    이슈 {issueCount}건 발견 (Critical: {criticalCount}건)
                  </p>
                )}
              </div>
              <div className="flex gap-3">
                <a
                  href={getLDDReportDownloadUrl(txnId, createdId)}
                  download={`LDD_${createdId}.docx`}
                  className="flex items-center gap-1.5 rounded-lg bg-accent-primary px-4 py-2 text-sm font-medium text-white hover:bg-accent-primary/90"
                >
                  <Download className="h-4 w-4" />
                  다운로드 (.docx)
                </a>
                <Button variant="ghost" onClick={handleDone}>
                  완료
                </Button>
              </div>
            </div>
          )}

          {/* 생성 실패 — FAILED */}
          {createdId && createdStatus === "FAILED" && (
            <div className="flex flex-col items-center gap-4 py-10 text-center">
              <div className="flex h-16 w-16 items-center justify-center rounded-full bg-negative-light">
                <AlertCircle className="h-8 w-8 text-negative" />
              </div>
              <div>
                <p className="text-base font-semibold text-text-primary">보고서 생성 실패</p>
                {createdError && (
                  <p className="text-sm text-text-secondary max-w-md">{createdError}</p>
                )}
              </div>
              <div className="flex gap-3">
                <Button
                  icon={ArrowLeft}
                  onClick={() => {
                    setCreatedId(null);
                    setCreatedStatus(null);
                    setCreatedError(null);
                  }}
                >
                  다시 시도
                </Button>
                <Button variant="ghost" onClick={handleDone}>
                  닫기
                </Button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/** SPA 계약서 LLM 역분석 위저드 — 4단계 */

import { useCallback, useEffect, useRef, useState } from "react";
import {
  AlertCircle,
  ArrowLeft,
  ArrowRight,
  ChevronRight,
  Loader2,
  RefreshCw,
  Sparkles,
} from "lucide-react";
import { toast } from "sonner";
import { useNavigate } from "react-router-dom";
import { useSpaStep1, useSpaStep2, useSpaStep3 } from "../hooks/useSpaAnalysis";
import type {
  AllStructureType,
  ExtractedVariable,
  AnalyzedClause,
  DocType,
  IndustryType,
  ShaType,
  ExitStrategy,
  BtaScope,
  SeverancePayHandling,
  SsaSecurityType,
  SsaTransactionContext,
  MouTransactionType,
  MouDepositHandling,
  SpaStep1Response,
  SpaStep2Response,
} from "../types/spa_analysis";
import {
  DOC_TYPES,
  DOC_TYPE_LABELS,
  DEAL_STRUCTURES,
  DEAL_STRUCTURE_LABELS,
  INDUSTRY_TYPE_LABELS,
  SHA_TYPES,
  SHA_TYPE_LABELS,
  EXIT_STRATEGY_LABELS,
  BTA_SCOPES,
  BTA_SCOPE_LABELS,
  SEVERANCE_PAY_LABELS,
  SSA_SECURITY_TYPES,
  SSA_SECURITY_TYPE_LABELS,
  SSA_TRANSACTION_CONTEXT_LABELS,
  MOU_TRANSACTION_TYPES,
  MOU_TRANSACTION_TYPE_LABELS,
  MOU_DEPOSIT_HANDLING_LABELS,
} from "../types/spa_analysis";
import SpaTextInput from "./SpaTextInput";
import {
  VariableReviewPanel,
  ClauseReviewPanel,
  ShaClassificationPanel,
  BtaClassificationPanel,
  SsaClassificationPanel,
  MouClassificationPanel,
} from "./AnalysisReviewPanel";

interface SpaAnalysisWizardProps {
  txnId: string;
}

const STEP_LABELS = ["원문 입력", "변수 확인", "조항 확인", "템플릿 생성"];

/** LLM 분석 중 표시할 오버레이 */
function AnalysisOverlay({ message }: { message: string }) {
  return (
    <div className="flex flex-col items-center gap-3 rounded-xl border border-border bg-white p-8 text-center">
      <Loader2 className="h-8 w-8 animate-spin text-accent-primary" />
      <p className="text-sm font-medium text-text-primary">{message}</p>
      <p className="text-xs text-text-tertiary">
        LLM 분석은 10~30초 소요됩니다
      </p>
    </div>
  );
}

export default function SpaAnalysisWizard({ txnId }: SpaAnalysisWizardProps) {
  const navigate = useNavigate();
  const [step, setStep] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);

  // P3-2: Step 0 텍스트 보존 (실패 시 입력 유지)
  const [preservedText, setPreservedText] = useState("");

  // Step 1 결과
  const [sessionId, setSessionId] = useState("");
  const [variables, setVariables] = useState<ExtractedVariable[]>([]);
  const [dealStructure, setDealStructure] = useState<AllStructureType>(
    "PURE_SHARE_TRANSFER",
  );
  const [industryType, setIndustryType] = useState<IndustryType>("GENERAL");
  const [docType, setDocType] = useState<DocType>("SPA");
  // SHA 전용 상태
  const [exitStrategy, setExitStrategy] =
    useState<ExitStrategy>("OTHER_STRATEGY");
  // BTA 전용 상태
  const [severancePayHandling, setSeverancePayHandling] =
    useState<SeverancePayHandling>("OTHER_METHOD");
  // SSA 전용 상태
  const [securityType, setSecurityType] =
    useState<SsaSecurityType>("OTHER_SECURITY");
  const [transactionContext, setTransactionContext] =
    useState<SsaTransactionContext>("OTHER_CONTEXT");
  // MOU 전용 상태
  const [mouTransactionType, setMouTransactionType] =
    useState<MouTransactionType>("OTHER_MOU_TYPE");
  const [depositHandling, setDepositHandling] =
    useState<MouDepositHandling>("NO_DEPOSIT");

  // Step 2 결과
  const [clauses, setClauses] = useState<AnalyzedClause[]>([]);

  // Step 3 입력
  const [templateName, setTemplateName] = useState("");
  const [templateDesc, setTemplateDesc] = useState("");

  // API 훅
  const step1Mut = useSpaStep1(txnId);
  const step2Mut = useSpaStep2(txnId);
  const step3Mut = useSpaStep3(txnId);

  // 스텝 전환 시 스크롤 + 포커스
  useEffect(() => {
    const heading = containerRef.current?.querySelector<HTMLElement>("h2, h3");
    if (heading) {
      heading.setAttribute("tabindex", "-1");
      heading.focus();
    }
    containerRef.current?.scrollIntoView({
      behavior: "smooth",
      block: "start",
    });
  }, [step]);

  // E-2: 분석 진행 중 브라우저 뒤로가기/새로고침 경고
  useEffect(() => {
    if (step === 0) return;
    const handler = (e: BeforeUnloadEvent) => {
      e.preventDefault();
    };
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }, [step]);

  // Step 0 → 1: 변수 추출
  const handleStep1Submit = useCallback(
    async (
      text: string,
      languageHint: "ko" | "en" | null,
      docTypeHint: DocType | null,
    ) => {
      setPreservedText(text); // P3-2: 텍스트 보존
      try {
        const result: SpaStep1Response = await step1Mut.mutateAsync({
          spa_text: text,
          language_hint: languageHint,
          doc_type_hint: docTypeHint,
        });
        setSessionId(result.session_id);

        // A-2: discovered_booleans를 BOOLEAN 변수로 병합 (Jinja2 UndefinedError 방지)
        const mergedVars = [...result.variables];
        for (const db of result.discovered_booleans ?? []) {
          if (!mergedVars.some((v) => v.variable_key === db.variable_key)) {
            mergedVars.push({
              variable_key: db.variable_key,
              input_type: "BOOLEAN",
              question_label: db.question_label,
              description: db.detected_in_clause
                ? `발견 조항: ${db.detected_in_clause}`
                : null,
              extracted_value: "true",
              default_value: "true",
              is_required: false,
              select_options: null,
              display_order: mergedVars.length,
              group_name: "자동 발견 조항",
              visible_condition: null,
              confidence: 0.8,
            });
          }
        }
        setVariables(mergedVars);
        // 문서 유형별 deal_structure 매핑
        if (result.detected_doc_type === "SHA") {
          setDealStructure(result.sha_type ?? result.deal_structure);
        } else if (result.detected_doc_type === "BTA") {
          setDealStructure(result.bta_scope ?? result.deal_structure);
          setSeverancePayHandling(
            result.severance_pay_handling ?? "OTHER_METHOD",
          );
        } else if (result.detected_doc_type === "SSA") {
          setDealStructure(result.security_type ?? result.deal_structure);
          setSecurityType(result.security_type ?? "OTHER_SECURITY");
          setTransactionContext(result.transaction_context ?? "OTHER_CONTEXT");
        } else if (result.detected_doc_type === "MOU") {
          setDealStructure(
            result.mou_transaction_type ?? result.deal_structure,
          );
          setMouTransactionType(
            result.mou_transaction_type ?? "OTHER_MOU_TYPE",
          );
          setDepositHandling(result.deposit_handling ?? "NO_DEPOSIT");
        } else {
          setDealStructure(result.deal_structure);
        }
        setIndustryType(result.industry_type);
        setDocType(result.detected_doc_type ?? "SPA");
        setExitStrategy(result.exit_strategy ?? "OTHER_STRATEGY");
        setTemplateName("");
        setStep(1);
      } catch {
        // onError 토스트가 이미 표시됨 — unhandled rejection 방지
      }
    },
    [step1Mut],
  );

  // Step 1 → 2: 조항 분해
  const handleStep2Submit = useCallback(async () => {
    try {
      const result: SpaStep2Response = await step2Mut.mutateAsync({
        session_id: sessionId,
        spa_text: preservedText || undefined,
        doc_type_hint: docType !== "SPA" ? docType : undefined,
        variables,
        deal_structure: dealStructure,
        industry_type: industryType,
      });
      setClauses(result.clauses);
      setStep(2);
    } catch {
      // onError 토스트가 이미 표시됨 — unhandled rejection 방지
    }
  }, [
    step2Mut,
    sessionId,
    preservedText,
    docType,
    variables,
    dealStructure,
    industryType,
  ]);

  // Step 2 → 3: 생성 입력
  const handleGoToStep3 = useCallback(() => {
    if (clauses.length === 0) {
      toast.error("최소 1개 이상의 조항이 필요합니다.");
      return;
    }
    setStep(3);
  }, [clauses]);

  // Step 3: 템플릿 생성
  const handleCreateTemplate = useCallback(async () => {
    if (!templateName.trim()) {
      toast.error("템플릿 이름을 입력하세요.");
      return;
    }
    try {
      const result = await step3Mut.mutateAsync({
        session_id: sessionId,
        template_name: templateName.trim(),
        template_description: templateDesc.trim() || null,
        doc_type: docType,
        variables,
        clauses,
      });
      toast.success(result.message);
      // 생성 완료 → 계약서 생성 페이지로 이동 (template_id 포함)
      navigate(
        `/docs/legal/generate?txn_id=${txnId}&template_id=${result.template_id}`,
      );
    } catch {
      // onError 토스트가 이미 표시됨 — unhandled rejection 방지
    }
  }, [
    step3Mut,
    sessionId,
    templateName,
    templateDesc,
    docType,
    variables,
    clauses,
    navigate,
    txnId,
  ]);

  const isPending =
    step1Mut.isPending || step2Mut.isPending || step3Mut.isPending;

  return (
    <div ref={containerRef} className="flex flex-col gap-6">
      {/* 스텝 인디케이터 */}
      <nav
        aria-label={`SPA 분석 단계: ${step + 1}/${STEP_LABELS.length} — ${STEP_LABELS[step]}`}
      >
        <ol className="flex items-center gap-2" role="list">
          {STEP_LABELS.map((label, i) => (
            <li key={label} className="flex items-center gap-2">
              {i > 0 && (
                <ChevronRight
                  className="h-4 w-4 text-text-tertiary"
                  aria-hidden="true"
                />
              )}
              <div
                aria-current={i === step ? "step" : undefined}
                className={`flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium ${
                  i === step
                    ? "bg-accent-primary text-white"
                    : i < step
                      ? "bg-emerald-100 text-emerald-700"
                      : "bg-white-elevated text-text-tertiary"
                }`}
              >
                <span
                  className="flex h-4 w-4 items-center justify-center rounded-full bg-white/20 text-[10px]"
                  aria-hidden="true"
                >
                  {i < step ? "\u2713" : i + 1}
                </span>
                {label}
              </div>
            </li>
          ))}
        </ol>
      </nav>

      {/* aria-live 상태 */}
      <div aria-live="polite" role="status" className="sr-only">
        {step1Mut.isPending && "계약서 원문을 분석하고 있습니다..."}
        {step2Mut.isPending && "조항을 분해하고 있습니다..."}
        {step3Mut.isPending && "템플릿을 생성하고 있습니다..."}
      </div>

      {/* Step 0: 원문 입력 */}
      {step === 0 && (
        <>
          {step1Mut.isPending ? (
            <AnalysisOverlay message="계약서 원문에서 변수를 추출하고 있습니다..." />
          ) : (
            <>
              {step1Mut.isError && (
                <div
                  role="alert"
                  className="flex items-start gap-2 rounded-lg border border-negative/30 bg-red-50 p-3 text-sm text-negative"
                >
                  <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
                  <div>
                    <p className="font-medium">변수 추출 실패</p>
                    <p className="text-xs text-negative/80">
                      {step1Mut.error instanceof Error
                        ? step1Mut.error.message
                        : "LLM 분석 중 오류가 발생했습니다. 다시 시도하세요."}
                    </p>
                  </div>
                </div>
              )}
              <SpaTextInput
                onSubmit={handleStep1Submit}
                isPending={step1Mut.isPending}
                initialText={preservedText}
              />
            </>
          )}
        </>
      )}

      {/* Step 1: 변수 리뷰 */}
      {step === 1 && (
        <div className="flex flex-col gap-4">
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => setStep(0)}
              className="rounded-lg p-1.5 text-text-tertiary hover:bg-white-elevated hover:text-text-primary"
              aria-label="이전 단계: 원문 입력으로 돌아가기"
            >
              <ArrowLeft className="h-4 w-4" />
            </button>
            <div>
              <h2 className="text-sm font-semibold text-text-primary">
                추출된 변수 확인
              </h2>
              <div className="mt-0.5 flex items-center gap-3 text-xs text-text-secondary">
                <span>
                  {variables.length}개 변수 · 편집/삭제/추가 후 다음 단계로
                  진행하세요
                </span>
                <span className="text-text-tertiary">|</span>
                <label
                  htmlFor="wizard-doc-type"
                  className="flex items-center gap-1.5"
                >
                  <span className="font-medium">계약 유형</span>
                  <select
                    id="wizard-doc-type"
                    value={docType}
                    onChange={(e) => {
                      const next = e.target.value as DocType;
                      setDocType(next);
                      // 문서 유형 전환 시 dealStructure + 전용 상태 리셋
                      if (
                        next === "SHA" &&
                        !(SHA_TYPES as readonly string[]).includes(
                          dealStructure,
                        )
                      ) {
                        setDealStructure("OTHER_TYPE");
                      } else if (
                        next === "BTA" &&
                        !(BTA_SCOPES as readonly string[]).includes(
                          dealStructure,
                        )
                      ) {
                        setDealStructure("OTHER_SCOPE");
                      } else if (
                        next === "SSA" &&
                        !(SSA_SECURITY_TYPES as readonly string[]).includes(
                          dealStructure,
                        )
                      ) {
                        setDealStructure("OTHER_SECURITY");
                        setSecurityType("OTHER_SECURITY");
                      } else if (
                        next === "MOU" &&
                        !(MOU_TRANSACTION_TYPES as readonly string[]).includes(
                          dealStructure,
                        )
                      ) {
                        setDealStructure("OTHER_MOU_TYPE");
                        setMouTransactionType("OTHER_MOU_TYPE");
                      } else if (
                        !["SHA", "BTA", "SSA", "MOU"].includes(next) &&
                        !(DEAL_STRUCTURES as readonly string[]).includes(
                          dealStructure,
                        )
                      ) {
                        setDealStructure("PURE_SHARE_TRANSFER");
                      }
                      // 이전 유형 전용 상태 초기화
                      if (next !== "SHA") {
                        setExitStrategy("OTHER_STRATEGY");
                      }
                      if (next !== "BTA") {
                        setSeverancePayHandling("OTHER_METHOD");
                      }
                      if (next !== "SSA") {
                        setSecurityType("OTHER_SECURITY");
                        setTransactionContext("OTHER_CONTEXT");
                      }
                      if (next !== "MOU") {
                        setMouTransactionType("OTHER_MOU_TYPE");
                        setDepositHandling("NO_DEPOSIT");
                      }
                    }}
                    className="rounded-lg border border-border bg-white px-2 py-0.5 text-xs text-text-primary focus:border-accent-primary focus:outline-none focus:ring-1 focus:ring-accent-primary"
                  >
                    {DOC_TYPES.map((dt) => (
                      <option key={dt} value={dt}>
                        {DOC_TYPE_LABELS[dt]}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
            </div>
          </div>

          {/* SHA/BTA: 전용 분류 패널 / SPA 등: VariableReviewPanel 내장 분류 */}
          {docType === "SHA" ? (
            <>
              <ShaClassificationPanel
                shaType={dealStructure as ShaType}
                exitStrategy={exitStrategy}
                industryType={industryType}
                onShaTypeChange={(v) => setDealStructure(v)}
                onExitStrategyChange={setExitStrategy}
                onIndustryTypeChange={setIndustryType}
                variableCount={variables.length}
              />
              <VariableReviewPanel
                variables={variables}
                dealStructure={dealStructure}
                industryType={industryType}
                onVariablesChange={setVariables}
                onDealStructureChange={setDealStructure}
                onIndustryTypeChange={setIndustryType}
                hideClassification
              />
            </>
          ) : docType === "BTA" ? (
            <>
              <BtaClassificationPanel
                btaScope={dealStructure as BtaScope}
                severancePayHandling={severancePayHandling}
                industryType={industryType}
                onBtaScopeChange={(v) => setDealStructure(v)}
                onSeverancePayChange={setSeverancePayHandling}
                onIndustryTypeChange={setIndustryType}
                variableCount={variables.length}
              />
              <VariableReviewPanel
                variables={variables}
                dealStructure={dealStructure}
                industryType={industryType}
                onVariablesChange={setVariables}
                onDealStructureChange={setDealStructure}
                onIndustryTypeChange={setIndustryType}
                hideClassification
              />
            </>
          ) : docType === "SSA" ? (
            <>
              <SsaClassificationPanel
                securityType={securityType}
                transactionContext={transactionContext}
                industryType={industryType}
                onSecurityTypeChange={(v) => {
                  setSecurityType(v);
                  setDealStructure(v);
                }}
                onTransactionContextChange={setTransactionContext}
                onIndustryTypeChange={setIndustryType}
                variableCount={variables.length}
              />
              <VariableReviewPanel
                variables={variables}
                dealStructure={dealStructure}
                industryType={industryType}
                onVariablesChange={setVariables}
                onDealStructureChange={setDealStructure}
                onIndustryTypeChange={setIndustryType}
                hideClassification
              />
            </>
          ) : docType === "MOU" ? (
            <>
              <MouClassificationPanel
                mouTransactionType={mouTransactionType}
                depositHandling={depositHandling}
                industryType={industryType}
                onMouTransactionTypeChange={(v) => {
                  setMouTransactionType(v);
                  setDealStructure(v);
                }}
                onDepositHandlingChange={setDepositHandling}
                onIndustryTypeChange={setIndustryType}
                variableCount={variables.length}
              />
              <VariableReviewPanel
                variables={variables}
                dealStructure={dealStructure}
                industryType={industryType}
                onVariablesChange={setVariables}
                onDealStructureChange={setDealStructure}
                onIndustryTypeChange={setIndustryType}
                hideClassification
              />
            </>
          ) : (
            <VariableReviewPanel
              variables={variables}
              dealStructure={dealStructure}
              industryType={industryType}
              onVariablesChange={setVariables}
              onDealStructureChange={setDealStructure}
              onIndustryTypeChange={setIndustryType}
            />
          )}

          {/* Step 2 에러 배너 */}
          {step2Mut.isError && (
            <div
              role="alert"
              className="flex items-start gap-2 rounded-lg border border-negative/30 bg-red-50 p-3 text-sm text-negative"
            >
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
              <div>
                <p className="font-medium">조항 분해 실패</p>
                <p className="text-xs text-negative/80">
                  {step2Mut.error instanceof Error
                    ? step2Mut.error.message
                    : "LLM 분석 중 오류가 발생했습니다. 다시 시도하세요."}
                </p>
              </div>
            </div>
          )}

          {/* 다음 단계 (로딩 중에는 오버레이만 표시) */}
          {step2Mut.isPending ? (
            <AnalysisOverlay message="확정된 변수를 기반으로 조항을 분해하고 있습니다..." />
          ) : (
            <div className="flex justify-end">
              <button
                type="button"
                onClick={handleStep2Submit}
                disabled={variables.length === 0}
                className="flex items-center gap-1.5 rounded-lg bg-accent-primary px-4 py-2 text-sm font-medium text-white hover:bg-accent-primary/90 disabled:opacity-40"
              >
                <ArrowRight className="h-4 w-4" />
                조항 분해 시작
              </button>
            </div>
          )}
        </div>
      )}

      {/* Step 2: 조항 리뷰 */}
      {step === 2 && (
        <div className="flex flex-col gap-4">
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => {
                setClauses([]);
                setStep(1);
              }}
              className="rounded-lg p-1.5 text-text-tertiary hover:bg-white-elevated hover:text-text-primary"
              aria-label="이전 단계: 변수 확인으로 돌아가기"
            >
              <ArrowLeft className="h-4 w-4" />
            </button>
            <div>
              <h2 className="text-sm font-semibold text-text-primary">
                분해된 조항 확인
              </h2>
              <p className="text-xs text-text-secondary">
                {clauses.length}개 조항 · 순서 조정, 조건식 편집, 삭제 가능
              </p>
            </div>
          </div>

          <ClauseReviewPanel clauses={clauses} onClausesChange={setClauses} />

          <div className="flex justify-end">
            <button
              type="button"
              onClick={handleGoToStep3}
              disabled={clauses.length === 0}
              className="flex items-center gap-1.5 rounded-lg bg-accent-primary px-4 py-2 text-sm font-medium text-white hover:bg-accent-primary/90 disabled:opacity-40"
            >
              <ArrowRight className="h-4 w-4" />
              템플릿 정보 입력
            </button>
          </div>
        </div>
      )}

      {/* Step 3: 템플릿 생성 */}
      {step === 3 && (
        <div className="flex flex-col gap-4">
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => setStep(2)}
              className="rounded-lg p-1.5 text-text-tertiary hover:bg-white-elevated hover:text-text-primary"
              aria-label="이전 단계: 조항 확인으로 돌아가기"
            >
              <ArrowLeft className="h-4 w-4" />
            </button>
            <div>
              <h2 className="text-sm font-semibold text-text-primary">
                템플릿 생성
              </h2>
              <p className="text-xs text-text-secondary">
                {variables.length}개 변수 · {clauses.length}개 조항 → 재사용
                가능 템플릿으로 저장
              </p>
            </div>
          </div>

          <div className="rounded-xl border border-border p-4">
            <div className="flex flex-col gap-4">
              <div>
                <label
                  htmlFor="tmpl-name"
                  className="mb-1 block text-xs font-medium text-text-secondary"
                >
                  템플릿 이름 <span className="text-negative">*</span>
                </label>
                <input
                  id="tmpl-name"
                  type="text"
                  value={templateName}
                  onChange={(e) => setTemplateName(e.target.value)}
                  className="w-full rounded-lg border border-border bg-white px-3 py-2 text-sm text-text-primary focus:border-accent-primary focus:outline-none focus:ring-1 focus:ring-accent-primary"
                  placeholder="예: Project Alpha SPA 템플릿"
                />
              </div>
              <div>
                <label
                  htmlFor="tmpl-desc"
                  className="mb-1 block text-xs font-medium text-text-secondary"
                >
                  설명 (선택)
                </label>
                <textarea
                  id="tmpl-desc"
                  value={templateDesc}
                  onChange={(e) => setTemplateDesc(e.target.value)}
                  rows={3}
                  className="w-full rounded-lg border border-border bg-white px-3 py-2 text-sm text-text-primary placeholder:text-text-tertiary focus:border-accent-primary focus:outline-none focus:ring-1 focus:ring-accent-primary"
                  placeholder="이 템플릿의 특징이나 용도를 간략히 기술하세요"
                />
              </div>
            </div>
          </div>

          {/* 요약 */}
          <div className="rounded-xl border border-border p-4">
            <h3 className="mb-2 text-xs font-semibold text-text-secondary">
              생성 요약
            </h3>
            <div
              className={`grid grid-cols-2 gap-2 text-sm ${docType === "SHA" || docType === "BTA" || docType === "SSA" || docType === "MOU" ? "sm:grid-cols-6" : "sm:grid-cols-5"}`}
            >
              <div className="flex flex-col">
                <span className="text-text-tertiary text-xs">계약 유형</span>
                <span className="font-medium text-text-primary">
                  {DOC_TYPE_LABELS[docType] ?? docType}
                </span>
              </div>
              <div className="flex flex-col">
                <span className="text-text-tertiary text-xs">변수</span>
                <span className="font-medium text-text-primary">
                  {variables.length}개
                </span>
              </div>
              <div className="flex flex-col">
                <span className="text-text-tertiary text-xs">조항</span>
                <span className="font-medium text-text-primary">
                  {clauses.length}개
                </span>
              </div>
              {docType === "SHA" ? (
                <>
                  <div className="flex flex-col">
                    <span className="text-text-tertiary text-xs">SHA 유형</span>
                    <span className="font-medium text-text-primary">
                      {SHA_TYPE_LABELS[dealStructure as ShaType] ??
                        dealStructure}
                    </span>
                  </div>
                  <div className="flex flex-col">
                    <span className="text-text-tertiary text-xs">
                      Exit 전략
                    </span>
                    <span className="font-medium text-text-primary">
                      {EXIT_STRATEGY_LABELS[exitStrategy] ?? exitStrategy}
                    </span>
                  </div>
                </>
              ) : docType === "BTA" ? (
                <>
                  <div className="flex flex-col">
                    <span className="text-text-tertiary text-xs">
                      양도 범위
                    </span>
                    <span className="font-medium text-text-primary">
                      {BTA_SCOPE_LABELS[dealStructure as BtaScope] ??
                        dealStructure}
                    </span>
                  </div>
                  <div className="flex flex-col">
                    <span className="text-text-tertiary text-xs">
                      퇴직금 처리
                    </span>
                    <span className="font-medium text-text-primary">
                      {SEVERANCE_PAY_LABELS[severancePayHandling] ??
                        severancePayHandling}
                    </span>
                  </div>
                </>
              ) : docType === "SSA" ? (
                <>
                  <div className="flex flex-col">
                    <span className="text-text-tertiary text-xs">
                      증권 종류
                    </span>
                    <span className="font-medium text-text-primary">
                      {SSA_SECURITY_TYPE_LABELS[securityType] ?? securityType}
                    </span>
                  </div>
                  <div className="flex flex-col">
                    <span className="text-text-tertiary text-xs">
                      거래 맥락
                    </span>
                    <span className="font-medium text-text-primary">
                      {SSA_TRANSACTION_CONTEXT_LABELS[transactionContext] ??
                        transactionContext}
                    </span>
                  </div>
                </>
              ) : docType === "MOU" ? (
                <>
                  <div className="flex flex-col">
                    <span className="text-text-tertiary text-xs">
                      거래 유형
                    </span>
                    <span className="font-medium text-text-primary">
                      {MOU_TRANSACTION_TYPE_LABELS[mouTransactionType] ??
                        mouTransactionType}
                    </span>
                  </div>
                  <div className="flex flex-col">
                    <span className="text-text-tertiary text-xs">
                      보증금 처리
                    </span>
                    <span className="font-medium text-text-primary">
                      {MOU_DEPOSIT_HANDLING_LABELS[depositHandling] ??
                        depositHandling}
                    </span>
                  </div>
                </>
              ) : (
                <div className="flex flex-col">
                  <span className="text-text-tertiary text-xs">딜 구조</span>
                  <span className="font-medium text-text-primary">
                    {DEAL_STRUCTURE_LABELS[
                      dealStructure as keyof typeof DEAL_STRUCTURE_LABELS
                    ] ?? dealStructure}
                  </span>
                </div>
              )}
              <div className="flex flex-col">
                <span className="text-text-tertiary text-xs">산업</span>
                <span className="font-medium text-text-primary">
                  {INDUSTRY_TYPE_LABELS[industryType] ?? industryType}
                </span>
              </div>
            </div>
          </div>

          {/* 생성 버튼 */}
          <div className="flex justify-end">
            <button
              type="button"
              onClick={handleCreateTemplate}
              disabled={isPending || !templateName.trim()}
              className="flex items-center gap-1.5 rounded-lg bg-accent-primary px-4 py-2 text-sm font-medium text-white hover:bg-accent-primary/90 disabled:opacity-40"
            >
              {step3Mut.isPending ? (
                <RefreshCw className="h-4 w-4 animate-spin" />
              ) : (
                <Sparkles className="h-4 w-4" />
              )}
              {step3Mut.isPending ? "생성 중..." : "템플릿 생성 및 저장"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

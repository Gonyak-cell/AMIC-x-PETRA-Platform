/** 계약서 자동 생성 위저드 — Step 0 → Step 1 → Step 2 */

import { useCallback, useEffect, useRef, useState } from "react";
import { ArrowLeft, ChevronRight, RefreshCw, Sparkles } from "lucide-react";
import {
  useContractTemplates,
  useContractTemplateDetail,
  useGenerateContract,
  useExportDocx,
  useSaveContractHtml,
  downloadBlob,
} from "@/modules/docs/hooks/useContractGeneration";
import type {
  ContractTemplate,
  ContractGenerationResult,
} from "@/modules/docs/types/contract_generation";
import TemplateSelector from "./TemplateSelector";
import DynamicVariableForm from "./DynamicVariableForm";
import ContractEditor from "./ContractEditor";

interface ContractGeneratorWizardProps {
  txnId: string;
}

const STEP_LABELS = ["유형 선택", "체크리스트 작성", "편집 및 다운로드"];

export default function ContractGeneratorWizard({
  txnId,
}: ContractGeneratorWizardProps) {
  const [step, setStep] = useState(0);
  const [selectedTemplate, setSelectedTemplate] =
    useState<ContractTemplate | null>(null);
  const [variables, setVariables] = useState<Record<string, unknown>>({});
  const [useLlm, setUseLlm] = useState(true);
  const [generatedHtml, setGeneratedHtml] = useState("");
  const [savedHtml, setSavedHtml] = useState("");
  const [genResult, setGenResult] = useState<ContractGenerationResult | null>(
    null,
  );
  const [contractTitle, setContractTitle] = useState("");
  const [lastModifiedAt, setLastModifiedAt] = useState<string | null>(null);

  const isDirty = generatedHtml !== savedHtml;
  const containerRef = useRef<HTMLDivElement>(null);

  // 스텝 전환 시 컨테이너 내 첫 제목으로 포커스 이동 (스크린 리더 안내)
  useEffect(() => {
    const heading = containerRef.current?.querySelector<HTMLElement>("h2, h3");
    if (heading) {
      heading.setAttribute("tabindex", "-1");
      heading.focus();
    }
  }, [step]);

  // API 훅
  const { data: templates, isLoading: templatesLoading } =
    useContractTemplates(txnId);
  const { data: templateDetail } = useContractTemplateDetail(
    txnId,
    selectedTemplate?.id ?? "",
  );
  const generateMut = useGenerateContract(txnId);
  const exportMut = useExportDocx(txnId);
  const saveMut = useSaveContractHtml(txnId);

  // Step 0 → 1: 템플릿 선택
  const handleTemplateSelect = useCallback((tmpl: ContractTemplate) => {
    setSelectedTemplate(tmpl);
    setContractTitle(`${tmpl.doc_type} 계약서`);
    setVariables({});
    setStep(1);
  }, []);

  // 변수 값 변경
  const handleVariableChange = useCallback((key: string, value: unknown) => {
    setVariables((prev) => ({ ...prev, [key]: value }));
  }, []);

  // Step 1 → 2: 계약서 생성
  const handleGenerate = useCallback(async () => {
    if (!selectedTemplate) return;
    const result = await generateMut.mutateAsync({
      template_id: selectedTemplate.id,
      title: contractTitle,
      variables,
      use_llm_smoothing: useLlm,
    });
    setGeneratedHtml(result.html);
    setSavedHtml(result.html);
    setGenResult(result);
    setLastModifiedAt(result.updated_at);
    setStep(2);
  }, [selectedTemplate, contractTitle, variables, useLlm, generateMut]);

  // DOCX 내보내기
  const handleExportDocx = useCallback(async () => {
    const blob = await exportMut.mutateAsync({
      html: generatedHtml,
      title: contractTitle,
    });
    downloadBlob(blob, `${contractTitle}.docx`);
  }, [generatedHtml, contractTitle, exportMut]);

  // HTML 저장 (OCC 지원)
  const handleSave = useCallback(async () => {
    if (!genResult) return;
    const result = await saveMut.mutateAsync({
      docId: genResult.legal_document_id,
      html: generatedHtml,
      lastModifiedAt,
    });
    setLastModifiedAt(result.updated_at);
    // 서버 살균 결과가 다르면 에디터 동기화
    if (result.html) {
      setGeneratedHtml(result.html);
      setSavedHtml(result.html);
    } else {
      setSavedHtml(generatedHtml);
    }
  }, [genResult, generatedHtml, saveMut, lastModifiedAt]);

  // Step 2 → 1 뒤로가기 (미저장 확인)
  const handleBackFromEditor = useCallback(() => {
    if (
      isDirty &&
      !window.confirm(
        "저장하지 않은 변경사항이 있습니다. 이전 단계로 돌아가시겠습니까?",
      )
    ) {
      return;
    }
    setStep(1);
  }, [isDirty]);

  return (
    <div ref={containerRef} className="flex flex-col gap-6">
      {/* 스텝 인디케이터 */}
      <nav
        aria-label={`계약서 생성 단계: ${step + 1}/${STEP_LABELS.length} — ${STEP_LABELS[step]}`}
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
                  {i < step ? "✓" : i + 1}
                </span>
                {label}
              </div>
            </li>
          ))}
        </ol>
      </nav>

      {/* A-2: aria-live 상태 알림 영역 */}
      <div aria-live="polite" role="status" className="sr-only">
        {generateMut.isPending && "계약서를 생성하고 있습니다..."}
        {exportMut.isPending && "DOCX 파일을 생성하고 있습니다..."}
        {saveMut.isPending && "초안을 저장하고 있습니다..."}
      </div>

      {/* Step 0: 템플릿 선택 */}
      {step === 0 && (
        <div>
          <h2 className="mb-4 text-sm font-semibold text-text-primary">
            계약서 유형을 선택하세요
          </h2>
          <TemplateSelector
            templates={templates}
            isLoading={templatesLoading}
            onSelect={handleTemplateSelect}
          />
        </div>
      )}

      {/* Step 1: 변수 폼 */}
      {step === 1 && templateDetail && (
        <div className="flex flex-col gap-4">
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => setStep(0)}
              className="rounded-lg p-1.5 text-text-tertiary hover:bg-white-elevated hover:text-text-primary"
              title="유형 선택으로 돌아가기"
              aria-label="이전 단계: 유형 선택으로 돌아가기"
            >
              <ArrowLeft className="h-4 w-4" />
            </button>
            <div>
              <h2 className="text-sm font-semibold text-text-primary">
                {selectedTemplate?.doc_type} — 체크리스트 입력
              </h2>
              <p className="text-xs text-text-secondary">
                {templateDetail.variables.length}개 항목 ·{" "}
                {templateDetail.clauses.length}개 조항 템플릿
              </p>
            </div>
          </div>

          {/* 계약서 제목 */}
          <div className="rounded-xl border border-border p-4">
            <label
              htmlFor="contract-title"
              className="mb-1 block text-xs font-medium text-text-secondary"
            >
              계약서 제목 <span className="text-negative">*</span>
            </label>
            <input
              id="contract-title"
              type="text"
              value={contractTitle}
              onChange={(e) => setContractTitle(e.target.value)}
              className="w-full rounded-lg border border-border bg-white px-3 py-2 text-sm text-text-primary focus:border-accent-primary focus:outline-none focus:ring-1 focus:ring-accent-primary"
              placeholder="예: 주식매매계약서"
            />
          </div>

          {/* 동적 변수 폼 */}
          <DynamicVariableForm
            variables={templateDetail.variables}
            values={variables}
            onChange={handleVariableChange}
          />

          {/* LLM 스무딩 토글 + 생성 버튼 */}
          <div className="flex items-center justify-between rounded-xl border border-border p-4">
            <label
              htmlFor="llm-smoothing"
              className="flex items-center gap-2 cursor-pointer"
            >
              <input
                id="llm-smoothing"
                type="checkbox"
                checked={useLlm}
                onChange={(e) => setUseLlm(e.target.checked)}
                className="h-4 w-4 rounded border-border text-accent-primary focus:ring-accent-primary"
              />
              <div>
                <span className="text-sm font-medium text-text-primary">
                  AI 다듬기
                </span>
                <p className="text-xs text-text-tertiary">
                  조항 번호, 교차 참조, 용어 통일 자동 교정 (10~30초 소요)
                </p>
              </div>
            </label>

            <button
              type="button"
              onClick={handleGenerate}
              disabled={generateMut.isPending || !contractTitle}
              className="flex items-center gap-1.5 rounded-lg bg-accent-primary px-4 py-2 text-sm font-medium text-white hover:bg-accent-primary/90 disabled:opacity-40"
            >
              {generateMut.isPending ? (
                <RefreshCw className="h-4 w-4 animate-spin" />
              ) : (
                <Sparkles className="h-4 w-4" />
              )}
              {generateMut.isPending ? "생성 중..." : "계약서 생성"}
            </button>
          </div>
        </div>
      )}

      {/* Step 2: 에디터 */}
      {step === 2 && genResult && (
        <div className="flex flex-col gap-4">
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={handleBackFromEditor}
              className="rounded-lg p-1.5 text-text-tertiary hover:bg-white-elevated hover:text-text-primary"
              title="체크리스트로 돌아가기"
              aria-label="이전 단계: 체크리스트로 돌아가기"
            >
              <ArrowLeft className="h-4 w-4" />
            </button>
            <div>
              <h2 className="text-sm font-semibold text-text-primary">
                계약서 편집
              </h2>
              <p className="text-xs text-text-secondary">
                {genResult.clauses_used}개 조항 사용 ·{" "}
                {genResult.clauses_skipped}개 건너뜀
                {genResult.llm_smoothed
                  ? " · AI 다듬기 완료"
                  : " · AI 다듬기 미적용"}
              </p>
            </div>
          </div>

          <ContractEditor
            html={generatedHtml}
            onHtmlChange={setGeneratedHtml}
            onExportDocx={handleExportDocx}
            onSave={handleSave}
            isExporting={exportMut.isPending}
            isSaving={saveMut.isPending}
            title={contractTitle}
            isDirty={isDirty}
          />
        </div>
      )}
    </div>
  );
}

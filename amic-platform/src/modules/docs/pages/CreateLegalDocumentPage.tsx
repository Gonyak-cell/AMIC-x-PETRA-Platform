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
} from "lucide-react";
import { cn } from "@/lib/cn";
import { Button, PageHero } from "@/components/ui";
import LegalDocTypePicker from "@/modules/docs/components/LegalDocTypePicker";
import LegalParamsForm from "@/modules/docs/components/LegalParamsForm";
import { useCreateLegalDocument, getLegalDocDownloadUrl } from "@/modules/docs/hooks/useLegalDocuments";
import { LEGAL_DOC_META } from "@/modules/docs/types/legal_document";
import type { LegalDocType } from "@/modules/docs/types/legal_document";
import { useTransaction } from "@/modules/ma/hooks/useTransactions";
import heroImg from "@/assets/images/heroes/hero-arch-dark-round.jpg";

// ── Step 인디케이터 ───────────────────────────────────────────────────────────

function StepIndicator({ step }: { step: number }) {
  const steps = ["문서 유형 선택", "세부 정보 입력", "생성 확인"];
  return (
    <ol className="flex items-center gap-2 list-none p-0 m-0" aria-label="법률 문서 생성 단계">
      {steps.map((label, i) => (
        <li key={i} className="flex items-center gap-2" aria-current={i === step ? "step" : undefined}>
          <div className="flex items-center gap-1.5">
            <div
              aria-label={`${i + 1}단계: ${label}${i < step ? " (완료)" : i === step ? " (현재)" : ""}`}
              className={cn(
                "flex h-7 w-7 items-center justify-center rounded-full text-xs font-medium transition-colors",
                i < step
                  ? "bg-amic text-white"
                  : i === step
                    ? "bg-amic text-white ring-2 ring-amic/20 ring-offset-2"
                    : "border border-gray-border bg-bg-cool text-text-secondary",
              )}
            >
              {i < step ? <CheckCircle className="h-3.5 w-3.5" aria-hidden="true" /> : i + 1}
            </div>
            <span
              className={cn(
                "hidden text-xs font-heading sm:inline",
                i === step ? "font-semibold text-text-dark" : "text-text-secondary",
              )}
            >
              {label}
            </span>
          </div>
          {i < steps.length - 1 && (
            <div
              aria-hidden="true"
              className={cn("h-px w-8", i < step ? "bg-amic" : "bg-gray-border")}
            />
          )}
        </li>
      ))}
    </ol>
  );
}

// ── 메인 페이지 ───────────────────────────────────────────────────────────────

interface CreateLegalDocumentPageProps {
  defaultType?: LegalDocType;
}

export default function CreateLegalDocumentPage({ defaultType }: CreateLegalDocumentPageProps = {}) {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  const txnId = searchParams.get("txn_id") ?? "";
  const typeParam = (searchParams.get("type") as LegalDocType | null) ?? defaultType ?? null;

  const [step, setStep] = useState<0 | 1 | 2>(typeParam ? 1 : 0);
  const [selectedType, setSelectedType] = useState<LegalDocType | null>(typeParam);
  const [title, setTitle] = useState("");
  const [params, setParams] = useState<Record<string, unknown>>({});

  // 생성 결과
  const [createdDocId, setCreatedDocId] = useState<string | null>(null);
  const [createdStatus, setCreatedStatus] = useState<string | null>(null);
  const [createdError, setCreatedError] = useState<string | null>(null);

  // Transaction 데이터 (txn_id 있을 때 자동 채우기)
  const { data: txn } = useTransaction(txnId);

  // Transaction 데이터 자동 채우기
  useEffect(() => {
    if (!txn || !selectedType) return;

    setParams((prev) => {
      const defaults: Record<string, unknown> = { ...prev };

      // 공통 자동 채우기
      if (txn.target_company_name && !prev.target_company_name) {
        defaults.target_company_name = txn.target_company_name;
      }
      if (txn.target_close_date && !prev.closing_date) {
        defaults.closing_date = txn.target_close_date;
      }
      if (txn.estimated_deal_value && !prev.total_purchase_price) {
        defaults.total_purchase_price = txn.estimated_deal_value;
      }

      // SPA 전용
      if (selectedType === "SPA") {
        if (txn.side === "SELL" && txn.client_name && !prev.seller_name) {
          defaults.seller_name = txn.client_name;
        } else if (txn.side === "BUY" && txn.client_name && !prev.buyer_name) {
          defaults.buyer_name = txn.client_name;
        }
      }

      // MOU 전용
      if (selectedType === "MOU") {
        if (txn.client_name && !prev.party_a_name) {
          defaults.party_a_name = txn.client_name;
        }
        if (txn.target_company_name && !prev.party_b_name) {
          defaults.party_b_name = txn.target_company_name;
        }
      }

      return defaults;
    });
  }, [txn, selectedType]);

  const createMut = useCreateLegalDocument(txnId);

  const handleSelectType = (type: LegalDocType) => {
    setSelectedType(type);
    const meta = LEGAL_DOC_META[type];
    setTitle(`${meta.labelKo} - ${txn?.code_name ?? txn?.name ?? ""}`.trim().replace(/ - $/, ""));
    setParams({});
    setStep(1);
  };

  const handleBack = () => {
    if (step === 1) {
      setStep(0);
    } else if (step === 2) {
      setStep(1);
    }
  };

  const handleToConfirm = () => {
    if (!selectedType || !title.trim()) return;
    setStep(2);
  };

  const handleGenerate = async () => {
    if (!selectedType || !txnId) return;

    try {
      const doc = await createMut.mutateAsync({
        doc_type: selectedType,
        title: title.trim(),
        parameters: params,
      });
      setCreatedDocId(doc.id);
      setCreatedStatus(doc.status);
      if (doc.error_message) setCreatedError(doc.error_message);
    } catch {
      // 에러는 useMutation onError에서 toast 처리
    }
  };

  const handleDone = () => {
    if (txnId) {
      navigate(`/ma/transactions/${txnId}/legal_docs`);
    } else {
      navigate("/docs");
    }
  };

  return (
    <div className="space-y-6">
      <PageHero
        title="법률 문서 생성"
        subtitle="SPA, SHA, BTA, SSA, MOU 등 M&A 법률 문서를 생성합니다"
        backgroundImage={heroImg}
        backgroundOpacity={0.18}
        compact
        actions={
          <Button variant="ghost" icon={ArrowLeft} onClick={() => navigate(-1)}>
            뒤로
          </Button>
        }
      />

      {/* Step 인디케이터 */}
      <div className="px-1">
        <StepIndicator step={step} />
      </div>

      {/* ── Step 0: 유형 선택 ── */}
      {step === 0 && (
        <div className="space-y-4">
          <h2 className="text-sm font-semibold text-text-primary">생성할 문서 유형을 선택하세요</h2>
          <LegalDocTypePicker value={null} onChange={handleSelectType} />
        </div>
      )}

      {/* ── Step 1: 파라미터 입력 ── */}
      {step === 1 && selectedType && (
        <div className="space-y-6">
          {/* 제목 입력 */}
          <div className="space-y-1.5">
            <label
              htmlFor="legal-doc-title"
              className="text-xs font-medium text-text-secondary"
            >
              문서 제목{" "}
              <span className="text-negative" aria-label="필수">*</span>
            </label>
            <input
              id="legal-doc-title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder={`${LEGAL_DOC_META[selectedType].labelKo} 제목을 입력하세요`}
              required
              aria-required="true"
              className="w-full rounded-lg border border-border bg-white px-3 py-2 text-sm text-text-primary placeholder:text-text-placeholder focus:border-accent-primary focus:outline-none focus:ring-1 focus:ring-accent-primary"
            />
          </div>

          {/* 파라미터 폼 */}
          <div className="rounded-xl border border-border bg-white p-5">
            <h3 className="mb-4 text-sm font-semibold text-text-primary">
              {LEGAL_DOC_META[selectedType].labelKo} 정보
            </h3>
            <LegalParamsForm
              docType={selectedType}
              params={params}
              onChange={setParams}
            />
          </div>

          {/* 하단 버튼 */}
          <div className="flex justify-between">
            <Button variant="ghost" icon={ArrowLeft} onClick={handleBack}>
              유형 재선택
            </Button>
            <Button
              icon={ArrowRight}
              iconPosition="right"
              onClick={handleToConfirm}
              disabled={!title.trim()}
            >
              확인 및 생성
            </Button>
          </div>
        </div>
      )}

      {/* ── Step 2: 확인 및 생성 ── */}
      {step === 2 && selectedType && (
        <div className="space-y-6">
          {/* 생성 전 요약 */}
          {!createdDocId && (
            <>
              <div className="rounded-xl border border-border bg-white p-5 space-y-3">
                <h3 className="text-sm font-semibold text-text-primary">생성 정보 확인</h3>
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div>
                    <p className="text-xs text-text-tertiary">문서 유형</p>
                    <p className="font-medium text-text-primary">
                      {selectedType} — {LEGAL_DOC_META[selectedType].labelKo}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-text-tertiary">문서 제목</p>
                    <p className="font-medium text-text-primary">{title}</p>
                  </div>
                  {txn && (
                    <div>
                      <p className="text-xs text-text-tertiary">거래</p>
                      <p className="font-medium text-text-primary">{txn.name}</p>
                    </div>
                  )}
                </div>
                <div className="border-t border-border pt-3">
                  <p className="text-xs text-text-tertiary mb-2">입력 파라미터 ({Object.keys(params).length}개)</p>
                  <div className="max-h-40 overflow-y-auto rounded-lg bg-white-elevated p-3 text-xs font-mono text-text-secondary">
                    {Object.entries(params).map(([k, v]) => (
                      <div key={k} className="flex gap-2">
                        <span className="text-text-tertiary">{k}:</span>
                        <span className="truncate">{JSON.stringify(v)}</span>
                      </div>
                    ))}
                    {Object.keys(params).length === 0 && (
                      <span className="text-text-tertiary">파라미터 없음 (기본 템플릿 사용)</span>
                    )}
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
                  {createMut.isPending ? "생성 중..." : "문서 생성"}
                </Button>
              </div>
            </>
          )}

          {/* 생성 중 */}
          {createMut.isPending && (
            <div className="flex flex-col items-center gap-3 py-10 text-center">
              <Loader2 className="h-10 w-10 animate-spin text-accent-primary" />
              <p className="text-sm font-medium text-text-primary">법률 문서를 생성하고 있습니다...</p>
              <p className="text-xs text-text-tertiary">잠시 기다려 주세요</p>
            </div>
          )}

          {/* 생성 완료 — READY */}
          {createdDocId && createdStatus === "READY" && (
            <div className="flex flex-col items-center gap-4 py-10 text-center">
              <div className="flex h-16 w-16 items-center justify-center rounded-full bg-emerald-100">
                <CheckCircle className="h-8 w-8 text-emerald-600" />
              </div>
              <div>
                <p className="text-base font-semibold text-text-primary">문서 생성 완료</p>
                <p className="text-sm text-text-secondary">{title}</p>
              </div>
              <div className="flex gap-3">
                <a
                  href={getLegalDocDownloadUrl(txnId, createdDocId)}
                  download={`${selectedType}_${createdDocId}.docx`}
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
          {createdDocId && createdStatus === "FAILED" && (
            <div className="flex flex-col items-center gap-4 py-10 text-center">
              <div className="flex h-16 w-16 items-center justify-center rounded-full bg-negative-light">
                <AlertCircle className="h-8 w-8 text-negative" />
              </div>
              <div>
                <p className="text-base font-semibold text-text-primary">문서 생성 실패</p>
                {createdError && (
                  <p className="text-sm text-text-secondary">{createdError}</p>
                )}
              </div>
              <div className="flex gap-3">
                <Button
                  icon={ArrowLeft}
                  onClick={() => {
                    setCreatedDocId(null);
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

      {/* txn_id 없을 때 경고 */}
      {!txnId && step >= 1 && (
        <div className="flex items-center gap-2 rounded-lg border border-yellow-200 bg-yellow-50 px-4 py-3 text-sm text-yellow-700">
          <AlertCircle className="h-4 w-4 flex-shrink-0" />
          <span>거래(Transaction)가 선택되지 않았습니다. 문서를 저장하려면 거래가 필요합니다.</span>
        </div>
      )}
    </div>
  );
}

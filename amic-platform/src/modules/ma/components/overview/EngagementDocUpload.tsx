import { useState, useCallback, useRef, useEffect } from "react";
import { Upload, CheckCircle2, Loader2, FileText, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { cn } from "@/lib/cn";
import { useQueryClient } from "@tanstack/react-query";
import { maApi } from "@/api/maClient";
import { useVdrFolders, useInitVdr } from "@/modules/ma/hooks/useVdr";
import { useCreateExtraction, useExtraction } from "@/modules/ma/hooks/useDocumentExtraction";
import ExtractionReviewModal from "@/modules/ma/components/extraction/ExtractionReviewModal";
import type { DocumentExtraction } from "@/modules/ma/types/document_extraction";

interface Props {
  txnId: string;
  onComplete?: () => void;
}

const ACCEPTED_TYPES = [
  "application/pdf",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  "image/jpeg",
  "image/png",
];
const ACCEPTED_EXTENSIONS = ".pdf,.docx,.jpg,.jpeg,.png";
const MAX_FILE_SIZE = 50 * 1024 * 1024; // 50MB

type Step = "idle" | "uploading" | "classifying" | "extracting" | "completed" | "failed";

export default function EngagementDocUpload({ txnId, onComplete }: Props) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [step, setStep] = useState<Step>("idle");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [extractionId, setExtractionId] = useState<string | null>(null);
  const [reviewOpen, setReviewOpen] = useState(false);
  const [reviewExtraction, setReviewExtraction] = useState<DocumentExtraction | null>(null);

  // VDR 훅
  const qc = useQueryClient();
  const { data: folders, refetch: refetchFolders } = useVdrFolders(txnId);
  const initVdr = useInitVdr(txnId);
  const createExtraction = useCreateExtraction(txnId);

  // "01. CORPORATE" 폴더 찾기
  const corporateFolder = folders?.find((f) => f.category === "CORPORATE");

  // 추출 상태 폴링 (extractionId가 있을 때만)
  const { data: polledExtraction } = useExtraction(txnId, extractionId ?? "");

  // 폴링 결과 → 완료/실패 시 상태 전환
  useEffect(() => {
    if (!polledExtraction || !extractionId) return;
    if (polledExtraction.status === "COMPLETED" && step !== "completed") {
      setStep("completed");
      setReviewExtraction(polledExtraction);
      setReviewOpen(true);
    } else if (polledExtraction.status === "FAILED" && step !== "failed") {
      setStep("failed");
      setErrorMsg(polledExtraction.error_message ?? "AI 분석에 실패했습니다.");
    } else if (polledExtraction.status === "EXTRACTING" && step === "classifying") {
      setStep("extracting");
    }
  }, [polledExtraction, extractionId, step]);

  // 파일 검증
  const validateFile = useCallback((file: File): string | null => {
    if (!ACCEPTED_TYPES.includes(file.type)) {
      return "지원하지 않는 파일 형식입니다. (PDF, DOCX, JPG, PNG)";
    }
    if (file.size > MAX_FILE_SIZE) {
      return "파일 크기가 50MB를 초과합니다.";
    }
    return null;
  }, []);

  // 업로드 → AI 추출 파이프라인
  const handleFile = useCallback(
    async (file: File) => {
      const err = validateFile(file);
      if (err) {
        setErrorMsg(err);
        return;
      }

      setSelectedFile(file);
      setErrorMsg(null);
      setStep("uploading");

      try {
        // 1. VDR 미초기화 → 초기화
        let targetFolderId = corporateFolder?.id;
        if (!targetFolderId) {
          const initResult = await initVdr.mutateAsync();
          const corporate = initResult.find((f) => f.category === "CORPORATE");
          targetFolderId = corporate?.id;
          if (!targetFolderId) {
            setStep("failed");
            setErrorMsg("VDR CORPORATE 폴더를 찾을 수 없습니다.");
            return;
          }
          await refetchFolders();
        }

        // 2. 파일 업로드
        const formData = new FormData();
        formData.append("file", file);
        const { data: uploadedDoc } = await maApi.post(
          `/transactions/${txnId}/vdr/folders/${targetFolderId}/documents`,
          formData,
        );

        // 3. VDR 캐시 무효화 (VDR 탭 즉시 반영)
        qc.invalidateQueries({ queryKey: ["ma", "transactions", txnId, "vdr"] });

        // 4. AI 추출 시작
        setStep("classifying");
        const extraction = await createExtraction.mutateAsync(uploadedDoc.id);
        setExtractionId(extraction.id);
        // 이후는 폴링으로 상태 추적
      } catch {
        setStep("failed");
        setErrorMsg("파일 업로드에 실패했습니다.");
      }
    },
    [corporateFolder, initVdr, createExtraction, txnId, validateFile, refetchFolders, qc],
  );

  // 드래그 앤 드롭 핸들러
  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragging(false);
      const file = e.dataTransfer.files[0];
      if (file) handleFile(file);
    },
    [handleFile],
  );

  const handleFileSelect = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) handleFile(file);
      e.target.value = "";
    },
    [handleFile],
  );

  const handleReviewClose = useCallback(() => {
    setReviewOpen(false);
    setReviewExtraction(null);
    setStep("idle");
    setExtractionId(null);
    setSelectedFile(null);
    onComplete?.();
  }, [onComplete]);

  const handleRetry = useCallback(() => {
    setStep("idle");
    setErrorMsg(null);
    setSelectedFile(null);
    setExtractionId(null);
  }, []);

  // ── 진행 상태 UI ──────────────────────────────────────

  if (step !== "idle") {
    const steps = [
      { key: "uploading", label: "파일 업로드" },
      { key: "classifying", label: "AI 분석 중 (문서 분류)" },
      { key: "extracting", label: "데이터 추출" },
      { key: "completed", label: "검토 대기" },
    ];

    const stepIdx = steps.findIndex((s) => s.key === step);

    return (
      <>
        <div className="bg-bg-cool rounded-dr p-6">
          {selectedFile && (
            <div className="flex items-center gap-2 mb-4 pb-3 border-b border-gray-border">
              <FileText size={16} className="text-text-muted" />
              <span className="text-sm font-medium truncate">{selectedFile.name}</span>
            </div>
          )}

          {step === "failed" ? (
            <div className="text-center py-2">
              <AlertCircle size={24} className="mx-auto text-negative mb-2" />
              <p className="text-sm text-negative mb-3">{errorMsg}</p>
              <Button variant="secondary" size="sm" onClick={handleRetry}>
                다시 시도
              </Button>
            </div>
          ) : (
            <div className="space-y-2.5">
              {steps.map((s, i) => {
                const isDone = i < stepIdx || step === "completed";
                const isActive = s.key === step && step !== "completed";
                const isPending = i > stepIdx && step !== "completed";

                return (
                  <div key={s.key} className="flex items-center gap-2.5">
                    {isDone && <CheckCircle2 size={16} className="text-accent shrink-0" />}
                    {isActive && <Loader2 size={16} className="text-accent shrink-0 animate-spin" />}
                    {isPending && (
                      <div className="w-4 h-4 rounded-full border-2 border-gray-border shrink-0" />
                    )}
                    <span
                      className={cn(
                        "text-sm",
                        isDone && "text-text-secondary",
                        isActive && "text-text-body font-medium",
                        isPending && "text-text-muted",
                      )}
                    >
                      {s.label}
                    </span>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        <ExtractionReviewModal
          txnId={txnId}
          extraction={reviewExtraction}
          open={reviewOpen}
          onClose={handleReviewClose}
        />
      </>
    );
  }

  // ── 드래그 & 드롭 업로드 UI ────────────────────────────

  return (
    <div
      className={cn(
        "border-2 border-dashed rounded-dr p-8 text-center transition-colors cursor-pointer",
        dragging
          ? "border-accent bg-accent/5"
          : "border-gray-border hover:border-accent/40 hover:bg-bg-cool",
      )}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      onClick={() => fileInputRef.current?.click()}
    >
      <input
        ref={fileInputRef}
        type="file"
        accept={ACCEPTED_EXTENSIONS}
        className="hidden"
        onChange={handleFileSelect}
      />

      <div className="mx-auto w-12 h-12 rounded-full bg-bg-cool border border-gray-border flex items-center justify-center mb-3">
        <Upload size={20} className={cn(dragging ? "text-accent" : "text-text-muted")} />
      </div>

      <p className="text-sm text-text-secondary mb-1">
        사업자등록증 또는 법인등기부등본을
      </p>
      <p className="text-sm text-text-secondary mb-4">
        드래그하거나 클릭하여 업로드하세요
      </p>

      <Button
        variant="secondary"
        size="sm"
        icon={Upload}
        onClick={(e) => {
          e.stopPropagation();
          fileInputRef.current?.click();
        }}
      >
        파일 선택
      </Button>

      <p className="text-xs text-text-muted mt-3">
        PDF, DOCX, JPG, PNG (최대 50MB)
      </p>

      {errorMsg && (
        <p className="text-xs text-negative mt-2">{errorMsg}</p>
      )}
    </div>
  );
}

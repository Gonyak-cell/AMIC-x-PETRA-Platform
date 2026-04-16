import { AlertTriangle, Loader2, RefreshCw, Upload } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { toast } from "sonner";

import { useQueryClient } from "@tanstack/react-query";

import { extractApiError } from "@/api/errors";
import { maApi } from "@/api/maClient";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { useExtractions } from "@/modules/ma/hooks/useDocumentExtraction";
import {
  useCreateVdrFolder,
  useDeleteVdrFolder,
  useVdrFolders,
  useVdrSummary,
} from "@/modules/ma/hooks/useVdr";
import {
  getVdrUploadEntryState,
  type VdrCompanyInfoDocHint,
} from "@/modules/ma/hooks/useVdrUploadNavigation";
import {
  IN_PROGRESS_STATUSES,
  type DocumentExtraction,
} from "@/modules/ma/types/document_extraction";
import type { DirectUploadBatchResult } from "@/modules/ma/types/vdr";

import ExtractionList from "../extraction/ExtractionList";
import ExtractionReviewModal from "../extraction/ExtractionReviewModal";
import DirectUploadResultModal from "./DirectUploadResultModal";
import DirectUploadZone from "./DirectUploadZone";
import { VdrAccessDashboard } from "./VdrAccessDashboard";
import VdrExplorer from "./VdrExplorer";
import VdrReturnToOriginCard from "./VdrReturnToOriginCard";
import VdrRoutingTriagePanel from "./VdrRoutingTriagePanel";

interface Props {
  txnId: string;
  readOnly?: boolean;
  showReviewTabs?: boolean;
  showExtractionTools?: boolean;
}

function InlineRetryCard({
  title,
  description,
  tone = "warning",
  actionLabel = "Retry",
  onAction,
}: {
  title: string;
  description: string;
  tone?: "warning" | "error";
  actionLabel?: string;
  onAction: () => void;
}) {
  const toneClass =
    tone === "error"
      ? "border-red-200 bg-red-50 text-red-900"
      : "border-amber-200 bg-amber-50 text-amber-900";
  const bodyClass = tone === "error" ? "text-red-800" : "text-amber-800";
  const iconClass = tone === "error" ? "text-red-500" : "text-amber-500";

  return (
    <Card padding="md" className={`border ${toneClass}`}>
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-start gap-3">
          <AlertTriangle className={`mt-0.5 h-4 w-4 shrink-0 ${iconClass}`} />
          <div className="space-y-1">
            <p className="text-sm font-medium">{title}</p>
            <p className={`text-sm ${bodyClass}`}>{description}</p>
          </div>
        </div>
        <Button
          type="button"
          size="sm"
          variant="secondary"
          onClick={onAction}
          className="shrink-0"
        >
          <RefreshCw className="h-4 w-4" />
          {actionLabel}
        </Button>
      </div>
    </Card>
  );
}

function delay(ms: number) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

function isGuidedCompanyInfoDocHint(
  value: string | null,
): value is VdrCompanyInfoDocHint {
  return value === "REGISTRY_DOCS" || value === "BIZ_REG_DOCS";
}

export default function VdrTab({
  txnId,
  readOnly = false,
  showReviewTabs = true,
  showExtractionTools = true,
}: Props) {
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams, setSearchParams] = useSearchParams();
  const qc = useQueryClient();
  const uploadEntryRef = useRef<HTMLDivElement | null>(null);
  const [subTab, setSubTab] = useState<"documents" | "routing" | "access">(
    "documents",
  );
  const [showDirectUpload, setShowDirectUpload] = useState(false);
  const [directUploadResult, setDirectUploadResult] =
    useState<DirectUploadBatchResult | null>(null);
  const [guidedReviewExtraction, setGuidedReviewExtraction] =
    useState<DocumentExtraction | null>(null);
  const [isStartingGuidedExtraction, setIsStartingGuidedExtraction] =
    useState(false);
  const canManageDocuments = !readOnly;
  const canShowReviewTabs = showReviewTabs && !readOnly;
  const canUseExtractionTools = showExtractionTools && !readOnly;

  const summaryQuery = useVdrSummary(txnId);
  const foldersQuery = useVdrFolders(txnId);
  const extractionQuery = useExtractions(
    txnId,
    canUseExtractionTools && subTab === "documents",
  );

  const summary = summaryQuery.data;
  const folders = foldersQuery.data ?? [];
  const extractionData = extractionQuery.data;
  const extractionCount = extractionData?.total ?? 0;

  const createFolder = useCreateVdrFolder(txnId);
  const deleteFolder = useDeleteVdrFolder(txnId);

  const autoInitRef = useRef(false);
  const uploadEntryRefState = useRef(getVdrUploadEntryState(location.state));
  const [isRepairing, setIsRepairing] = useState(false);
  const [initError, setInitError] = useState<string | null>(null);
  const uploadEntryFromLocation = getVdrUploadEntryState(location.state);
  if (uploadEntryFromLocation?.returnTo) {
    uploadEntryRefState.current = uploadEntryFromLocation;
  }
  const uploadEntry = uploadEntryFromLocation ?? uploadEntryRefState.current;
  const wantsUploadEntry = searchParams.get("upload") === "1";
  const rawDocHint = searchParams.get("docHint");
  const docHint = isGuidedCompanyInfoDocHint(rawDocHint)
    ? rawDocHint
    : null;
  const canReturnToOrigin = Boolean(uploadEntry?.returnTo);

  const hasWorkspaceData = summary != null || foldersQuery.data != null;
  const isWorkspaceBootstrapping =
    !hasWorkspaceData && (summaryQuery.isLoading || foldersQuery.isLoading);
  const summaryUnavailable = summaryQuery.isError && summaryQuery.data == null;
  const foldersUnavailable = foldersQuery.isError && foldersQuery.data == null;
  const extractionUnavailable =
    extractionQuery.isError && extractionQuery.data == null;
  const hasWorkspaceLoadFailure = summaryUnavailable || foldersUnavailable;
  const showingStaleWorkspace =
    (summaryQuery.isError && summary != null) ||
    (foldersQuery.isError && foldersQuery.data != null);
  const showingStaleExtractions =
    extractionQuery.isError && extractionQuery.data != null;
  const needsInitialization = Boolean(summary && !summary.initialized);
  const subTabs = canShowReviewTabs
    ? ([
        ["documents", "Documents"],
        ["routing", "Routing"],
        ["access", "Access"],
      ] as const)
    : ([["documents", "Documents"]] as const);

  const repairVdr = useCallback(
    async (manual: boolean) => {
      setIsRepairing(true);
      setInitError(null);
      try {
        await maApi.post(`/transactions/${txnId}/vdr/init`, {});
        sessionStorage.removeItem(`vdr-init-retry-${txnId}`);
        autoInitRef.current = false;
        await qc.invalidateQueries({
          queryKey: ["ma", "transactions", txnId, "vdr"],
        });
        if (manual) {
          toast.success("VDR is ready.");
        }
      } catch (err: unknown) {
        autoInitRef.current = false;
        const message = extractApiError(err, "Failed to initialize VDR.");
        setInitError(message);
        if (manual) {
          toast.error(message);
        }
        throw err;
      } finally {
        setIsRepairing(false);
      }
    },
    [qc, txnId],
  );

  useEffect(() => {
    const storageKey = `vdr-init-retry-${txnId}`;
    const retryCount = Number.parseInt(
      sessionStorage.getItem(storageKey) ?? "0",
      10,
    );
    if (
      summary &&
      !summary.initialized &&
      !autoInitRef.current &&
      retryCount < 3
    ) {
      autoInitRef.current = true;
      sessionStorage.setItem(storageKey, String(retryCount + 1));
      const delay = retryCount > 0 ? Math.min(1000 * 2 ** retryCount, 8000) : 0;
      const timer = window.setTimeout(() => {
        repairVdr(false)
          .catch((err: unknown) => {
            if (import.meta.env.DEV) {
              console.error("[VDR init]", err);
            }
            if (retryCount + 1 >= 3) {
              toast.error("VDR setup still needs attention. Use Repair VDR.");
            } else {
              qc.invalidateQueries({
                queryKey: ["ma", "transactions", txnId, "vdr"],
              });
            }
          });
      }, delay);
      return () => window.clearTimeout(timer);
    }
    return undefined;
  }, [summary, txnId, qc, repairVdr]);

  useEffect(() => {
    if (!summary?.initialized) {
      setShowDirectUpload(false);
    }
  }, [summary?.initialized]);

  useEffect(() => {
    if (!canShowReviewTabs && subTab !== "documents") {
      setSubTab("documents");
    }
  }, [canShowReviewTabs, subTab]);

  useEffect(() => {
    if (!canManageDocuments || !wantsUploadEntry) return;
    setSubTab("documents");
    if (summary?.initialized) {
      setShowDirectUpload(true);
    }
  }, [canManageDocuments, summary?.initialized, wantsUploadEntry]);

  useEffect(() => {
    if (!wantsUploadEntry || !showDirectUpload) return;
    if (typeof uploadEntryRef.current?.scrollIntoView === "function") {
      uploadEntryRef.current.scrollIntoView({
        behavior: "smooth",
        block: "start",
      });
    }
  }, [showDirectUpload, wantsUploadEntry]);

  const clearUploadQuery = useCallback(() => {
    if (!searchParams.has("upload") && !searchParams.has("docHint")) return;
    const next = new URLSearchParams(searchParams);
    next.delete("upload");
    next.delete("docHint");
    setSearchParams(next, { replace: true });
  }, [searchParams, setSearchParams]);

  const waitForExtractionToSettle = useCallback(
    async (extractionId: string) => {
      while (true) {
        const { data } = await maApi.get<DocumentExtraction>(
          `/transactions/${txnId}/extractions/${extractionId}`,
        );
        qc.setQueryData(
          ["ma", "transactions", txnId, "extractions", extractionId],
          data,
        );
        if (!IN_PROGRESS_STATUSES.includes(data.status)) {
          return data;
        }
        await delay(1500);
      }
    },
    [qc, txnId],
  );

  const startGuidedExtractionReview = useCallback(
    async (result: DirectUploadBatchResult, guidedDocHint: VdrCompanyInfoDocHint) => {
      const uploadedDocuments = result.results.map((item) => item.document);
      if (uploadedDocuments.length === 0) {
        setDirectUploadResult(result);
        return;
      }

      setIsStartingGuidedExtraction(true);
      try {
        const createdExtractions = await Promise.all(
          uploadedDocuments.map(async (document) => {
            const { data } = await maApi.post<DocumentExtraction>(
              `/transactions/${txnId}/extractions`,
              {
                vdr_document_id: document.id,
                doc_category_hint: guidedDocHint,
              },
            );
            qc.setQueryData(
              ["ma", "transactions", txnId, "extractions", data.id],
              data,
            );
            return data;
          }),
        );

        await qc.invalidateQueries({
          queryKey: ["ma", "transactions", txnId, "extractions"],
        });

        const settledExtraction = await waitForExtractionToSettle(
          createdExtractions[0].id,
        );

        await qc.invalidateQueries({
          queryKey: ["ma", "transactions", txnId, "extractions"],
        });

        if (
          settledExtraction.status === "COMPLETED" ||
          settledExtraction.status === "CONFIRMED"
        ) {
          setGuidedReviewExtraction(settledExtraction);
          if (createdExtractions.length > 1) {
            toast.info(
              "첫 번째 OCR 검토를 열었습니다. 나머지 문서는 Extraction Results에서 확인할 수 있습니다.",
            );
          }
          return;
        }

        toast.error(
          settledExtraction.error_message ??
            "OCR 처리에 실패했습니다. 문서를 다시 확인해주세요.",
        );
        setDirectUploadResult(result);
      } catch (err: unknown) {
        toast.error(
          extractApiError(err, "OCR 자동 시작에 실패했습니다. 다시 시도해주세요."),
        );
        setDirectUploadResult(result);
      } finally {
        setIsStartingGuidedExtraction(false);
      }
    },
    [qc, txnId, waitForExtractionToSettle],
  );

  const handleDirectUploadComplete = useCallback(
    (result: DirectUploadBatchResult) => {
      clearUploadQuery();
      if (docHint) {
        void startGuidedExtractionReview(result, docHint);
        return;
      }
      setDirectUploadResult(result);
    },
    [clearUploadQuery, docHint, startGuidedExtractionReview],
  );

  const handleCreateFolder = useCallback(
    (name: string, parentId?: string) => {
      createFolder.mutate({ name, parent_id: parentId });
    },
    [createFolder],
  );

  const handleDeleteFolder = useCallback(
    (id: string) => {
      deleteFolder.mutate(id);
    },
    [deleteFolder],
  );

  const handleToggleDirectUpload = useCallback(() => {
    setShowDirectUpload((current) => {
      const next = !current;
      if (!next) {
        clearUploadQuery();
      }
      return next;
    });
  }, [clearUploadQuery]);

  const handleReturnToOrigin = useCallback(() => {
    if (uploadEntry?.returnTo) {
      navigate(uploadEntry.returnTo);
      return;
    }
    navigate(-1);
  }, [navigate, uploadEntry]);

  const handleRetryWorkspace = useCallback(() => {
    void Promise.allSettled([
      summaryQuery.refetch(),
      foldersQuery.refetch(),
      extractionQuery.refetch(),
    ]);
  }, [extractionQuery, foldersQuery, summaryQuery]);

  if (isWorkspaceBootstrapping) {
    return (
      <Card padding="lg">
        <div className="flex h-64 items-center justify-center text-sm text-slate-400">
          Loading VDR...
        </div>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex gap-1 rounded-lg bg-gray-100 p-0.5">
          {subTabs.map(([value, label]) => (
            <button
              key={value}
              type="button"
              onClick={() => setSubTab(value)}
              className={`rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
                subTab === value
                  ? "bg-white text-gray-900 shadow-sm"
                  : "text-gray-500 hover:text-gray-700"
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        {canManageDocuments && summary?.initialized && subTab === "documents" && (
          <Button
            variant="accent"
            size="sm"
            onClick={handleToggleDirectUpload}
            className="flex items-center gap-1.5 whitespace-nowrap"
          >
            <Upload className="h-4 w-4" />
            Quick Upload
          </Button>
        )}
      </div>

      {canShowReviewTabs && subTab === "access" && (
        <VdrAccessDashboard txnId={txnId} />
      )}
      {canShowReviewTabs && subTab === "routing" && (
        <VdrRoutingTriagePanel txnId={txnId} />
      )}

      {subTab === "documents" && (
        <>
          {canReturnToOrigin && (
            <VdrReturnToOriginCard
              returnLabel={uploadEntry?.returnLabel}
              onReturn={handleReturnToOrigin}
            />
          )}

          {hasWorkspaceLoadFailure && (
            <InlineRetryCard
              tone="error"
              title="Some VDR data could not be loaded."
              description={
                summaryUnavailable && foldersUnavailable
                  ? "The VDR summary and folder tree are both unavailable right now."
                  : summaryUnavailable
                    ? "The VDR summary is unavailable, so upload controls stay limited until it reloads."
                    : "The folder tree is unavailable, so browsing is paused until it reloads."
              }
              onAction={handleRetryWorkspace}
            />
          )}

          {showingStaleWorkspace && (
            <InlineRetryCard
              title="Refresh failed, but your last loaded VDR data is still shown."
              description="You can keep working and retry when you need the latest server state."
              actionLabel="Refresh"
              onAction={handleRetryWorkspace}
            />
          )}

          {needsInitialization && (
            <Card padding="md" className="border border-amber-200 bg-amber-50">
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div className="space-y-1">
                  <p className="text-sm font-medium text-amber-900">
                    VDR setup is incomplete.
                  </p>
                  <p className="text-sm text-amber-800">
                    Default folders are being repaired before uploads resume.
                    {initError ? ` ${initError}` : ""}
                  </p>
                </div>
                {canManageDocuments && (
                  <Button
                    type="button"
                    size="sm"
                    variant="secondary"
                    onClick={() => {
                      void repairVdr(true);
                    }}
                    disabled={isRepairing}
                  >
                    {isRepairing ? "Repairing..." : "Repair VDR"}
                  </Button>
                )}
              </div>
            </Card>
          )}

          <div ref={uploadEntryRef}>
            {canManageDocuments && summary?.initialized && showDirectUpload && (
              <DirectUploadZone
                txnId={txnId}
                onUploadComplete={handleDirectUploadComplete}
              />
            )}
          </div>

          {isStartingGuidedExtraction && (
            <Card padding="md" className="border border-sky-200 bg-sky-50">
              <div className="flex items-center gap-3 text-sm text-sky-900">
                <Loader2 className="h-4 w-4 animate-spin text-sky-600" />
                업로드한 문서의 OCR을 시작하고 검토 화면을 준비하고 있습니다.
              </div>
            </Card>
          )}

          {foldersQuery.data != null ? (
            <Card padding="none" className="overflow-hidden">
              <VdrExplorer
                txnId={txnId}
                folders={folders}
                onCreateFolder={handleCreateFolder}
                onDeleteFolder={handleDeleteFolder}
                readOnly={readOnly}
                allowExtractionTools={canUseExtractionTools}
                extractions={extractionData?.items ?? []}
              />
            </Card>
          ) : (
            <InlineRetryCard
              tone="error"
              title="The folder explorer is temporarily unavailable."
              description="Retry loading the folder tree to resume browsing documents."
              onAction={() => {
                void foldersQuery.refetch();
              }}
            />
          )}

          {canUseExtractionTools && extractionUnavailable ? (
            <InlineRetryCard
              title="AI extraction status could not be refreshed."
              description="Document uploads remain available while extraction data reloads."
              onAction={() => {
                void extractionQuery.refetch();
              }}
            />
          ) : canUseExtractionTools && extractionCount > 0 ? (
            <div>
              {showingStaleExtractions && (
                <div className="mb-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">
                  Showing the last loaded extraction results while refresh retries.
                </div>
              )}
              <h3 className="mb-2 text-sm font-semibold text-slate-700">
                AI Extraction Results
              </h3>
              <ExtractionList txnId={txnId} />
            </div>
          ) : null}
        </>
      )}

      {directUploadResult && (
        <DirectUploadResultModal
          open={directUploadResult !== null}
          onClose={() => setDirectUploadResult(null)}
          txnId={txnId}
          result={directUploadResult}
        />
      )}
      {guidedReviewExtraction && (
        <ExtractionReviewModal
          txnId={txnId}
          extraction={guidedReviewExtraction}
          open={guidedReviewExtraction !== null}
          onClose={() => setGuidedReviewExtraction(null)}
          onConfirmed={() => {
            setGuidedReviewExtraction(null);
            handleReturnToOrigin();
          }}
        />
      )}
    </div>
  );
}

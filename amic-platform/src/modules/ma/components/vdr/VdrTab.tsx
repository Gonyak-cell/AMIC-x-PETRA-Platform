import { Upload } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { toast } from "sonner";

import { useQueryClient } from "@tanstack/react-query";

import { extractApiError } from "@/api/errors";
import { maApi } from "@/api/maClient";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { useExtractions } from "@/modules/ma/hooks/useDocumentExtraction";
import { getVdrUploadEntryState } from "@/modules/ma/hooks/useVdrUploadNavigation";
import {
  useCreateVdrFolder,
  useDeleteVdrFolder,
  useVdrFolders,
  useVdrSummary,
} from "@/modules/ma/hooks/useVdr";
import type { DirectUploadBatchResult } from "@/modules/ma/types/vdr";

import ExtractionList from "../extraction/ExtractionList";
import DirectUploadResultModal from "./DirectUploadResultModal";
import DirectUploadZone from "./DirectUploadZone";
import { VdrAccessDashboard } from "./VdrAccessDashboard";
import VdrExplorer from "./VdrExplorer";
import VdrReturnToOriginCard from "./VdrReturnToOriginCard";
import VdrRoutingTriagePanel from "./VdrRoutingTriagePanel";

interface Props {
  txnId: string;
}

export default function VdrTab({ txnId }: Props) {
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams, setSearchParams] = useSearchParams();
  const qc = useQueryClient();
  const { data: summary, isLoading: summaryLoading } = useVdrSummary(txnId);
  const { data: folders = [], isLoading: foldersLoading } =
    useVdrFolders(txnId);
  const createFolder = useCreateVdrFolder(txnId);
  const deleteFolder = useDeleteVdrFolder(txnId);
  const uploadEntryRef = useRef<HTMLDivElement | null>(null);
  const [subTab, setSubTab] = useState<"documents" | "routing" | "access">(
    "documents",
  );
  const [showDirectUpload, setShowDirectUpload] = useState(false);
  const [directUploadResult, setDirectUploadResult] =
    useState<DirectUploadBatchResult | null>(null);

  const autoInitRef = useRef(false);
  const [isRepairing, setIsRepairing] = useState(false);
  const [initError, setInitError] = useState<string | null>(null);
  const uploadEntry = getVdrUploadEntryState(location.state);
  const wantsUploadEntry = searchParams.get("upload") === "1";
  const canReturnToOrigin = Boolean(uploadEntry?.returnTo);

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
    if (!wantsUploadEntry) return;
    setSubTab("documents");
    if (summary?.initialized) {
      setShowDirectUpload(true);
    }
  }, [summary?.initialized, wantsUploadEntry]);

  useEffect(() => {
    if (!wantsUploadEntry || !showDirectUpload) return;
    if (typeof uploadEntryRef.current?.scrollIntoView === "function") {
      uploadEntryRef.current.scrollIntoView({
        behavior: "smooth",
        block: "start",
      });
    }
  }, [showDirectUpload, wantsUploadEntry]);

  const { data: extractionData } = useExtractions(
    txnId,
    subTab === "documents",
  );
  const extractionCount = extractionData?.total ?? 0;
  const needsInitialization = Boolean(summary && !summary.initialized);

  const clearUploadQuery = useCallback(() => {
    if (!searchParams.has("upload")) return;
    const next = new URLSearchParams(searchParams);
    next.delete("upload");
    setSearchParams(next, { replace: true });
  }, [searchParams, setSearchParams]);

  const handleDirectUploadComplete = useCallback(
    (result: DirectUploadBatchResult) => {
      setDirectUploadResult(result);
      setShowDirectUpload(false);
      clearUploadQuery();
    },
    [clearUploadQuery],
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

  if (summaryLoading || foldersLoading) {
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
          {(
            [
              ["documents", "Documents"],
              ["routing", "Routing"],
              ["access", "Access"],
            ] as const
          ).map(([value, label]) => (
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

        {summary && subTab === "documents" && summary.initialized && (
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

      {subTab === "access" && <VdrAccessDashboard txnId={txnId} />}
      {subTab === "routing" && <VdrRoutingTriagePanel txnId={txnId} />}

      {subTab === "documents" && (
        <>
          {canReturnToOrigin && (
            <VdrReturnToOriginCard
              returnLabel={uploadEntry?.returnLabel}
              onReturn={handleReturnToOrigin}
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
              </div>
            </Card>
          )}

          <div ref={uploadEntryRef}>
            {summary?.initialized && showDirectUpload && (
              <DirectUploadZone
                txnId={txnId}
                onUploadComplete={handleDirectUploadComplete}
              />
            )}
          </div>

          <Card padding="none" className="overflow-hidden">
            <VdrExplorer
              txnId={txnId}
              folders={folders}
              onCreateFolder={handleCreateFolder}
              onDeleteFolder={handleDeleteFolder}
              extractions={extractionData?.items ?? []}
            />
          </Card>

          {extractionCount > 0 && (
            <div>
              <h3 className="mb-2 text-sm font-semibold text-slate-700">
                AI Extraction Results
              </h3>
              <ExtractionList txnId={txnId} />
            </div>
          )}
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
    </div>
  );
}

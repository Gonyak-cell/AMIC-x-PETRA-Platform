import { Upload } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "sonner";

import { useQueryClient } from "@tanstack/react-query";

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
import type { DirectUploadBatchResult } from "@/modules/ma/types/vdr";

import ExtractionList from "../extraction/ExtractionList";
import DirectUploadResultModal from "./DirectUploadResultModal";
import DirectUploadZone from "./DirectUploadZone";
import { VdrAccessDashboard } from "./VdrAccessDashboard";
import VdrExplorer from "./VdrExplorer";
import VdrRoutingTriagePanel from "./VdrRoutingTriagePanel";

interface Props {
  txnId: string;
}

export default function VdrTab({ txnId }: Props) {
  const qc = useQueryClient();
  const { data: summary, isLoading: summaryLoading } = useVdrSummary(txnId);
  const { data: folders = [], isLoading: foldersLoading } =
    useVdrFolders(txnId);
  const createFolder = useCreateVdrFolder(txnId);
  const deleteFolder = useDeleteVdrFolder(txnId);

  const autoInitRef = useRef(false);
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
        maApi
          .post(`/transactions/${txnId}/vdr/init`, {})
          .then(() => {
            sessionStorage.removeItem(storageKey);
            qc.invalidateQueries({
              queryKey: ["ma", "transactions", txnId, "vdr"],
            });
          })
          .catch((err: unknown) => {
            if (import.meta.env.DEV) {
              console.error("[VDR init]", err);
            }
            autoInitRef.current = false;
            if (retryCount + 1 >= 3) {
              toast.error("Failed to initialize VDR. Please refresh and retry.");
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
  }, [summary, txnId, qc]);

  const [subTab, setSubTab] = useState<"documents" | "routing" | "access">(
    "documents",
  );
  const [showDirectUpload, setShowDirectUpload] = useState(false);
  const [directUploadResult, setDirectUploadResult] =
    useState<DirectUploadBatchResult | null>(null);

  const { data: extractionData } = useExtractions(
    txnId,
    subTab === "documents",
  );
  const extractionCount = extractionData?.total ?? 0;

  const handleDirectUploadComplete = useCallback(
    (result: DirectUploadBatchResult) => {
      setDirectUploadResult(result);
      setShowDirectUpload(false);
    },
    [],
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

        {summary && subTab === "documents" && (
          <Button
            variant="accent"
            size="sm"
            onClick={() => setShowDirectUpload((current) => !current)}
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
          {showDirectUpload && (
            <DirectUploadZone
              txnId={txnId}
              onUploadComplete={handleDirectUploadComplete}
            />
          )}

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

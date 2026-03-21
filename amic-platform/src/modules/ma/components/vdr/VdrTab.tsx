import { Upload } from "lucide-react";
import { useState, useCallback, useRef, useEffect } from "react";
import { toast } from "sonner";

import { useQueryClient } from "@tanstack/react-query";

import { maApi } from "@/api/maClient";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";

import { useExtractions } from "@/modules/ma/hooks/useDocumentExtraction";
import {
  useVdrSummary,
  useVdrFolders,
  useCreateVdrFolder,
  useDeleteVdrFolder,
} from "@/modules/ma/hooks/useVdr";
import type { DirectUploadBatchResult } from "@/modules/ma/types/vdr";

import ExtractionList from "../extraction/ExtractionList";
import DirectUploadResultModal from "./DirectUploadResultModal";
import DirectUploadZone from "./DirectUploadZone";
import { VdrAccessDashboard } from "./VdrAccessDashboard";
import VdrExplorer from "./VdrExplorer";

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

  // 기존 미초기화 거래 자동 처리 (최대 3회 재시도, sessionStorage 기반)
  const autoInitRef = useRef(false);
  useEffect(() => {
    const storageKey = `vdr-init-retry-${txnId}`;
    const retryCount = parseInt(sessionStorage.getItem(storageKey) ?? "0", 10);
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
            if (import.meta.env.DEV) console.error("[VDR init]", err);
            autoInitRef.current = false;
            if (retryCount + 1 >= 3) {
              toast.error(
                "VDR 초기화에 실패했습니다. 새로고침 후 다시 시도해 주세요.",
              );
            } else {
              qc.invalidateQueries({
                queryKey: ["ma", "transactions", txnId, "vdr"],
              });
            }
          });
      }, delay);
      return () => window.clearTimeout(timer);
    }
  }, [summary, txnId, qc]);

  const [subTab, setSubTab] = useState<"documents" | "access">("documents");
  const [showDirectUpload, setShowDirectUpload] = useState(false);
  const [directUploadResult, setDirectUploadResult] =
    useState<DirectUploadBatchResult | null>(null);

  const { data: extractionData } = useExtractions(txnId, subTab === "documents");
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

  // ── 로딩 ──────────────────────────────────────────────
  if (summaryLoading || foldersLoading) {
    return (
      <Card padding="lg">
        <div className="flex h-64 items-center justify-center text-sm text-slate-400">
          불러오는 중...
        </div>
      </Card>
    );
  }

  // ── 초기화 완료 상태 ──────────────────────────────────
  return (
    <div className="space-y-4">
      {/* 서브탭: 문서 관리 / 접근 현황 */}
      <div className="flex items-center justify-between">
        <div className="flex gap-1 rounded-lg bg-gray-100 p-0.5">
          <button
            type="button"
            onClick={() => setSubTab("documents")}
            className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
              subTab === "documents"
                ? "bg-white text-gray-900 shadow-sm"
                : "text-gray-500 hover:text-gray-700"
            }`}
          >
            문서 관리
          </button>
          <button
            type="button"
            onClick={() => setSubTab("access")}
            className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
              subTab === "access"
                ? "bg-white text-gray-900 shadow-sm"
                : "text-gray-500 hover:text-gray-700"
            }`}
          >
            접근 현황
          </button>
        </div>

        {/* 빠른 업로드 버튼 */}
        {summary && subTab === "documents" && (
          <Button
            variant="accent"
            size="sm"
            onClick={() => setShowDirectUpload(!showDirectUpload)}
            className="flex items-center gap-1.5 whitespace-nowrap"
          >
            <Upload className="h-4 w-4" />
            빠른 업로드
          </Button>
        )}
      </div>

      {/* 접근 현황 탭 */}
      {subTab === "access" && <VdrAccessDashboard txnId={txnId} />}

      {/* 문서 관리 탭 컨텐츠 */}
      {subTab === "documents" && (
        <>
          {/* 빠른 업로드 영역 (토글) */}
          {showDirectUpload && (
            <DirectUploadZone
              txnId={txnId}
              onUploadComplete={handleDirectUploadComplete}
            />
          )}

          {/* 파일 탐색기 */}
          <Card padding="none" className="overflow-hidden">
            <VdrExplorer
              txnId={txnId}
              folders={folders}
              onCreateFolder={handleCreateFolder}
              onDeleteFolder={handleDeleteFolder}
              extractions={extractionData?.items ?? []}
            />
          </Card>

          {/* AI 분석 결과 */}
          {extractionCount > 0 && (
            <div>
              <h3 className="mb-2 text-sm font-semibold text-slate-700">
                AI 문서 분석 결과
              </h3>
              <ExtractionList txnId={txnId} />
            </div>
          )}
        </>
      )}

      {/* Direct Upload 결과 모달 */}
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

import { Upload } from "lucide-react";
import { useState, useMemo, useCallback, useRef, useEffect } from "react";
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
  useVdrDocuments,
  useVdrAllDocuments,
  useUploadVdrDocument,
  useDeleteVdrDocument,
} from "@/modules/ma/hooks/useVdr";
import type {
  VdrFolder,
  DirectUploadBatchResult,
} from "@/modules/ma/types/vdr";

import ExtractionList from "../extraction/ExtractionList";
import VdrQAPanel from "../VdrQAPanel";
import DirectUploadResultModal from "./DirectUploadResultModal";
import DirectUploadZone from "./DirectUploadZone";
import { VdrAccessDashboard } from "./VdrAccessDashboard";
import VdrDocumentList from "./VdrDocumentList";
import VdrFolderTree from "./VdrFolderTree";

interface Props {
  txnId: string;
}

/** flat tree에서 id로 폴더를 재귀 검색 */
function findFolder(folders: VdrFolder[], id: string): VdrFolder | null {
  for (const f of folders) {
    if (f.id === id) return f;
    const found = findFolder(f.children, id);
    if (found) return found;
  }
  return null;
}

/** flat tree를 folder_id → folder_name 맵으로 변환 */
function buildFolderMap(folders: VdrFolder[]): Map<string, string> {
  const map = new Map<string, string>();
  function walk(list: VdrFolder[]) {
    for (const f of list) {
      map.set(f.id, f.name);
      walk(f.children);
    }
  }
  walk(folders);
  return map;
}

/** flat tree에서 category로 폴더를 검색 */
function findFolderByCategory(
  folders: VdrFolder[],
  category: string,
): VdrFolder | null {
  for (const f of folders) {
    if (f.category === category) return f;
    const found = findFolderByCategory(f.children, category);
    if (found) return found;
  }
  return null;
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
  const [selectedFolderId, setSelectedFolderId] = useState<string | null>(null);
  const [showDirectUpload, setShowDirectUpload] = useState(false);
  const [directUploadResult, setDirectUploadResult] =
    useState<DirectUploadBatchResult | null>(null);

  // ── 리사이즈 상태 ─────────────────────────────────────
  const [topHeight, setTopHeight] = useState(520);
  const isDragging = useRef(false);

  const handleMouseDown = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault();
      isDragging.current = true;
      const startY = e.clientY;
      const startHeight = topHeight;

      const onMouseMove = (ev: MouseEvent) => {
        if (!isDragging.current) return;
        const delta = ev.clientY - startY;
        setTopHeight(Math.max(200, Math.min(800, startHeight + delta)));
      };

      const onMouseUp = () => {
        isDragging.current = false;
        document.removeEventListener("mousemove", onMouseMove);
        document.removeEventListener("mouseup", onMouseUp);
      };

      document.addEventListener("mousemove", onMouseMove);
      document.addEventListener("mouseup", onMouseUp);
    },
    [topHeight],
  );

  const selectedFolder = useMemo(
    () => (selectedFolderId ? findFolder(folders, selectedFolderId) : null),
    [folders, selectedFolderId],
  );

  const { data: documents = [], isLoading: docsLoading } = useVdrDocuments(
    txnId,
    selectedFolderId,
  );

  const { data: allDocuments = [], isLoading: allDocsLoading } =
    useVdrAllDocuments(txnId, !selectedFolderId);

  const folderMap = useMemo(() => buildFolderMap(folders), [folders]);

  const uploadDoc = useUploadVdrDocument(txnId, selectedFolderId ?? "");
  const deleteDoc = useDeleteVdrDocument(txnId);
  const { data: extractionData } = useExtractions(txnId);
  const extractionCount = extractionData?.total ?? 0;

  const handleDirectUploadComplete = useCallback(
    (result: DirectUploadBatchResult) => {
      setDirectUploadResult(result);
      setShowDirectUpload(false);
    },
    [],
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

          {/* 2-column 레이아웃 + 하단 Q&A */}
          <div className="flex flex-col">
            {/* 상단: 폴더 트리 + 문서 목록 */}
            <div
              className="grid grid-cols-[280px_1fr] gap-4 items-start overflow-hidden"
              style={{ maxHeight: topHeight }}
            >
              <Card
                padding="none"
                className="overflow-hidden"
                style={{ maxHeight: topHeight }}
              >
                <VdrFolderTree
                  folders={folders}
                  selectedFolderId={selectedFolderId}
                  onSelectFolder={setSelectedFolderId}
                  onCreateFolder={(name, parentId) =>
                    createFolder.mutate({ name, parent_id: parentId })
                  }
                  onDeleteFolder={(id) => {
                    if (selectedFolderId === id) setSelectedFolderId(null);
                    deleteFolder.mutate(id);
                  }}
                />
              </Card>

              <Card
                padding="none"
                className="overflow-hidden"
                style={{ maxHeight: topHeight }}
              >
                <VdrDocumentList
                  txnId={txnId}
                  folder={selectedFolder}
                  documents={selectedFolder ? documents : allDocuments}
                  extractions={extractionData?.items ?? []}
                  isLoading={selectedFolder ? docsLoading : allDocsLoading}
                  isUploading={uploadDoc.isPending}
                  onUpload={(file) => uploadDoc.mutate(file)}
                  onDelete={(docId) => deleteDoc.mutate(docId)}
                  folderMap={selectedFolder ? undefined : folderMap}
                  onNavigateToFolder={(category) => {
                    const target = findFolderByCategory(folders, category);
                    if (target) setSelectedFolderId(target.id);
                  }}
                />
              </Card>
            </div>

            {/* 드래그 리사이즈 핸들 */}
            <div
              role="separator"
              aria-orientation="horizontal"
              aria-label="패널 크기 조절"
              tabIndex={0}
              className="h-2 flex items-center justify-center cursor-row-resize group hover:bg-accent/10 my-2 rounded focus:outline-none focus:ring-2 focus:ring-accent/50"
              onMouseDown={handleMouseDown}
              onKeyDown={(e) => {
                if (e.key === "ArrowUp") {
                  e.preventDefault();
                  setTopHeight((h) => Math.max(200, h - 40));
                } else if (e.key === "ArrowDown") {
                  e.preventDefault();
                  setTopHeight((h) => Math.min(800, h + 40));
                }
              }}
            >
              <div className="w-12 h-1 rounded-full bg-border group-hover:bg-accent/40 transition-colors" />
            </div>

            {/* 하단: Q&A 패널 */}
            <div className="min-h-[300px]">
              <VdrQAPanel txnId={txnId} />
            </div>
          </div>

          {/* AI 분석 결과 */}
          {extractionCount > 0 && (
            <div>
              <h3 className="text-sm font-semibold text-slate-700 mb-2">
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

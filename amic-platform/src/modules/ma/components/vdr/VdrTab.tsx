import {
  FolderLock,
  HardDrive,
  Files,
  FolderTree,
  Sparkles,
} from "lucide-react";
import { useState, useMemo } from "react";

import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { KpiCard } from "@/components/ui/KpiCard";
import { useExtractions } from "@/modules/ma/hooks/useDocumentExtraction";
import {
  useVdrSummary,
  useVdrFolders,
  useInitVdr,
  useCreateVdrFolder,
  useDeleteVdrFolder,
  useVdrDocuments,
  useUploadVdrDocument,
  useDeleteVdrDocument,
} from "@/modules/ma/hooks/useVdr";
import type { VdrFolder } from "@/modules/ma/types/vdr";

import ExtractionList from "../extraction/ExtractionList";
import VdrDocumentList from "./VdrDocumentList";
import VdrFolderTree from "./VdrFolderTree";

interface Props {
  txnId: string;
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  if (bytes < 1024 * 1024 * 1024)
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
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
  const { data: summary, isLoading: summaryLoading } = useVdrSummary(txnId);
  const { data: folders = [], isLoading: foldersLoading } =
    useVdrFolders(txnId);
  const initVdr = useInitVdr(txnId);
  const createFolder = useCreateVdrFolder(txnId);
  const deleteFolder = useDeleteVdrFolder(txnId);

  const [selectedFolderId, setSelectedFolderId] = useState<string | null>(null);

  const selectedFolder = useMemo(
    () => (selectedFolderId ? findFolder(folders, selectedFolderId) : null),
    [folders, selectedFolderId],
  );

  const { data: documents = [], isLoading: docsLoading } = useVdrDocuments(
    txnId,
    selectedFolderId,
  );

  const uploadDoc = useUploadVdrDocument(txnId, selectedFolderId ?? "");
  const deleteDoc = useDeleteVdrDocument(txnId);
  const { data: extractionData } = useExtractions(txnId);
  const extractionCount = extractionData?.total ?? 0;

  // ── 초기화 전 상태 ────────────────────────────────────
  if (!summaryLoading && summary && !summary.initialized) {
    return (
      <Card padding="lg">
        <div className="flex flex-col items-center gap-4 py-12 text-center">
          <FolderLock className="h-12 w-12 text-slate-300" />
          <div>
            <h3 className="text-lg font-semibold text-slate-700">
              VDR (Virtual Data Room)
            </h3>
            <p className="mt-1 text-sm text-slate-500">
              실사 자료실을 초기화하면 M&A 실사에 필요한 11개 기본 폴더가
              자동으로 생성됩니다.
            </p>
          </div>
          <Button
            variant="primary"
            onClick={() => initVdr.mutate()}
            disabled={initVdr.isPending}
          >
            {initVdr.isPending ? "초기화 중..." : "VDR 초기화"}
          </Button>
        </div>
      </Card>
    );
  }

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
      {/* KPI 요약 */}
      {summary && (
        <div className="grid grid-cols-4 gap-4">
          <KpiCard
            label="폴더"
            value={String(summary.total_folders)}
            icon={FolderTree}
          />
          <KpiCard
            label="문서"
            value={String(summary.total_documents)}
            icon={Files}
          />
          <KpiCard
            label="총 용량"
            value={formatBytes(summary.total_size_bytes)}
            icon={HardDrive}
          />
          <KpiCard
            label="AI 분석"
            value={String(extractionCount)}
            icon={Sparkles}
          />
        </div>
      )}

      {/* 2-column 레이아웃 */}
      <div className="grid grid-cols-[280px_1fr] gap-4">
        {/* 좌측: 폴더 트리 */}
        <Card padding="none" className="h-[520px] overflow-hidden">
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

        {/* 우측: 문서 목록 */}
        <Card padding="none" className="h-[520px] overflow-hidden">
          <VdrDocumentList
            txnId={txnId}
            folder={selectedFolder}
            documents={documents}
            isLoading={docsLoading}
            onUpload={(file) => uploadDoc.mutate(file)}
            onDelete={(docId) => deleteDoc.mutate(docId)}
            onNavigateToFolder={(category) => {
              const target = findFolderByCategory(folders, category);
              if (target) setSelectedFolderId(target.id);
            }}
          />
        </Card>
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
    </div>
  );
}

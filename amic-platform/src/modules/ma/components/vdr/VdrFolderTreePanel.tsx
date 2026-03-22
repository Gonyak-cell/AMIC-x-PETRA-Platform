import { Database, FolderOpen } from "lucide-react";
import { useMemo } from "react";

import type { VdrFolder } from "@/modules/ma/types/vdr";

import VdrFolderTreeNode from "./VdrFolderTreeNode";

interface VdrFolderTreePanelProps {
  childrenByParentId: Map<string | null, VdrFolder[]>;
  folderById: Map<string, VdrFolder>;
  currentFolderId: string | null;
  onNavigate: (folderId: string | null) => void;
}

export default function VdrFolderTreePanel({
  childrenByParentId,
  folderById,
  currentFolderId,
  onNavigate,
}: VdrFolderTreePanelProps) {
  const rootFolders = childrenByParentId.get(null) ?? [];

  // 현재 선택된 폴더의 조상 id Set 계산 (자동 펼침용)
  const ancestorIds = useMemo(() => {
    const ids = new Set<string>();
    if (!currentFolderId) return ids;
    let current = folderById.get(currentFolderId);
    while (current?.parent_id) {
      ids.add(current.parent_id);
      current = folderById.get(current.parent_id);
    }
    return ids;
  }, [currentFolderId, folderById]);

  const isRootSelected = currentFolderId === null;

  return (
    <div className="flex w-60 shrink-0 flex-col border-r border-slate-200 bg-white">
      {/* 루트 노드 */}
      <button
        type="button"
        className={`flex items-center gap-1.5 px-3 py-2 text-left text-xs font-medium transition-colors ${
          isRootSelected
            ? "bg-accent/10 text-accent"
            : "text-slate-700 hover:bg-slate-50"
        }`}
        onClick={() => onNavigate(null)}
      >
        <Database className="h-3.5 w-3.5 shrink-0" />
        <span>VDR</span>
      </button>

      {/* 폴더 트리 */}
      <div className="flex-1 overflow-y-auto px-1 py-1">
        {rootFolders.length === 0 && (
          <div className="flex flex-col items-center gap-2 px-3 py-6 text-center text-slate-400">
            <FolderOpen className="h-5 w-5 text-slate-300" />
            <p className="text-[11px] font-medium text-slate-500">
              아직 표시할 폴더가 없습니다
            </p>
            <p className="text-[10px] leading-4 text-slate-400">
              새 폴더를 만들면 이 영역에 바로 나타납니다.
            </p>
          </div>
        )}
        {rootFolders.map((folder) => (
          <VdrFolderTreeNode
            key={folder.id}
            folder={folder}
            childrenByParentId={childrenByParentId}
            depth={0}
            currentFolderId={currentFolderId}
            ancestorIds={ancestorIds}
            onNavigate={onNavigate}
          />
        ))}
      </div>
    </div>
  );
}

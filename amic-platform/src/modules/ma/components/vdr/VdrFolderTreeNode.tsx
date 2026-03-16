import { ChevronDown, ChevronRight, Folder } from "lucide-react";
import { useEffect, useState } from "react";

import type { VdrFolder } from "@/modules/ma/types/vdr";

interface VdrFolderTreeNodeProps {
  folder: VdrFolder;
  childrenByParentId: Map<string | null, VdrFolder[]>;
  depth: number;
  currentFolderId: string | null;
  /** currentFolderId의 조상 id Set — 자동 펼침용 */
  ancestorIds: Set<string>;
  onNavigate: (folderId: string | null) => void;
}

export default function VdrFolderTreeNode({
  folder,
  childrenByParentId,
  depth,
  currentFolderId,
  ancestorIds,
  onNavigate,
}: VdrFolderTreeNodeProps) {
  const children = childrenByParentId.get(folder.id) ?? [];
  const hasChildren = children.length > 0;
  const isSelected = currentFolderId === folder.id;

  // 조상 경로에 있으면 자동 펼침
  const [expanded, setExpanded] = useState(
    ancestorIds.has(folder.id) || isSelected,
  );

  // currentFolderId가 바뀌어 조상 경로에 포함되면 자동 펼침
  useEffect(() => {
    if (ancestorIds.has(folder.id)) {
      setExpanded(true);
    }
  }, [ancestorIds, folder.id]);

  return (
    <div>
      <button
        type="button"
        className={`flex w-full items-center gap-1 rounded-md px-1.5 py-1 text-left text-xs transition-colors ${
          isSelected
            ? "bg-blue-50 font-medium text-blue-700"
            : "text-slate-600 hover:bg-slate-50"
        }`}
        style={{ paddingLeft: `${8 + depth * 16}px` }}
        onClick={() => onNavigate(folder.id)}
      >
        {/* 펼침/접힘 토글 */}
        {hasChildren ? (
          <span
            className="shrink-0 rounded p-0.5 hover:bg-slate-200"
            onClick={(e) => {
              e.stopPropagation();
              setExpanded((prev) => !prev);
            }}
            role="button"
            tabIndex={-1}
          >
            {expanded ? (
              <ChevronDown className="h-3 w-3" />
            ) : (
              <ChevronRight className="h-3 w-3" />
            )}
          </span>
        ) : (
          <span className="w-4 shrink-0" />
        )}

        <Folder
          className={`h-3.5 w-3.5 shrink-0 ${isSelected ? "text-blue-500 fill-blue-100" : "text-amber-400 fill-amber-100"}`}
        />

        <span className="min-w-0 truncate">{folder.name}</span>

        {folder.is_required && (
          <span className="text-[10px] font-bold text-negative leading-none">
            *
          </span>
        )}

        {folder.document_count > 0 && (
          <span className="ml-auto shrink-0 text-[10px] text-slate-400">
            {folder.document_count}
          </span>
        )}
      </button>

      {/* 자식 폴더 재귀 렌더 */}
      {expanded &&
        hasChildren &&
        children.map((child) => (
          <VdrFolderTreeNode
            key={child.id}
            folder={child}
            childrenByParentId={childrenByParentId}
            depth={depth + 1}
            currentFolderId={currentFolderId}
            ancestorIds={ancestorIds}
            onNavigate={onNavigate}
          />
        ))}
    </div>
  );
}

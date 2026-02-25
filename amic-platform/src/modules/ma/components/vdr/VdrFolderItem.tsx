import { ChevronDown, ChevronRight, Folder, FolderOpen, Trash2 } from "lucide-react";
import { useState } from "react";

import type { VdrFolder } from "@/modules/ma/types/vdr";

interface Props {
  folder: VdrFolder;
  depth: number;
  selectedId: string | null;
  onSelect: (id: string) => void;
  onDelete?: (id: string) => void;
}

export default function VdrFolderItem({
  folder,
  depth,
  selectedId,
  onSelect,
  onDelete,
}: Props) {
  const [expanded, setExpanded] = useState(depth === 0);
  const hasChildren = folder.children.length > 0;
  const isSelected = selectedId === folder.id;

  return (
    <div>
      <button
        type="button"
        className={`group flex w-full items-center gap-1.5 rounded-md px-2 py-1.5 text-sm transition-colors hover:bg-slate-100 ${
          isSelected ? "bg-slate-100 font-medium text-slate-900" : "text-slate-700"
        }`}
        style={{ paddingLeft: `${depth * 16 + 8}px` }}
        onClick={() => {
          onSelect(folder.id);
          if (hasChildren) setExpanded((v) => !v);
        }}
      >
        {/* expand/collapse */}
        <span className="w-4 shrink-0">
          {hasChildren &&
            (expanded ? (
              <ChevronDown className="h-3.5 w-3.5 text-slate-400" />
            ) : (
              <ChevronRight className="h-3.5 w-3.5 text-slate-400" />
            ))}
        </span>

        {/* icon */}
        {isSelected ? (
          <FolderOpen className="h-4 w-4 shrink-0 text-amber-500" />
        ) : (
          <Folder className="h-4 w-4 shrink-0 text-slate-400" />
        )}

        {/* name */}
        <span className="truncate">{folder.name}</span>

        {/* required badge */}
        {folder.is_required && (
          <span className="text-[10px] text-red-400">*</span>
        )}

        {/* doc count */}
        {folder.document_count > 0 && (
          <span className="ml-auto rounded-full bg-slate-200 px-1.5 py-0.5 text-[10px] font-medium text-slate-600">
            {folder.document_count}
          </span>
        )}

        {/* delete btn (non-required only) */}
        {!folder.is_required && onDelete && (
          <button
            type="button"
            aria-label={`${folder.name} 폴더 삭제`}
            className="ml-1 rounded p-0.5 opacity-0 transition-opacity group-hover:opacity-100 hover:text-negative focus-visible:opacity-100 focus-visible:ring-2 focus-visible:ring-blue-400"
            onClick={(e) => {
              e.stopPropagation();
              onDelete(folder.id);
            }}
            onKeyDown={(e) => {
              if (e.key === " ") {
                e.preventDefault();
                e.stopPropagation();
                onDelete(folder.id);
              }
            }}
          >
            <Trash2 className="h-3.5 w-3.5" />
          </button>
        )}
      </button>

      {/* children */}
      {expanded &&
        folder.children.map((child) => (
          <VdrFolderItem
            key={child.id}
            folder={child}
            depth={depth + 1}
            selectedId={selectedId}
            onSelect={onSelect}
            onDelete={onDelete}
          />
        ))}
    </div>
  );
}

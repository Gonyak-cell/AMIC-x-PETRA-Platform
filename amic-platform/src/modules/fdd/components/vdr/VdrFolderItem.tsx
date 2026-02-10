import { useState } from "react";
import { Folder, FolderOpen, ChevronRight, ChevronDown } from "lucide-react";
import { cn } from "@/lib/cn";
import type { VdrFolder } from "@/modules/fdd/types/vdr";

interface VdrFolderItemProps {
  folder: VdrFolder;
  dealId: string;
  depth?: number;
  onSelect: (folderId: string) => void;
}

export default function VdrFolderItem({
  folder,
  dealId,
  depth = 0,
  onSelect,
}: VdrFolderItemProps) {
  const [expanded, setExpanded] = useState(depth < 1);
  const hasChildren = folder.children && folder.children.length > 0;

  return (
    <div>
      <button
        onClick={() => {
          onSelect(folder.id);
          if (hasChildren) setExpanded((prev) => !prev);
        }}
        className={cn(
          "w-full flex items-center gap-2 px-3 py-2 text-sm rounded-lg hover:bg-bg-cool transition-colors text-left",
          "min-h-[40px]"
        )}
        style={{ paddingLeft: `${12 + depth * 20}px` }}
      >
        {/* Expand/collapse icon */}
        {hasChildren ? (
          expanded ? (
            <ChevronDown className="h-4 w-4 text-text-secondary flex-shrink-0" />
          ) : (
            <ChevronRight className="h-4 w-4 text-text-secondary flex-shrink-0" />
          )
        ) : (
          <span className="w-4 flex-shrink-0" />
        )}

        {/* Folder icon */}
        {expanded && hasChildren ? (
          <FolderOpen className="h-4 w-4 text-caution flex-shrink-0" />
        ) : (
          <Folder className="h-4 w-4 text-caution flex-shrink-0" />
        )}

        {/* Folder name */}
        <span className="flex-1 text-text-dark truncate">
          {folder.name}
          {folder.is_required && (
            <span className="text-negative ml-1">*</span>
          )}
        </span>

        {/* File count badge */}
        {folder.file_count > 0 && (
          <span className="inline-flex items-center px-1.5 py-0.5 rounded text-xs bg-bg-cool text-text-secondary">
            {folder.file_count}
          </span>
        )}
      </button>

      {/* Children */}
      {expanded && hasChildren && (
        <div>
          {folder.children.map((child) => (
            <VdrFolderItem
              key={child.id}
              folder={child}
              dealId={dealId}
              depth={depth + 1}
              onSelect={onSelect}
            />
          ))}
        </div>
      )}
    </div>
  );
}

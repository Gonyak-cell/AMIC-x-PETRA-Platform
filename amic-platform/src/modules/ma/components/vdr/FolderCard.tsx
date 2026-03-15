import { Folder, Trash2 } from "lucide-react";

import type { VdrFolder } from "@/modules/ma/types/vdr";

interface FolderCardProps {
  folder: VdrFolder;
  onOpen: (folderId: string) => void;
  onDelete?: (folderId: string) => void;
}

export default function FolderCard({
  folder,
  onOpen,
  onDelete,
}: FolderCardProps) {
  return (
    <div
      role="button"
      tabIndex={0}
      className="group relative flex flex-col items-center gap-1.5 rounded-lg border border-slate-200 bg-white p-3 text-left transition-all hover:border-slate-300 hover:shadow-sm w-full cursor-pointer"
      onClick={() => onOpen(folder.id)}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onOpen(folder.id);
        }
      }}
    >
      {folder.is_required && (
        <span
          className="absolute right-1.5 top-1.5 text-xs font-bold text-negative leading-none"
          title="필수 폴더"
        >
          *
        </span>
      )}

      <Folder className="h-8 w-8 text-amber-400 fill-amber-100" />

      <p
        className="line-clamp-2 w-full text-center text-xs font-medium text-slate-700 leading-tight"
        title={folder.name}
      >
        {folder.name}
      </p>

      <span className="text-[10px] text-slate-400">
        {folder.document_count}개 파일
      </span>

      {!folder.is_required && onDelete && (
        <div className="absolute inset-0 flex items-end justify-center pb-1.5 opacity-0 transition-opacity group-hover:opacity-100">
          <button
            type="button"
            className="rounded p-0.5 text-slate-400 hover:bg-red-50 hover:text-negative"
            title="폴더 삭제"
            onClick={(e) => {
              e.stopPropagation();
              if (window.confirm(folder.name + " 폴더를 삭제하시겠습니까?"))
                onDelete(folder.id);
            }}
          >
            <Trash2 className="h-3.5 w-3.5" />
          </button>
        </div>
      )}
    </div>
  );
}

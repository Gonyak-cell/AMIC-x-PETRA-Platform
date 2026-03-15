import { ChevronRight, FolderPlus, Home, Upload } from "lucide-react";

import { Button } from "@/components/ui/Button";

interface Breadcrumb {
  id: string | null;
  name: string;
}

interface ExplorerToolbarProps {
  breadcrumbs: Breadcrumb[];
  onNavigate: (folderId: string | null) => void;
  onCreateFolder: () => void;
  currentFolderId: string | null;
  isUploading: boolean;
  onUploadClick: () => void;
}

export default function ExplorerToolbar({
  breadcrumbs,
  onNavigate,
  onCreateFolder,
  currentFolderId,
  isUploading,
  onUploadClick,
}: ExplorerToolbarProps) {
  return (
    <div className="flex items-center justify-between gap-2 border-b border-slate-100 px-4 py-2">
      {/* Breadcrumb */}
      <nav className="flex items-center gap-0.5 text-xs text-slate-500 flex-1 min-w-0 overflow-hidden">
        {breadcrumbs.map((crumb, idx) => (
          <span
            key={crumb.id ?? "root"}
            className="flex items-center gap-0.5 min-w-0"
          >
            {idx > 0 && (
              <ChevronRight className="h-3 w-3 flex-shrink-0 text-slate-300" />
            )}
            {idx === breadcrumbs.length - 1 ? (
              <span className="font-medium text-slate-700 truncate">
                {crumb.id === null ? (
                  <Home className="h-3.5 w-3.5 inline -mt-0.5" />
                ) : (
                  crumb.name
                )}
              </span>
            ) : (
              <button
                type="button"
                className="hover:text-slate-800 hover:underline truncate flex-shrink-0"
                aria-label={crumb.id === null ? "홈" : crumb.name}
                onClick={() => onNavigate(crumb.id)}
              >
                {crumb.id === null ? (
                  <Home className="h-3.5 w-3.5 inline -mt-0.5" />
                ) : (
                  crumb.name
                )}
              </button>
            )}
          </span>
        ))}
      </nav>

      {/* Actions */}
      <div className="flex items-center gap-1.5 flex-shrink-0">
        <Button
          variant="ghost"
          size="sm"
          onClick={onCreateFolder}
          className="flex items-center gap-1 text-xs"
        >
          <FolderPlus className="h-3.5 w-3.5" />새 폴더
        </Button>
        <Button
          variant="secondary"
          size="sm"
          disabled={currentFolderId === null || isUploading}
          onClick={onUploadClick}
          className="flex items-center gap-1 text-xs"
        >
          <Upload className="h-3.5 w-3.5" />
          업로드
        </Button>
      </div>
    </div>
  );
}

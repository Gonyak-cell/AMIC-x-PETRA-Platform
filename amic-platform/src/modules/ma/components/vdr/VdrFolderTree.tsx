import { FolderPlus } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/Button";
import type { VdrFolder } from "@/modules/ma/types/vdr";

import VdrFolderItem from "./VdrFolderItem";

interface Props {
  folders: VdrFolder[];
  selectedFolderId: string | null;
  onSelectFolder: (id: string) => void;
  onCreateFolder: (name: string, parentId?: string) => void;
  onDeleteFolder: (id: string) => void;
}

export default function VdrFolderTree({
  folders,
  selectedFolderId,
  onSelectFolder,
  onCreateFolder,
  onDeleteFolder,
}: Props) {
  const [newFolderName, setNewFolderName] = useState("");
  const [showInput, setShowInput] = useState(false);

  const handleCreate = () => {
    const trimmed = newFolderName.trim();
    if (!trimmed) return;
    onCreateFolder(trimmed);
    setNewFolderName("");
    setShowInput(false);
  };

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between border-b border-slate-200 px-3 py-2">
        <h3 className="text-sm font-semibold text-slate-700">폴더</h3>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setShowInput((v) => !v)}
        >
          <FolderPlus className="h-4 w-4" />
        </Button>
      </div>

      {showInput && (
        <div className="flex items-center gap-1 border-b border-slate-100 px-3 py-2">
          <input
            type="text"
            value={newFolderName}
            onChange={(e) => setNewFolderName(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") handleCreate();
              if (e.key === "Escape") setShowInput(false);
            }}
            placeholder="새 폴더 이름"
            className="flex-1 rounded border border-slate-300 px-2 py-1 text-sm focus:border-blue-400 focus:outline-none"
            autoFocus
          />
          <Button variant="primary" size="sm" onClick={handleCreate}>
            추가
          </Button>
        </div>
      )}

      <div className="flex-1 overflow-y-auto py-1">
        {folders.map((folder) => (
          <VdrFolderItem
            key={folder.id}
            folder={folder}
            depth={0}
            selectedId={selectedFolderId}
            onSelect={onSelectFolder}
            onDelete={onDeleteFolder}
          />
        ))}
      </div>
    </div>
  );
}

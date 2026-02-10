import type { VdrFolder } from "@/modules/fdd/types/vdr";
import VdrFolderItem from "./VdrFolderItem";

interface VdrFolderTreeProps {
  folders: VdrFolder[];
  dealId: string;
  onFolderSelect: (folderId: string) => void;
}

export default function VdrFolderTree({
  folders,
  dealId,
  onFolderSelect,
}: VdrFolderTreeProps) {
  return (
    <div className="space-y-0.5">
      {folders.map((folder) => (
        <VdrFolderItem
          key={folder.id}
          folder={folder}
          dealId={dealId}
          onSelect={onFolderSelect}
        />
      ))}
    </div>
  );
}

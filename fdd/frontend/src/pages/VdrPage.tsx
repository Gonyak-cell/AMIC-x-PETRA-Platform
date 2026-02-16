import { useState } from "react";
import { useParams } from "react-router-dom";
import { FolderOpen, FileText } from "lucide-react";
import { toast } from "sonner";
import { Card, Spinner, EmptyState } from "@/components/ui";
import { useVdrFolders, useInitializeVdr } from "@/hooks/useVdr";
import VdrFolderTree from "@/components/vdr/VdrFolderTree";

export default function VdrPage() {
  const { dealId } = useParams<{ dealId: string }>();
  const { data: folders = [], isLoading } = useVdrFolders(dealId!);
  const initializeVdr = useInitializeVdr(dealId!);
  const [selectedFolderId, setSelectedFolderId] = useState<string | null>(null);

  const handleInitialize = async () => {
    try {
      await initializeVdr.mutateAsync();
      toast.success("VDR initialized successfully");
    } catch {
      toast.error("Failed to initialize VDR");
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Spinner size="lg" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-heading font-bold text-text-dark">
          Virtual Data Room
        </h1>
        <p className="text-text-secondary mt-1">
          Manage VDR folder structure and uploaded files.
        </p>
      </div>

      {folders.length === 0 ? (
        /* Empty state — VDR not initialized */
        <Card>
          <EmptyState
            icon={FolderOpen}
            title="VDR Not Initialized"
            description="Initialize the Virtual Data Room to create the default folder structure for this deal."
            actionLabel="Initialize VDR"
            onAction={handleInitialize}
          />
        </Card>
      ) : (
        /* Two-column layout */
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left: Folder Tree */}
          <Card title="Folders" padding="sm" className="lg:col-span-1">
            <VdrFolderTree
              folders={folders}
              dealId={dealId!}
              onFolderSelect={(folderId) => setSelectedFolderId(folderId)}
            />
          </Card>

          {/* Right: File list */}
          <Card title="Files" padding="sm" className="lg:col-span-2">
            {selectedFolderId ? (
              <div className="py-8 text-center">
                <p className="text-text-secondary text-sm">
                  File listing for the selected folder will be available in a future update.
                </p>
              </div>
            ) : (
              <EmptyState
                icon={FileText}
                title="Select a Folder"
                description="Choose a folder from the tree on the left to view its files."
              />
            )}
          </Card>
        </div>
      )}
    </div>
  );
}

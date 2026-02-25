import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { FolderOpen, FileText, Play } from "lucide-react";
import { toast } from "sonner";
import { Card, Button, Spinner, EmptyState, PageHero } from "@/components/ui";
import { useVdrFolders, useInitializeVdr } from "@/modules/fdd/hooks/useVdr";
import { useRunAnalysis } from "@/modules/fdd/hooks/useAnalysis";
import VdrFolderTree from "@/modules/fdd/components/vdr/VdrFolderTree";
import heroImg from "@/assets/images/heroes/hero-arch-diamond.jpg";

export default function VdrPage() {
  const navigate = useNavigate();
  const { dealId } = useParams<{ dealId: string }>();
  const { data: folders = [], isLoading } = useVdrFolders(dealId!);
  const initializeVdr = useInitializeVdr(dealId!);
  const runAnalysis = useRunAnalysis(dealId!);
  const [selectedFolderId, setSelectedFolderId] = useState<string | null>(null);

  const handleRunAnalysis = async () => {
    try {
      await runAnalysis.mutateAsync();
      toast.success("Auto analysis started — redirecting to checklist");
      navigate(`/fdd/deals/${dealId}/checklist`);
    } catch {
      toast.error("Failed to start analysis");
    }
  };

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
      <PageHero
        title="Virtual Data Room"
        subtitle="Manage VDR folder structure and uploaded files."
        compact
        backgroundImage={heroImg}
        backgroundOpacity={0.18}
        actions={
          folders.length > 0 ? (
            <Button
              variant="primary"
              icon={Play}
              onClick={handleRunAnalysis}
              loading={runAnalysis.isPending}
            >
              Run Auto Analysis
            </Button>
          ) : undefined
        }
      />

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

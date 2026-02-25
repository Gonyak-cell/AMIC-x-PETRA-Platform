import { useParams } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Lock, Play } from "lucide-react";
import { Card, Button, Spinner, EmptyState, PageHero, Badge } from "@/components/ui";
import ChecklistSummaryBar from "@/modules/fdd/components/checklist/ChecklistSummaryBar";
import ChecklistCategorySection from "@/modules/fdd/components/checklist/ChecklistCategorySection";
import {
  useChecklist,
  useUpdateChecklistItem,
  useFinalizeChecklist,
  CATEGORY_GROUPS,
} from "@/modules/fdd/hooks/useChecklist";
import type { ChecklistItemStatus } from "@/modules/fdd/hooks/useChecklist";
import { useRunAnalysis } from "@/modules/fdd/hooks/useAnalysis";
import heroImg from "@/assets/images/heroes/hero-arch-teal.jpg";

export default function ChecklistReviewPage() {
  const { dealId } = useParams<{ dealId: string }>();
  const queryClient = useQueryClient();
  const { data: checklist, isLoading, error } = useChecklist(dealId!);
  const updateItem = useUpdateChecklistItem(dealId!);
  const finalize = useFinalizeChecklist(dealId!);
  const runAnalysis = useRunAnalysis(dealId!);

  const handleUpdateItem = (
    itemId: string,
    status: ChecklistItemStatus,
    correction?: string,
    amount?: string
  ) => {
    updateItem.mutate(
      {
        itemId,
        update: {
          status,
          user_correction: correction || null,
          user_amount: amount || null,
        },
      },
      {
        onSuccess: () => toast.success("Item updated"),
        onError: () => toast.error("Failed to update item"),
      }
    );
  };

  const handleFinalize = () => {
    if (!checklist) return;
    finalize.mutate(
      { checklistId: checklist.id },
      {
        onSuccess: () => toast.success("Checklist finalized"),
        onError: (e) =>
          toast.error(e instanceof Error ? e.message : "Finalize failed"),
      }
    );
  };

  const handleRunAnalysis = () => {
    runAnalysis.mutate(undefined, {
      onSuccess: () => {
        toast.success("Auto analysis started — checklist will be generated");
        queryClient.invalidateQueries({ queryKey: ["fdd", "checklist", dealId] });
        queryClient.invalidateQueries({ queryKey: ["fdd", "analysis", dealId] });
      },
      onError: () => toast.error("Failed to start analysis"),
    });
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Spinner size="lg" />
      </div>
    );
  }

  if (error || !checklist) {
    return (
      <div className="space-y-6">
        <PageHero
          title="FDD Checklist"
          subtitle="Review and verify auto-generated findings"
          compact
          backgroundImage={heroImg}
          backgroundOpacity={0.18}
        />
        <Card>
          <EmptyState
            icon={Play}
            title="No Checklist Available"
            description="Run auto analysis from the VDR page to generate the FDD checklist."
            actionLabel="Run Auto Analysis"
            onAction={handleRunAnalysis}
          />
        </Card>
      </div>
    );
  }

  const isFinalized = checklist.status === "FINALIZED";

  return (
    <div className="space-y-6">
      <PageHero
        title="FDD Checklist Review"
        subtitle={`Version ${checklist.version} — ${checklist.status.replace(/_/g, " ")}`}
        compact
        backgroundImage={heroImg}
        backgroundOpacity={0.18}
        actions={
          !isFinalized ? (
            <Button
              variant="primary"
              icon={Lock}
              onClick={handleFinalize}
              loading={finalize.isPending}
            >
              Finalize Checklist
            </Button>
          ) : (
            <Badge variant="success">Finalized</Badge>
          )
        }
      />

      {/* Summary bar */}
      <ChecklistSummaryBar checklist={checklist} />

      {/* Category sections */}
      <div className="space-y-4">
        {Object.entries(CATEGORY_GROUPS).map(([groupName, categories]) => {
          const items = checklist.items.filter((item) =>
            (categories as readonly string[]).includes(item.category)
          );
          if (!items.length) return null;
          return (
            <ChecklistCategorySection
              key={groupName}
              groupName={groupName}
              items={items}
              dealId={dealId!}
              onUpdateItem={handleUpdateItem}
              isUpdating={updateItem.isPending}
            />
          );
        })}
      </div>
    </div>
  );
}

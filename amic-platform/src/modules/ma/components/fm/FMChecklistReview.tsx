import { useCallback } from "react";
import { CheckCircle, Loader2 } from "lucide-react";
import { Button, Spinner } from "@/components/ui";
import FMChecklistSummaryBar from "./FMChecklistSummaryBar";
import FMChecklistCategorySection from "./FMChecklistCategorySection";
import { useFMChecklist, useUpdateFMChecklistItem, useBulkUpdateFMItems, useFinalizeFMChecklist } from "@/modules/ma/hooks/useFMChecklist";
import type { FMChecklistItemStatus, FMChecklistCategory } from "@/modules/ma/types/financial_model";
import { FM_CATEGORY_GROUPS } from "@/modules/ma/types/financial_model";

interface Props {
  txnId: string;
  fmId: string;
}

export default function FMChecklistReview({ txnId, fmId }: Props) {
  const { data: checklist, isLoading, error } = useFMChecklist(txnId, fmId);
  const updateItem = useUpdateFMChecklistItem(txnId, fmId);
  const bulkUpdate = useBulkUpdateFMItems(txnId, fmId);
  const finalize = useFinalizeFMChecklist(txnId, fmId);

  const handleUpdateItem = useCallback(
    (itemId: string, body: { status: FMChecklistItemStatus; user_correction?: string | null; user_value?: string | null }) => {
      updateItem.mutate({ itemId, update: body });
    },
    [updateItem],
  );

  const handleConfirmAllInGroup = useCallback(
    (itemIds: string[]) => {
      if (!checklist) return;
      bulkUpdate.mutate({
        checklistId: checklist.id,
        items: itemIds.map((id) => ({ item_id: id, status: "CONFIRMED" as FMChecklistItemStatus })),
      });
    },
    [checklist, bulkUpdate],
  );

  const handleFinalize = useCallback(() => {
    if (!checklist) return;
    finalize.mutate({ checklistId: checklist.id });
  }, [checklist, finalize]);

  if (isLoading) return <Spinner size="lg" />;
  if (error || !checklist) {
    return (
      <div className="text-center py-12 text-text-muted">
        체크리스트를 불러올 수 없습니다.
      </div>
    );
  }

  const isFinalized = checklist.status === "FINALIZED";
  const canFinalize = checklist.pending_count === 0 && !isFinalized;

  return (
    <div className="space-y-6">
      {/* Summary Bar */}
      <FMChecklistSummaryBar checklist={checklist} />

      {/* Category Sections */}
      {Object.entries(FM_CATEGORY_GROUPS).map(([groupName, categories]) => (
        <FMChecklistCategorySection
          key={groupName}
          groupName={groupName}
          categories={categories as FMChecklistCategory[]}
          items={checklist.items}
          onUpdateItem={handleUpdateItem}
          onConfirmAllInGroup={handleConfirmAllInGroup}
          isUpdating={updateItem.isPending || bulkUpdate.isPending}
        />
      ))}

      {/* Finalize Button */}
      {!isFinalized && (
        <div className="flex items-center justify-end gap-3 pt-4 border-t border-gray-border">
          {!canFinalize && (
            <span className="text-xs text-text-secondary">
              모든 항목을 리뷰해야 Finalize할 수 있습니다 ({checklist.pending_count}개 대기)
            </span>
          )}
          <Button
            icon={finalize.isPending ? Loader2 : CheckCircle}
            onClick={handleFinalize}
            disabled={!canFinalize || finalize.isPending}
            loading={finalize.isPending}
          >
            Finalize — 최종 Excel 생성
          </Button>
        </div>
      )}

      {isFinalized && (
        <div className="flex items-center gap-2 p-4 bg-emerald-50 rounded-lg border border-emerald-200">
          <CheckCircle className="h-5 w-5 text-emerald-600" />
          <span className="text-sm text-emerald-700 font-medium">
            체크리스트가 확정되었습니다. 최종 Excel이 생성 중입니다.
          </span>
        </div>
      )}
    </div>
  );
}

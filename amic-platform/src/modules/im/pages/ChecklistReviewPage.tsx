import { useMemo, useState, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import {
  ArrowLeft,
  CheckCircle,
  Loader2,
  AlertTriangle,
  FileText,
  RefreshCw,
} from "lucide-react";
import {
  Button,
  Card,
  Breadcrumbs,
  Tabs,
  Spinner,
  Modal,
  PageHero,
} from "@/components/ui";
import type { BreadcrumbItem, TabItem } from "@/components/ui";
import { ChecklistProgressBar } from "@/modules/im/components/ChecklistProgressBar";
import { ChecklistTable } from "@/modules/im/components/ChecklistTable";
import {
  useChecklist,
  useChecklistSummary,
  useUpdateChecklistItem,
  useBatchUpdateItems,
  useConfirmChecklist,
} from "@/modules/im/hooks/useChecklist";
import type {
  ChecklistCategory,
  ChecklistItem,
} from "@/modules/im/types/checklist";
import {
  CHECKLIST_CATEGORIES,
  CHECKLIST_IN_PROGRESS_STATUSES,
} from "@/modules/im/types/checklist";
import heroImg from "@/assets/images/heroes/forestgp-vc.jpg";

// ── Component ───────────────────────────────────────────────

export default function ChecklistReviewPage() {
  const { documentId } = useParams<{ documentId: string }>();
  const navigate = useNavigate();
  const [activeCategory, setActiveCategory] = useState<ChecklistCategory>("FINANCIAL");
  const [showConfirmModal, setShowConfirmModal] = useState(false);

  // ── Data fetching ──────────────────────────────────────────

  const {
    data: checklist,
    isLoading: checklistLoading,
    isError: checklistError,
  } = useChecklist(documentId ?? "");

  const { data: summary } = useChecklistSummary(documentId ?? "");

  const updateItem = useUpdateChecklistItem(documentId ?? "");
  const batchUpdate = useBatchUpdateItems(documentId ?? "");
  const confirmChecklist = useConfirmChecklist(documentId ?? "");

  // ── Derived state ──────────────────────────────────────────

  const isProcessing =
    checklist?.status &&
    CHECKLIST_IN_PROGRESS_STATUSES.includes(checklist.status);

  const isReviewable = checklist?.status === "REVIEW";

  const itemsByCategory = useMemo(() => {
    if (!checklist?.items) return new Map<ChecklistCategory, ChecklistItem[]>();
    const map = new Map<ChecklistCategory, ChecklistItem[]>();
    for (const item of checklist.items) {
      const existing = map.get(item.category) ?? [];
      existing.push(item);
      map.set(item.category, existing);
    }
    return map;
  }, [checklist?.items]);

  const categoryItems = useMemo(
    () => itemsByCategory.get(activeCategory) ?? [],
    [itemsByCategory, activeCategory],
  );

  // Tab definitions with badges showing item counts
  const categoryTabs: TabItem[] = useMemo(
    () =>
      CHECKLIST_CATEGORIES.map(({ id, label }) => {
        const items = itemsByCategory.get(id) ?? [];
        const unconfirmed = items.filter(
          (it) =>
            it.status !== "CONFIRMED" &&
            it.status !== "MODIFIED" &&
            it.status !== "NOT_APPLICABLE",
        ).length;
        return {
          id,
          label,
          badge: unconfirmed > 0 ? unconfirmed : undefined,
        };
      }),
    [itemsByCategory],
  );

  // Completion check
  const allItemsConfirmed = useMemo(() => {
    if (!checklist?.items || checklist.items.length === 0) return false;
    return checklist.items.every(
      (it) =>
        it.status === "CONFIRMED" ||
        it.status === "MODIFIED" ||
        it.status === "NOT_APPLICABLE",
    );
  }, [checklist?.items]);

  // ── Handlers ───────────────────────────────────────────────

  const handleUpdateItem = useCallback(
    (
      itemId: string,
      body: Partial<Pick<ChecklistItem, "confirmed_value" | "status" | "notes">>,
    ) => {
      updateItem.mutate({ itemId, body });
    },
    [updateItem],
  );

  const handleConfirmAllInCategory = useCallback(
    (category: ChecklistCategory) => {
      const items = itemsByCategory.get(category) ?? [];
      const toConfirm = items
        .filter(
          (it) =>
            it.status !== "CONFIRMED" &&
            it.status !== "MODIFIED" &&
            it.status !== "NOT_APPLICABLE",
        )
        .map((it) => ({
          item_id: it.id,
          status: "CONFIRMED" as const,
          confirmed_value: it.confirmed_value ?? it.extracted_value ?? "",
        }));
      if (toConfirm.length === 0) {
        toast.info("All items in this category are already confirmed");
        return;
      }
      batchUpdate.mutate(toConfirm);
    },
    [itemsByCategory, batchUpdate],
  );

  const handleConfirmChecklist = useCallback(() => {
    confirmChecklist.mutate(undefined, {
      onSuccess: () => {
        setShowConfirmModal(false);
        navigate(`/im/documents/${documentId}`);
      },
    });
  }, [confirmChecklist, navigate, documentId]);

  // ── Breadcrumbs ────────────────────────────────────────────

  const breadcrumbs: BreadcrumbItem[] = [
    { label: "IM Projects", href: "/im" },
    { label: "Document", href: `/im/documents/${documentId}` },
    { label: "Checklist Review" },
  ];

  // ── Loading / Error states ─────────────────────────────────

  if (checklistLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Spinner />
      </div>
    );
  }

  if (checklistError || !checklist) {
    return (
      <div className="space-y-6">
        <Breadcrumbs items={breadcrumbs} />
        <div className="text-center py-12">
          <AlertTriangle className="h-10 w-10 text-negative mx-auto mb-3" />
          <p className="text-negative font-medium">
            Failed to load checklist
          </p>
          <p className="text-sm text-text-secondary mt-1">
            The checklist may not exist yet for this document.
          </p>
          <Button
            variant="ghost"
            className="mt-4"
            onClick={() => navigate(`/im/documents/${documentId}`)}
          >
            Back to Document
          </Button>
        </div>
      </div>
    );
  }

  // ── Processing overlay ─────────────────────────────────────

  if (isProcessing) {
    return (
      <div className="space-y-6">
        <Breadcrumbs items={breadcrumbs} />
        <PageHero
          title="Checklist Review"
          subtitle="VDR data extraction in progress"
          backgroundImage={heroImg}
          backgroundOpacity={0.18}
          compact
          actions={
            <Button
              variant="ghost"
              size="sm"
              icon={ArrowLeft}
              onClick={() => navigate(`/im/documents/${documentId}`)}
            >
              Back
            </Button>
          }
        />
        <Card>
          <div className="flex flex-col items-center justify-center py-16 space-y-4">
            <Loader2 className="h-10 w-10 text-accent animate-spin" />
            <h3 className="text-lg font-heading font-semibold text-text-dark">
              {checklist.status === "EXTRACTING"
                ? "Extracting data from VDR documents..."
                : "Generating IM document..."}
            </h3>
            <p className="text-sm text-text-secondary max-w-md text-center">
              {checklist.status === "EXTRACTING"
                ? "The system is analyzing your VDR documents and extracting relevant data points. This may take a few minutes."
                : "The confirmed checklist data is being used to generate your Investment Memorandum."}
            </p>
            <span className="text-xs text-text-secondary animate-pulse">
              Auto-refreshing every 3 seconds...
            </span>
          </div>
        </Card>
      </div>
    );
  }

  // ── Main render ────────────────────────────────────────────

  return (
    <div className="space-y-6">
      <Breadcrumbs items={breadcrumbs} />

      <PageHero
        title="Checklist Review"
        subtitle="Review and confirm extracted data before generating IM"
        backgroundImage={heroImg}
        backgroundOpacity={0.18}
        compact
        actions={
          <Button
            variant="ghost"
            size="sm"
            icon={ArrowLeft}
            onClick={() => navigate(`/im/documents/${documentId}`)}
          >
            Back to Document
          </Button>
        }
      />

      {/* Progress Overview */}
      <Card title="Completion Progress" headerBar>
        <ChecklistProgressBar
          status={checklist.status}
          totalItems={summary?.total_items ?? checklist.total_items}
          confirmedItems={summary?.confirmed_items ?? checklist.confirmed_items}
          missingItems={summary?.missing_items ?? checklist.missing_items}
          completionPct={summary?.completion_pct ?? 0}
          categories={summary?.categories}
        />
      </Card>

      {/* Category Tabs + Table */}
      <Card padding="none">
        <div className="px-5 pt-4 pb-0">
          <Tabs
            tabs={categoryTabs}
            activeTab={activeCategory}
            onTabChange={(id) => setActiveCategory(id as ChecklistCategory)}
            size="sm"
          />
        </div>

        <div
          role="tabpanel"
          id={`tabpanel-${activeCategory}`}
          aria-labelledby={`tab-${activeCategory}`}
        >
          <ChecklistTable
            items={categoryItems}
            category={activeCategory}
            onUpdateItem={handleUpdateItem}
            onConfirmAllInCategory={handleConfirmAllInCategory}
            isUpdating={updateItem.isPending || batchUpdate.isPending}
          />
        </div>
      </Card>

      {/* Bottom Action Bar */}
      {isReviewable && (
        <div className="sticky bottom-0 z-10 bg-white/95 backdrop-blur-sm border-t border-gray-border py-4 px-6 -mx-6 flex items-center justify-between">
          <div className="text-sm">
            {allItemsConfirmed ? (
              <span className="flex items-center gap-2 text-positive font-medium">
                <CheckCircle className="h-4 w-4" />
                All items confirmed - ready to generate
              </span>
            ) : (
              <span className="text-text-secondary">
                Confirm all items to enable IM generation
              </span>
            )}
          </div>
          <Button
            variant="accent"
            size="lg"
            icon={FileText}
            onClick={() => setShowConfirmModal(true)}
            disabled={!allItemsConfirmed}
          >
            Confirm Checklist & Generate IM
          </Button>
        </div>
      )}

      {/* Completed / Failed states */}
      {checklist.status === "COMPLETED" && (
        <Card>
          <div className="flex items-center gap-4 py-2">
            <CheckCircle className="h-8 w-8 text-positive flex-shrink-0" />
            <div>
              <h3 className="font-heading font-semibold text-text-dark">
                IM Generation Complete
              </h3>
              <p className="text-sm text-text-secondary">
                Your Investment Memorandum has been generated. You can download it
                from the document detail page.
              </p>
            </div>
            <Button
              variant="primary"
              onClick={() => navigate(`/im/documents/${documentId}`)}
              className="ml-auto flex-shrink-0"
            >
              View Document
            </Button>
          </div>
        </Card>
      )}

      {checklist.status === "FAILED" && (
        <Card>
          <div className="flex items-center gap-4 py-2">
            <AlertTriangle className="h-8 w-8 text-negative flex-shrink-0" />
            <div>
              <h3 className="font-heading font-semibold text-negative">
                Generation Failed
              </h3>
              <p className="text-sm text-text-secondary">
                An error occurred during IM generation. Please try again.
              </p>
            </div>
            <Button
              variant="primary"
              icon={RefreshCw}
              onClick={() => navigate(`/im/documents/${documentId}`)}
              className="ml-auto flex-shrink-0"
            >
              Back to Document
            </Button>
          </div>
        </Card>
      )}

      {/* Confirm Modal */}
      <Modal
        open={showConfirmModal}
        onClose={() => setShowConfirmModal(false)}
        title="Confirm Checklist & Generate IM"
        footer={
          <>
            <Button
              variant="ghost"
              onClick={() => setShowConfirmModal(false)}
            >
              Cancel
            </Button>
            <Button
              variant="accent"
              icon={FileText}
              onClick={handleConfirmChecklist}
              loading={confirmChecklist.isPending}
            >
              Confirm & Generate
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <p className="text-sm text-text-dark">
            You are about to finalize the checklist and start IM generation.
            This action will:
          </p>
          <ul className="space-y-2 text-sm text-text-secondary">
            <li className="flex items-start gap-2">
              <CheckCircle className="h-4 w-4 text-positive mt-0.5 flex-shrink-0" />
              Lock the checklist (no further edits)
            </li>
            <li className="flex items-start gap-2">
              <FileText className="h-4 w-4 text-amic mt-0.5 flex-shrink-0" />
              Generate the IM document using confirmed data
            </li>
            <li className="flex items-start gap-2">
              <Loader2 className="h-4 w-4 text-text-secondary mt-0.5 flex-shrink-0" />
              Generation typically takes 2-5 minutes
            </li>
          </ul>

          {/* Summary stats */}
          <div className="bg-bg-cool rounded-lg p-3 grid grid-cols-3 gap-3 text-center">
            <div>
              <p className="text-lg font-semibold text-accent">
                {checklist.confirmed_items}
              </p>
              <p className="text-[10px] text-text-secondary">Confirmed</p>
            </div>
            <div>
              <p className="text-lg font-semibold text-text-dark">
                {checklist.total_items}
              </p>
              <p className="text-[10px] text-text-secondary">Total</p>
            </div>
            <div>
              <p className="text-lg font-semibold text-negative">
                {checklist.missing_items}
              </p>
              <p className="text-[10px] text-text-secondary">Missing</p>
            </div>
          </div>
        </div>
      </Modal>
    </div>
  );
}

import { useMemo, useState } from "react";
import { User } from "lucide-react";
import { EmptyState } from "@/components/ui";
import type { BuyerCandidate } from "@/modules/ma/types/buyer";
import type { BuyerStageSummary } from "@/modules/ma/types/marketing_log";
import type { ShortListViewMode } from "./ShortListViewToggle";
import { isShortListed } from "@/modules/ma/constants";
import ShortListMasterList from "./ShortListMasterList";
import ShortListSummaryBar from "./ShortListSummaryBar";
import ShortListViewToggle from "./ShortListViewToggle";
import MarketingGridView from "./MarketingGridView";
import MarketingKanbanView from "./MarketingKanbanView";
import MarketingTimelineView from "./MarketingTimelineView";
import BuyerDetailPanel from "./BuyerDetailPanel";

interface ShortListOverviewProps {
  txnId: string;
  buyers: BuyerCandidate[];
  overviewData: BuyerStageSummary[];
  canWrite: boolean;
}

export default function ShortListOverview({
  txnId,
  buyers,
  overviewData,
  canWrite,
}: ShortListOverviewProps) {
  const [viewMode, setViewMode] = useState<ShortListViewMode>("grid");
  const [selectedBuyerId, setSelectedBuyerId] = useState<string | null>(null);

  const shortListBuyers = useMemo(
    () => buyers.filter(isShortListed),
    [buyers],
  );

  const selectedBuyer = useMemo(
    () => shortListBuyers.find((b) => b.id === selectedBuyerId) ?? null,
    [shortListBuyers, selectedBuyerId],
  );

  const summaryMap = useMemo(
    () => new Map(overviewData.map((s) => [s.buyer_id, s])),
    [overviewData],
  );

  if (!shortListBuyers.length) {
    return (
      <EmptyState
        icon={User}
        title="Short List 후보 없음"
        description="Long List에서 체크박스를 선택하면 여기에 표시됩니다."
      />
    );
  }

  const viewProps = {
    buyers: shortListBuyers,
    overviewData,
    onSelectBuyer: setSelectedBuyerId,
    canWrite,
    txnId,
  };

  return (
    <div className="flex gap-4">
      {/* Left sidebar — Master List */}
      <div className="w-64 flex-shrink-0 border-r border-gray-border pr-4">
        <ShortListMasterList
          buyers={shortListBuyers}
          overviewData={overviewData}
          selectedBuyerId={selectedBuyerId}
          onSelectBuyer={setSelectedBuyerId}
          totalBuyerCount={buyers.length}
        />
      </div>

      {/* Main content */}
      <div className="flex-1 min-w-0 space-y-4">
        <h2 className="text-lg font-semibold text-text-dark">
          마케팅 활동 추적
        </h2>

        {/* KPI Summary Bar */}
        <ShortListSummaryBar
          buyers={shortListBuyers}
          overviewData={overviewData}
        />

        {/* View Toggle */}
        <div className="flex justify-end">
          <ShortListViewToggle
            viewMode={viewMode}
            onViewModeChange={setViewMode}
          />
        </div>

        {/* View Content */}
        {viewMode === "grid" && <MarketingGridView {...viewProps} />}
        {viewMode === "kanban" && <MarketingKanbanView {...viewProps} />}
        {viewMode === "timeline" && <MarketingTimelineView {...viewProps} />}
      </div>

      {/* Right slide panel — Buyer Detail */}
      <BuyerDetailPanel
        txnId={txnId}
        buyer={selectedBuyer}
        stageSummary={summaryMap.get(selectedBuyerId ?? "")}
        onClose={() => setSelectedBuyerId(null)}
        canWrite={canWrite}
      />
    </div>
  );
}

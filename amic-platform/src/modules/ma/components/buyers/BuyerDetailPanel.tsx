import { useEffect, useRef, useState } from "react";
import { SlidePanel, Tabs } from "@/components/ui";
import type { TabItem } from "@/components/ui/Tabs";
import type { BuyerCandidate } from "@/modules/ma/types/buyer";
import type { BuyerStageSummary } from "@/modules/ma/types/marketing_log";
import { BUYER_TYPE_OPTIONS } from "@/modules/ma/constants";
import BuyerSummarySection from "./BuyerSummarySection";
import BuyerMeetingTimeline from "./BuyerMeetingTimeline";
import MaterialTracker from "./MaterialTracker";
import BuyerFeedbackSection from "./BuyerFeedbackSection";
import { CommentThread } from "@/components/collaboration/CommentThread";

interface BuyerDetailPanelProps {
  txnId: string;
  buyer: BuyerCandidate | null;
  stageSummary: BuyerStageSummary | undefined;
  onClose: () => void;
  canWrite: boolean;
  onToggleDrop?: (buyerId: string, isCurrentlyDropped: boolean) => void;
}

const TABS: TabItem[] = [
  { id: "summary", label: "요약" },
  { id: "meetings", label: "미팅" },
  { id: "materials", label: "자료" },
  { id: "feedback", label: "피드백" },
  { id: "comments", label: "댓글" },
];

function getBuyerTypeLabel(buyerType: string): string {
  const option = BUYER_TYPE_OPTIONS.find((o) => o.value === buyerType);
  return option?.label ?? buyerType;
}

export default function BuyerDetailPanel({
  txnId,
  buyer,
  stageSummary,
  onClose,
  canWrite,
  onToggleDrop,
}: BuyerDetailPanelProps) {
  const [activeTab, setActiveTab] = useState("summary");
  const contentRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setActiveTab("summary");
    contentRef.current?.scrollTo(0, 0);
  }, [buyer?.id]);

  const isOpen = !!buyer;
  const isDropped = buyer?.status === "BID_DROPPED";

  return (
    <SlidePanel
      open={isOpen}
      onClose={onClose}
      title={buyer?.company_name ?? ""}
      subtitle={buyer ? getBuyerTypeLabel(buyer.buyer_type) : undefined}
      width="xl"
    >
      {buyer && (
        <div ref={contentRef} className="flex flex-col h-full overflow-y-auto">
          {/* Drop 토글 버튼 */}
          {canWrite && onToggleDrop && (
            <div className="px-1 pt-2 pb-1">
              <button
                type="button"
                onClick={() => onToggleDrop(buyer.id, isDropped)}
                className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-medium transition-colors ${
                  isDropped
                    ? "bg-green-50 text-green-700 hover:bg-green-100"
                    : "bg-red-50 text-red-600 hover:bg-red-100"
                }`}
              >
                {isDropped ? "↩ 복구" : "✕ Drop 처리"}
              </button>
            </div>
          )}

          <Tabs
            tabs={TABS}
            activeTab={activeTab}
            onTabChange={setActiveTab}
            variant="underline"
            size="sm"
          />

          <div className="mt-4 flex-1 min-h-0">
            {activeTab === "summary" && (
              <BuyerSummarySection
                buyer={buyer}
                txnId={txnId}
                stageSummary={stageSummary}
              />
            )}
            {activeTab === "meetings" && (
              <BuyerMeetingTimeline txnId={txnId} buyerId={buyer.id} />
            )}
            {activeTab === "materials" && (
              <MaterialTracker
                txnId={txnId}
                buyerId={buyer.id}
                stageSummary={stageSummary}
              />
            )}
            {activeTab === "feedback" && (
              <BuyerFeedbackSection
                key={buyer.id}
                txnId={txnId}
                buyer={buyer}
                canWrite={canWrite}
              />
            )}
            {activeTab === "comments" && (
              <CommentThread entityType="buyer" entityId={buyer.id} />
            )}
          </div>
        </div>
      )}
    </SlidePanel>
  );
}

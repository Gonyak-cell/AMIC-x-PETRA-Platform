import { ChevronRight } from "lucide-react";
import { EmptyState } from "@/components/ui";
import BuyerTierBadge from "./BuyerTierBadge";
import MarketingGridCell from "./MarketingGridCell";
import { MARKETING_STAGES, MARKETING_STAGE_LABELS } from "@/modules/ma/constants";
import type { BuyerCandidate } from "@/modules/ma/types/buyer";
import type {
  BuyerStageSummary,
  MarketingStage,
} from "@/modules/ma/types/marketing_log";

interface MarketingGridViewProps {
  buyers: BuyerCandidate[];
  overviewData: BuyerStageSummary[];
  onSelectBuyer: (buyerId: string) => void;
  canWrite: boolean;
  txnId: string;
}

export default function MarketingGridView({
  buyers,
  overviewData,
  onSelectBuyer,
  canWrite,
  txnId,
}: MarketingGridViewProps) {
  if (buyers.length === 0) {
    return (
      <EmptyState
        title="Short List가 비어 있습니다"
        description="Long List에서 매수자를 Short List로 승격해주세요."
      />
    );
  }

  const stageMap = new Map(overviewData.map((s) => [s.buyer_id, s.stages]));

  // 완료 단계 수 기준 내림차순 정렬
  const sorted = [...buyers].sort((a, b) => {
    const aStages = stageMap.get(a.id);
    const bStages = stageMap.get(b.id);
    const aCount = aStages ? MARKETING_STAGES.filter((s) => aStages[s]).length : 0;
    const bCount = bStages ? MARKETING_STAGES.filter((s) => bStages[s]).length : 0;
    return bCount - aCount;
  });

  return (
    <div className="overflow-x-auto border border-gray-border rounded-dr">
      <table className="w-full text-sm">
        <thead>
          <tr className="bg-bg-cool border-b border-gray-border">
            <th className="text-left px-3 py-2 font-medium text-text-dark whitespace-nowrap min-w-[160px]">
              매수자
            </th>
            {MARKETING_STAGES.map((s) => (
              <th
                key={s}
                className="px-2 py-2 font-medium text-text-muted text-center text-xs whitespace-nowrap border-l border-gray-border"
              >
                {MARKETING_STAGE_LABELS[s]}
              </th>
            ))}
            <th className="w-10 border-l border-gray-border" />
          </tr>
        </thead>
        <tbody>
          {sorted.map((buyer) => {
            const stages = stageMap.get(buyer.id);
            return (
              <tr
                key={buyer.id}
                className="border-b border-gray-border last:border-b-0 hover:bg-gray-50/50"
              >
                <td className="px-3 py-1.5 border-r border-gray-border">
                  <div className="flex items-center gap-1.5">
                    <span className="font-medium text-text-dark text-xs truncate max-w-[120px]">
                      {buyer.company_name}
                    </span>
                    {buyer.tier && <BuyerTierBadge tier={buyer.tier} />}
                  </div>
                </td>
                {MARKETING_STAGES.map((stage) => (
                  <MarketingGridCell
                    key={stage}
                    txnId={txnId}
                    buyerId={buyer.id}
                    stage={stage}
                    dateValue={stages?.[stage] ?? null}
                    canWrite={canWrite}
                  />
                ))}
                <td className="text-center border-l border-gray-border">
                  <button
                    type="button"
                    onClick={() => onSelectBuyer(buyer.id)}
                    className="p-1 text-text-muted hover:text-accent transition-colors"
                    aria-label={`${buyer.company_name} 상세`}
                  >
                    <ChevronRight className="h-4 w-4" />
                  </button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

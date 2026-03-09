import { useState } from "react";
import { toast } from "sonner";
import { extractApiError } from "@/api/errors";
import type { BuyerCandidate } from "@/modules/ma/types/buyer";
import { useUpdateBuyer } from "@/modules/ma/hooks/useTransactions";
import { formatKRW } from "@/modules/ma/utils/format";

interface BuyerFeedbackSectionProps {
  txnId: string;
  buyer: BuyerCandidate;
  canWrite: boolean;
}

export default function BuyerFeedbackSection({
  txnId,
  buyer,
  canWrite,
}: BuyerFeedbackSectionProps) {
  const updateBuyer = useUpdateBuyer(txnId);
  const [notes, setNotes] = useState(buyer.notes ?? "");


  const handleSave = () => {
    if (notes === (buyer.notes ?? "")) return;
    updateBuyer.mutate(
      { buyerId: buyer.id, body: { notes } },
      {
        onSuccess: () => toast.success("비고가 저장되었습니다."),
        onError: (err) => toast.error(extractApiError(err, "비고 저장에 실패했습니다.")),
      },
    );
  };


  return (
    <div className="space-y-6">
      {/* 비고 */}
      <div>
        <label htmlFor="buyer-feedback-notes" className="block text-sm font-semibold text-text-primary mb-1">
          비고
        </label>
        <textarea
          id="buyer-feedback-notes"
          className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent disabled:bg-gray-50 disabled:text-text-muted"
          rows={4}
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          onBlur={handleSave}
          disabled={!canWrite}
          placeholder="매수 후보에 대한 비고사항을 기록하세요"
        />
      </div>

      {/* 인수가액 시각 */}
      <div>
        <h4 className="text-sm font-semibold text-text-primary mb-3">
          인수가액 시각
        </h4>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <span className="block text-xs text-text-muted">IOI 금액</span>
            <span className="text-sm font-medium">
              {formatKRW(buyer.ioi_value)}
            </span>
          </div>
          <div>
            <span className="block text-xs text-text-muted">IOI 날짜</span>
            <span className="text-sm font-medium">{buyer.ioi_date ?? "-"}</span>
          </div>
          <div>
            <span className="block text-xs text-text-muted">LOI 금액</span>
            <span className="text-sm font-medium">
              {formatKRW(buyer.loi_value)}
            </span>
          </div>
          <div>
            <span className="block text-xs text-text-muted">LOI 날짜</span>
            <span className="text-sm font-medium">{buyer.loi_date ?? "-"}</span>
          </div>
          <div className="col-span-2">
            <span className="block text-xs text-text-muted">최종 제안가</span>
            <span className="text-sm font-medium">
              {formatKRW(buyer.final_offer_value)}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

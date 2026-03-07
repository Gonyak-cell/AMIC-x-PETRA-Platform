import { useState } from "react";
import { toast } from "sonner";
import type { BuyerCandidate } from "@/modules/ma/types/buyer";
import { useUpdateBuyer } from "@/modules/ma/hooks/useTransactions";

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
        onError: () => toast.error("비고 저장에 실패했습니다."),
      },
    );
  };

  const formatCurrency = (value: string | null): string => {
    if (!value) return "-";
    const num = Number(value);
    if (Number.isNaN(num)) return value;
    return `${num.toLocaleString()}원`;
  };

  return (
    <div className="space-y-6">
      {/* 비고 */}
      <div>
        <label className="block text-sm font-semibold text-text-primary mb-1">
          비고
        </label>
        <textarea
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
              {formatCurrency(buyer.ioi_value)}
            </span>
          </div>
          <div>
            <span className="block text-xs text-text-muted">IOI 날짜</span>
            <span className="text-sm font-medium">{buyer.ioi_date ?? "-"}</span>
          </div>
          <div>
            <span className="block text-xs text-text-muted">LOI 금액</span>
            <span className="text-sm font-medium">
              {formatCurrency(buyer.loi_value)}
            </span>
          </div>
          <div>
            <span className="block text-xs text-text-muted">LOI 날짜</span>
            <span className="text-sm font-medium">{buyer.loi_date ?? "-"}</span>
          </div>
          <div className="col-span-2">
            <span className="block text-xs text-text-muted">최종 제안가</span>
            <span className="text-sm font-medium">
              {formatCurrency(buyer.final_offer_value)}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

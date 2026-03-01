import { useState, useMemo, useEffect } from "react";
import { toast } from "sonner";
import { AlertTriangle, Building2, TrendingUp } from "lucide-react";
import {
  Badge,
  Button,
  Card,
  EmptyState,
  Modal,
  Spinner,
} from "@/components/ui";
import { useFIRecommendations } from "@/modules/ma/hooks/usePefRegistry";
import { useAddBuyer } from "@/modules/ma/hooks/useTransactions";
import type { FIRecommendation } from "@/modules/ma/types/pef_registry";

interface FIRecommendModalProps {
  open: boolean;
  onClose: () => void;
  txnId: string;
  existingCompanyNames: string[];
}

export default function FIRecommendModal({
  open,
  onClose,
  txnId,
  existingCompanyNames,
}: FIRecommendModalProps) {
  const {
    data: recommendations,
    isLoading,
    isError,
  } = useFIRecommendations(txnId);
  const addBuyer = useAddBuyer(txnId);
  const [selected, setSelected] = useState<Set<string>>(new Set());

  // 모달 열릴 때 선택 초기화
  useEffect(() => {
    if (open) setSelected(new Set());
  }, [open]);

  const existingSet = useMemo(
    () => new Set(existingCompanyNames.map((n) => n.toLowerCase())),
    [existingCompanyNames],
  );

  const toggleGP = (gpName: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(gpName)) next.delete(gpName);
      else next.add(gpName);
      return next;
    });
  };

  const handleAdd = async () => {
    const toAdd = Array.from(selected).filter(
      (gp) => !existingSet.has(gp.toLowerCase()),
    );
    if (toAdd.length === 0) {
      toast.info("추가할 새로운 GP가 없습니다.");
      return;
    }

    let added = 0;
    for (const gpName of toAdd) {
      try {
        await addBuyer.mutateAsync({
          company_name: gpName,
          buyer_type: "FINANCIAL_SPONSOR",
        });
        added++;
      } catch {
        toast.error(`${gpName} 추가 실패`);
      }
    }
    if (added > 0) {
      toast.success(`${added}개 FI 후보가 Long List에 추가되었습니다.`);
    }
    onClose();
  };

  const formatBillion = (v: number) => {
    if (v >= 10000) return `${(v / 10000).toFixed(1)}조`;
    return `${v.toLocaleString()}억`;
  };

  return (
    <Modal open={open} onClose={onClose} title="FI 자동 추천" size="lg">
      <p className="text-xs text-text-secondary mb-4">
        거래금액 기준으로 PEF 레지스트리에서 적합한 FI(재무적 투자자)를 자동으로
        추천합니다.
      </p>

      {isLoading && (
        <div className="flex justify-center py-8">
          <Spinner />
        </div>
      )}

      {!isLoading && isError && (
        <EmptyState
          icon={AlertTriangle}
          title="추천 조회 실패"
          description="FI 추천 데이터를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요."
        />
      )}

      {!isLoading &&
        !isError &&
        (!recommendations || recommendations.length === 0) && (
          <EmptyState
            icon={Building2}
            title="추천 결과 없음"
            description="거래금액 범위에 해당하는 PEF가 없습니다. 거래금액(estimated_deal_value)을 확인해 주세요."
          />
        )}

      {!isLoading && recommendations && recommendations.length > 0 && (
        <div className="space-y-2 max-h-[400px] overflow-y-auto">
          {recommendations.map((rec: FIRecommendation) => {
            const isExisting = existingSet.has(rec.gp_name.toLowerCase());
            const isSelected = selected.has(rec.gp_name);

            return (
              <Card
                key={rec.gp_name}
                padding="sm"
                className={
                  isSelected
                    ? "ring-2 ring-accent-primary"
                    : isExisting
                      ? "opacity-50"
                      : ""
                }
              >
                <label className="flex items-center gap-3 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={isSelected}
                    disabled={isExisting}
                    onChange={() => toggleGP(rec.gp_name)}
                    aria-label={`${rec.gp_name} 선택`}
                    className="h-4 w-4 rounded border-border"
                  />

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-sm">{rec.gp_name}</span>
                      {isExisting && <Badge variant="neutral">추가됨</Badge>}
                    </div>
                    <div className="flex items-center gap-3 mt-0.5 text-xs text-text-muted">
                      <span className="flex items-center gap-1">
                        <Building2 className="h-3 w-3" />
                        펀드 {rec.fund_count}개
                      </span>
                      <span className="flex items-center gap-1">
                        <TrendingUp className="h-3 w-3" />
                        총약정 {formatBillion(rec.total_committed_sum)}
                      </span>
                    </div>
                  </div>
                </label>
              </Card>
            );
          })}
        </div>
      )}

      <div className="flex justify-between items-center pt-4 border-t border-border mt-4">
        <span className="text-xs text-text-muted">
          {selected.size}개 선택됨
        </span>
        <div className="flex gap-2">
          <Button variant="ghost" onClick={onClose}>
            취소
          </Button>
          <Button
            onClick={handleAdd}
            disabled={selected.size === 0}
            loading={addBuyer.isPending}
          >
            Long List에 추가
          </Button>
        </div>
      </div>
    </Modal>
  );
}

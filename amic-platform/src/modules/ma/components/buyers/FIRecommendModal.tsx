import { useState, useMemo, useEffect } from "react";
import { toast } from "sonner";
import { AlertTriangle, Building2 } from "lucide-react";
import { Button, EmptyState, Modal, Spinner } from "@/components/ui";
import { useFIRecommendations } from "@/modules/ma/hooks/usePefRegistry";
import { useAddBuyer } from "@/modules/ma/hooks/useTransactions";
import type { FIRecommendation } from "@/modules/ma/types/pef_registry";
import FIRecommendCard from "./FIRecommendCard";

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
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  // 모달 열릴 때 선택/확장 초기화
  useEffect(() => {
    if (open) {
      setSelected(new Set());
      setExpanded(new Set());
    }
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

  const toggleExpand = (gpName: string) => {
    setExpanded((prev) => {
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

    const results = await Promise.allSettled(
      toAdd.map((gpName) =>
        addBuyer.mutateAsync({
          company_name: gpName,
          buyer_type: "FINANCIAL_SPONSOR",
        }),
      ),
    );

    const added = results.filter((r) => r.status === "fulfilled").length;
    const failed = toAdd.length - added;
    if (failed > 0) {
      toast.error(`${failed}개 GP 추가 실패`);
    }
    if (added > 0) {
      toast.success(`${added}개 FI 후보가 Long List에 추가되었습니다.`);
      onClose();
    }
  };

  return (
    <Modal open={open} onClose={onClose} title="FI 자동 매핑" size="lg">
      <p className="text-xs text-text-secondary mb-4">
        2021년 이후 결성 펀드 기준, 거래금액의 0.5~3배 범위 GP를 자동
        매칭합니다. (프로젝트 펀드 제외)
      </p>

      <div aria-live="polite">
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
          <div
            className="max-h-[400px] overflow-y-auto"
            tabIndex={0}
            aria-label="FI 추천 목록"
          >
            <div role="list" className="space-y-2">
              {recommendations.map((rec: FIRecommendation) => (
                <FIRecommendCard
                  key={rec.gp_name}
                  rec={rec}
                  isSelected={selected.has(rec.gp_name)}
                  isExisting={existingSet.has(rec.gp_name.toLowerCase())}
                  isExpanded={expanded.has(rec.gp_name)}
                  onToggleSelect={toggleGP}
                  onToggleExpand={toggleExpand}
                />
              ))}
            </div>
          </div>
        )}
      </div>

      <div className="flex justify-between items-center pt-4 border-t border-border mt-4">
        <span
          className="text-xs text-text-muted"
          aria-live="polite"
          aria-atomic="true"
        >
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

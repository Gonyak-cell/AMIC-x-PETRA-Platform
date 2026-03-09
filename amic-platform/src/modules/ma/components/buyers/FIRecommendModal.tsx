import { useState, useMemo, useEffect } from "react";
import { toast } from "sonner";
import { extractApiError } from "@/api/errors";
import { useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, Building2 } from "lucide-react";
import { Button, EmptyState, Modal, Spinner } from "@/components/ui";
import { maApi } from "@/api/maClient";
import { useFIRecommendations } from "@/modules/ma/hooks/usePefRegistry";
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
  const qc = useQueryClient();
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [isSubmitting, setIsSubmitting] = useState(false);
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

    setIsSubmitting(true);
    try {
      // 서버 부하 방지: 5건씩 순차 배치 실행
      const BATCH_SIZE = 5;
      const results: PromiseSettledResult<unknown>[] = [];
      for (let i = 0; i < toAdd.length; i += BATCH_SIZE) {
        const chunk = toAdd.slice(i, i + BATCH_SIZE);
        const batch = await Promise.allSettled(
          chunk.map((gpName) =>
            maApi.post(`/transactions/${txnId}/buyers`, {
              company_name: gpName,
              buyer_type: "FINANCIAL_SPONSOR",
            }),
          ),
        );
        results.push(...batch);
      }

      const succeededNames: string[] = [];
      const failedNames: string[] = [];
      let firstError = "";
      for (let i = 0; i < results.length; i++) {
        if (results[i].status === "fulfilled") {
          succeededNames.push(toAdd[i]);
        } else {
          failedNames.push(toAdd[i]);
          if (!firstError) {
            firstError = extractApiError(
              (results[i] as PromiseRejectedResult).reason,
              "알 수 없는 오류",
            );
          }
        }
      }
      if (succeededNames.length > 0) {
        qc.invalidateQueries({
          queryKey: ["ma", "transactions", txnId, "buyers"],
        });
        // 성공한 항목을 selected에서 제거하여 재시도 시 중복 방지
        setSelected((prev) => {
          const next = new Set(prev);
          for (const name of succeededNames) next.delete(name);
          return next;
        });
      }
      if (succeededNames.length > 0 && failedNames.length === 0) {
        toast.success(`${succeededNames.length}개 FI 후보가 Long List에 추가되었습니다.`);
        onClose();
      } else if (succeededNames.length > 0 && failedNames.length > 0) {
        toast.warning(
          `${succeededNames.length}개 추가 완료, ${failedNames.length}개 실패 (${failedNames.join(", ")}): ${firstError}`,
        );
      } else if (failedNames.length > 0) {
        toast.error(
          `${failedNames.length}개 GP 추가 실패: ${failedNames.join(", ")} — ${firstError}`,
        );
      }
    } finally {
      setIsSubmitting(false);
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
              description="거래금액 범위에 해당하는 GP/PEF가 없습니다. 거래 설정에서 예상 거래 금액(억원)을 확인해 주세요."
            />
          )}

        {!isLoading && recommendations && recommendations.length > 0 && (
          <>
            <p className="text-xs text-text-muted mb-2">
              {recommendations.length}개 GP 매칭 · 2021년 이후 유효 PEF를 GP별로
              그룹핑하여 거래금액 범위 내 상위 최대 50개를 표시합니다. 결과를
              좁히려면 거래 설정에서 산업 키워드를 지정하세요 (Tier 1 우선
              매칭).
            </p>
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
          </>
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
            disabled={selected.size === 0 || isSubmitting}
            loading={isSubmitting}
          >
            Long List에 추가
          </Button>
        </div>
      </div>
    </Modal>
  );
}

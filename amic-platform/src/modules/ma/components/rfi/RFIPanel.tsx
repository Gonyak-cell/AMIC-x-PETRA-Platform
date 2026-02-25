import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { KpiCard } from "@/components/ui/KpiCard";
import { Spinner } from "@/components/ui/Spinner";
import { Plus, Sparkles, FileText } from "lucide-react";
import {
  useRFIs,
  useRFISummary,
  useGenerateRFIFromDD,
  useRespondRFIItem,
  useReviewRFIItem,
} from "@/modules/ma/hooks/useRFI";
import RFICreateModal from "./RFICreateModal";
import RFIDetailView from "./RFIDetailView";
import type { RFIStatus } from "@/modules/ma/types/rfi";
import { RFI_STATUS_LABELS } from "@/modules/ma/constants";

const STATUS_VARIANT: Record<RFIStatus, "success" | "warning" | "error" | "info" | "neutral"> = {
  DRAFT: "neutral",
  SENT: "info",
  PARTIALLY_RESPONDED: "warning",
  FULLY_RESPONDED: "success",
  CLOSED: "neutral",
  CANCELLED: "error",
};

interface RFIPanelProps {
  txnId: string;
}

export default function RFIPanel({ txnId }: RFIPanelProps) {
  const { data: rfis, isLoading: rfisLoading, isError: rfisError } = useRFIs(txnId);
  const { data: summary, isLoading: summaryLoading } = useRFISummary(txnId);
  const generateFromDD = useGenerateRFIFromDD(txnId);

  const [showCreate, setShowCreate] = useState(false);
  const [selectedRFIId, setSelectedRFIId] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<RFIStatus | "ALL">("ALL");

  // 선택된 RFI의 응답/검토 mutation (rfiId 필요)
  const respondItem = useRespondRFIItem(txnId, selectedRFIId ?? "");
  const reviewItem = useReviewRFIItem(txnId, selectedRFIId ?? "");

  if (selectedRFIId) {
    return (
      <RFIDetailView
        txnId={txnId}
        rfiId={selectedRFIId}
        onBack={() => setSelectedRFIId(null)}
        onRespond={(itemId, response) =>
          respondItem.mutate({ itemId, body: { response } })
        }
        onReview={(itemId, status, comment) =>
          reviewItem.mutate({
            itemId,
            body: { status, reviewer_comment: comment },
          })
        }
      />
    );
  }

  const filteredRFIs = rfis?.filter(
    (r) => statusFilter === "ALL" || r.status === statusFilter,
  );

  const isLoading = rfisLoading || summaryLoading;

  return (
    <div className="space-y-4">
      {/* 요약 */}
      {summary && summary.total_items > 0 && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <KpiCard label="총 RFI" value={String(summary.total_rfis)} />
          <KpiCard
            label="응답률"
            value={`${Math.round(summary.overall_response_pct)}%`}
            variant={summary.overall_response_pct >= 80 ? "positive" : summary.overall_response_pct >= 50 ? "default" : "negative"}
          />
          <KpiCard
            label="확인 완료"
            value={String(summary.accepted_items)}
            variant={summary.accepted_items > 0 ? "positive" : "default"}
          />
          <KpiCard
            label="기한 초과"
            value={String(summary.overdue_items)}
            variant={summary.overdue_items > 0 ? "negative" : "positive"}
          />
        </div>
      )}

      {/* 카테고리별 요약 바 */}
      {summary && summary.by_category.length > 0 && (
        <Card padding="md">
          <div className="space-y-2">
            {summary.by_category.map((cat) => {
              const pct = cat.total > 0 ? Math.round((cat.responded / cat.total) * 100) : 0;
              return (
                <div key={cat.category} className="flex items-center gap-3">
                  <span className="text-xs font-medium w-20 truncate">{cat.category}</span>
                  <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-accent rounded-full transition-all"
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                  <span className="text-xs text-gray-500 w-16 text-right">
                    {cat.responded}/{cat.total}
                  </span>
                </div>
              );
            })}
          </div>
        </Card>
      )}

      {/* 헤더 + 액션 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2" role="radiogroup" aria-label="RFI 상태 필터">
          <span className="text-xs font-medium text-gray-500">상태:</span>
          {([
            { value: "ALL", label: "전체" },
            { value: "DRAFT", label: "초안" },
            { value: "SENT", label: "발송됨" },
            { value: "PARTIALLY_RESPONDED", label: "일부 응답" },
            { value: "FULLY_RESPONDED", label: "전체 응답" },
            { value: "CLOSED", label: "마감" },
          ] as const).map((opt) => (
            <button
              key={opt.value}
              type="button"
              role="radio"
              aria-checked={statusFilter === opt.value}
              className={`px-3 py-1 text-xs font-medium rounded-full transition-colors ${
                statusFilter === opt.value
                  ? "bg-gray-900 text-white"
                  : "bg-gray-100 text-gray-600 hover:bg-gray-200"
              }`}
              onClick={() => setStatusFilter(opt.value as RFIStatus | "ALL")}
            >
              {opt.label}
            </button>
          ))}
        </div>

        <div className="flex gap-2">
          <Button
            size="sm"
            variant="secondary"
            icon={Sparkles}
            onClick={() => generateFromDD.mutate(undefined)}
            loading={generateFromDD.isPending}
          >
            DD에서 생성
          </Button>
          <Button size="sm" icon={Plus} onClick={() => setShowCreate(true)}>
            RFI 생성
          </Button>
        </div>
      </div>

      {/* RFI 목록 */}
      {isLoading ? (
        <Spinner />
      ) : rfisError ? (
        <Card padding="lg">
          <div className="text-center py-8 text-red-500">
            <p className="font-medium">RFI 목록을 불러오는 중 오류가 발생했습니다.</p>
            <p className="text-xs mt-1 text-gray-500">잠시 후 다시 시도해 주세요.</p>
          </div>
        </Card>
      ) : !filteredRFIs?.length ? (
        <Card padding="lg">
          <div className="text-center py-8 text-gray-500">
            <FileText className="w-10 h-10 mx-auto mb-2 text-gray-300" />
            <p className="font-medium">RFI가 없습니다</p>
            <p className="text-xs mt-1">새 RFI를 생성하거나 DD 체크리스트에서 자동으로 생성하세요.</p>
          </div>
        </Card>
      ) : (
        <div className="space-y-2">
          {filteredRFIs.map((rfi) => {
            const pct = rfi.total_items > 0 ? Math.round((rfi.responded_items / rfi.total_items) * 100) : 0;
            return (
              <Card
                key={rfi.id}
                padding="md"
                hoverEffect
                onClick={() => setSelectedRFIId(rfi.id)}
                className="cursor-pointer"
              >
                <div className="flex items-center justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-medium text-sm text-gray-900 truncate">
                        {rfi.title}
                      </span>
                      <Badge variant={STATUS_VARIANT[rfi.status]} pill>
                        {RFI_STATUS_LABELS[rfi.status]}
                      </Badge>
                      <span className="text-xs text-gray-400">Round {rfi.round_number}</span>
                    </div>
                    <div className="flex items-center gap-4 text-xs text-gray-500">
                      {rfi.recipient_company && <span>{rfi.recipient_company}</span>}
                      {rfi.due_date && <span>마감: {rfi.due_date}</span>}
                      <span>
                        응답 {rfi.responded_items}/{rfi.total_items} ({pct}%)
                      </span>
                      <span>확인 {rfi.accepted_items}</span>
                    </div>
                  </div>

                  {/* 진행률 미니 바 */}
                  <div className="w-24 flex-shrink-0 ml-4">
                    <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-accent rounded-full transition-all"
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
      )}

      <RFICreateModal txnId={txnId} open={showCreate} onClose={() => setShowCreate(false)} />
    </div>
  );
}

import { useState, useMemo } from "react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { KpiCard } from "@/components/ui/KpiCard";
import { Spinner } from "@/components/ui/Spinner";
import {
  Send,
  X,
  Download,
  RefreshCw,
  CalendarClock,
  ArrowLeft,
} from "lucide-react";
import {
  useRFI,
  useSendRFI,
  useCloseRFI,
  useExportRFI,
  useSyncRFIToChecklists,
  useExtendRFIDeadline,
} from "@/modules/ma/hooks/useRFI";
import RFIItemRow from "./RFIItemRow";
import type {
  RFICategory,
  RFIItemStatus,
  RFIItemPriority,
} from "@/modules/ma/types/rfi";
import {
  RFI_STATUS_LABELS,
  RFI_CATEGORY_LABELS,
  RFI_STATUS_VARIANT,
} from "@/modules/ma/constants";

interface RFIDetailViewProps {
  txnId: string;
  rfiId: string;
  onBack: () => void;
  onRespond?: (itemId: string, response: string) => void;
  onReview?: (
    itemId: string,
    status: "ACCEPTED" | "CLARIFICATION_NEEDED",
    comment?: string,
  ) => void;
}

export default function RFIDetailView({
  txnId,
  rfiId,
  onBack,
  onRespond,
  onReview,
}: RFIDetailViewProps) {
  const { data: rfi, isLoading, isError } = useRFI(txnId, rfiId);
  const sendRFI = useSendRFI(txnId);
  const closeRFI = useCloseRFI(txnId);
  const exportRFI = useExportRFI(txnId);
  const syncRFI = useSyncRFIToChecklists(txnId);
  const extendDeadline = useExtendRFIDeadline(txnId);

  const [categoryFilter, setCategoryFilter] = useState<RFICategory | "ALL">(
    "ALL",
  );
  const [statusFilter, setStatusFilter] = useState<RFIItemStatus | "ALL">(
    "ALL",
  );
  const [priorityFilter, setPriorityFilter] = useState<RFIItemPriority | "ALL">(
    "ALL",
  );
  const [extendDate, setExtendDate] = useState("");
  const [showExtend, setShowExtend] = useState(false);

  const filteredItems = useMemo(() => {
    if (!rfi?.items) return [];
    return rfi.items.filter((item) => {
      if (categoryFilter !== "ALL" && item.category !== categoryFilter)
        return false;
      if (statusFilter !== "ALL" && item.status !== statusFilter) return false;
      if (priorityFilter !== "ALL" && item.priority !== priorityFilter)
        return false;
      return true;
    });
  }, [rfi?.items, categoryFilter, statusFilter, priorityFilter]);

  const categories = useMemo(() => {
    if (!rfi?.items) return [];
    const cats = new Set(rfi.items.map((i) => i.category));
    return Array.from(cats).sort();
  }, [rfi?.items]);

  // 카테고리별 그룹
  const groupedItems = useMemo(() => {
    if (categoryFilter !== "ALL")
      return [{ category: categoryFilter, items: filteredItems }];
    const groups: Record<string, typeof filteredItems> = {};
    for (const item of filteredItems) {
      if (!groups[item.category]) groups[item.category] = [];
      groups[item.category].push(item);
    }
    return Object.entries(groups).map(([category, items]) => ({
      category: category as RFICategory,
      items,
    }));
  }, [filteredItems, categoryFilter]);

  if (isLoading) return <Spinner size="lg" />;
  if (isError) {
    return (
      <div className="text-center py-12">
        <p className="text-red-500 font-medium">
          RFI를 불러오는 중 오류가 발생했습니다.
        </p>
        <p className="text-xs text-gray-500 mt-1">
          잠시 후 다시 시도해 주세요.
        </p>
        <Button
          variant="ghost"
          icon={ArrowLeft}
          onClick={onBack}
          size="sm"
          className="mt-4"
        >
          목록으로
        </Button>
      </div>
    );
  }
  if (!rfi)
    return (
      <div className="text-center py-12 text-gray-500">
        RFI를 찾을 수 없습니다
      </div>
    );

  const responsePct =
    rfi.total_items > 0
      ? Math.round((rfi.responded_items / rfi.total_items) * 100)
      : 0;
  const acceptedPct =
    rfi.total_items > 0
      ? Math.round((rfi.accepted_items / rfi.total_items) * 100)
      : 0;

  return (
    <div className="space-y-4">
      {/* 헤더 */}
      <div className="flex items-center gap-3">
        <Button variant="ghost" icon={ArrowLeft} onClick={onBack} size="sm">
          목록
        </Button>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <h3 className="text-lg font-bold text-gray-900 truncate">
              {rfi.title}
            </h3>
            <Badge variant={RFI_STATUS_VARIANT[rfi.status]} pill>
              {RFI_STATUS_LABELS[rfi.status]}
            </Badge>
          </div>
          <div className="flex items-center gap-4 text-xs text-gray-500 mt-0.5">
            <span>Round {rfi.round_number}</span>
            {rfi.recipient_company && <span>{rfi.recipient_company}</span>}
            {rfi.recipient_name && <span>{rfi.recipient_name}</span>}
            {rfi.due_date && <span>마감: {rfi.due_date}</span>}
          </div>
        </div>

        {/* 액션 버튼 */}
        <div className="flex gap-2">
          {rfi.status === "DRAFT" && (
            <Button
              size="sm"
              icon={Send}
              onClick={() => sendRFI.mutate(rfiId)}
              loading={sendRFI.isPending}
            >
              발송
            </Button>
          )}
          {rfi.status !== "CLOSED" &&
            rfi.status !== "CANCELLED" &&
            rfi.status !== "DRAFT" && (
              <>
                <Button
                  size="sm"
                  variant="secondary"
                  icon={CalendarClock}
                  onClick={() => setShowExtend(!showExtend)}
                >
                  연장
                </Button>
                <Button
                  size="sm"
                  variant="secondary"
                  icon={X}
                  onClick={() => closeRFI.mutate(rfiId)}
                  loading={closeRFI.isPending}
                >
                  마감
                </Button>
              </>
            )}
          <Button
            size="sm"
            variant="secondary"
            icon={RefreshCw}
            onClick={() => syncRFI.mutate(rfiId)}
            loading={syncRFI.isPending}
          >
            동기화
          </Button>
          <Button
            size="sm"
            variant="secondary"
            icon={Download}
            onClick={() => exportRFI.mutate(rfiId)}
            loading={exportRFI.isPending}
          >
            Excel
          </Button>
        </div>
      </div>

      {/* 마감일 연장 인라인 */}
      {showExtend && (
        <Card padding="sm">
          <div className="flex items-center gap-3">
            <input
              type="date"
              className="border rounded px-3 py-1.5 text-sm"
              value={extendDate}
              onChange={(e) => setExtendDate(e.target.value)}
            />
            <Button
              size="sm"
              disabled={!extendDate}
              onClick={() => {
                extendDeadline.mutate({ rfiId, dueDate: extendDate });
                setShowExtend(false);
                setExtendDate("");
              }}
              loading={extendDeadline.isPending}
            >
              적용
            </Button>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => setShowExtend(false)}
            >
              취소
            </Button>
          </div>
        </Card>
      )}

      {/* KPI */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <KpiCard label="전체 질문" value={String(rfi.total_items)} />
        <KpiCard
          label="응답률"
          value={`${responsePct}%`}
          variant={
            responsePct >= 80
              ? "positive"
              : responsePct >= 50
                ? "default"
                : "negative"
          }
        />
        <KpiCard
          label="확인 완료"
          value={String(rfi.accepted_items)}
          variant={acceptedPct >= 80 ? "positive" : "default"}
        />
        <KpiCard
          label="대기 중"
          value={String(rfi.total_items - rfi.responded_items)}
          variant={
            rfi.total_items - rfi.responded_items > 0 ? "negative" : "positive"
          }
        />
      </div>

      {rfi.description && (
        <Card padding="sm">
          <p className="text-sm text-gray-600">{rfi.description}</p>
        </Card>
      )}

      {/* 필터 */}
      <div className="flex flex-wrap items-center gap-2">
        <div
          className="flex items-center gap-2"
          role="radiogroup"
          aria-label="RFI 카테고리 필터"
        >
          <span className="text-xs font-medium text-gray-500">분류:</span>
          {[
            { value: "ALL", label: "전체" },
            ...categories.map((c) => ({
              value: c,
              label: RFI_CATEGORY_LABELS[c] || c,
            })),
          ].map((opt) => (
            <button
              key={opt.value}
              type="button"
              role="radio"
              aria-checked={categoryFilter === opt.value}
              className={`px-3 py-1 text-xs font-medium rounded-full transition-colors ${
                categoryFilter === opt.value
                  ? "bg-gray-900 text-white"
                  : "bg-gray-100 text-gray-600 hover:bg-gray-200"
              }`}
              onClick={() =>
                setCategoryFilter(opt.value as RFICategory | "ALL")
              }
            >
              {opt.label}
            </button>
          ))}
        </div>

        <div
          className="flex items-center gap-2 ml-4"
          role="radiogroup"
          aria-label="RFI 항목 상태 필터"
        >
          <span className="text-xs font-medium text-gray-500">상태:</span>
          {(
            [
              { value: "ALL", label: "전체" },
              { value: "PENDING", label: "대기" },
              { value: "RESPONDED", label: "응답됨" },
              { value: "CLARIFICATION_NEEDED", label: "추가확인" },
              { value: "ACCEPTED", label: "확인완료" },
            ] as const
          ).map((opt) => (
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
              onClick={() =>
                setStatusFilter(opt.value as RFIItemStatus | "ALL")
              }
            >
              {opt.label}
            </button>
          ))}
        </div>

        <div
          className="flex items-center gap-2 ml-4"
          role="radiogroup"
          aria-label="RFI 우선순위 필터"
        >
          <span className="text-xs font-medium text-gray-500">우선순위:</span>
          {(
            [
              { value: "ALL", label: "전체" },
              { value: "CRITICAL", label: "긴급" },
              { value: "HIGH", label: "높음" },
              { value: "MEDIUM", label: "보통" },
              { value: "LOW", label: "낮음" },
            ] as const
          ).map((opt) => (
            <button
              key={opt.value}
              type="button"
              role="radio"
              aria-checked={priorityFilter === opt.value}
              className={`px-3 py-1 text-xs font-medium rounded-full transition-colors ${
                priorityFilter === opt.value
                  ? "bg-gray-900 text-white"
                  : "bg-gray-100 text-gray-600 hover:bg-gray-200"
              }`}
              onClick={() =>
                setPriorityFilter(opt.value as RFIItemPriority | "ALL")
              }
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {/* 아이템 목록 */}
      {groupedItems.length === 0 ? (
        <Card padding="lg">
          <div className="text-center py-8 text-gray-500">
            {rfi.items.length === 0
              ? "아직 질문이 없습니다. 질문을 추가하거나 DD 체크리스트에서 자동 생성하세요."
              : "필터 조건에 맞는 질문이 없습니다."}
          </div>
        </Card>
      ) : (
        groupedItems.map((group) => (
          <div key={group.category}>
            <h4 className="text-sm font-semibold text-gray-700 mb-2 flex items-center gap-2">
              <span className="px-2 py-0.5 bg-slate-100 rounded text-xs">
                {RFI_CATEGORY_LABELS[group.category] || group.category}
              </span>
              <span className="text-xs text-gray-400">
                {group.items.length}개
              </span>
            </h4>
            <div className="space-y-1">
              {group.items.map((item) => (
                <RFIItemRow
                  key={item.id}
                  item={item}
                  onRespond={onRespond}
                  onReview={onReview}
                />
              ))}
            </div>
          </div>
        ))
      )}
    </div>
  );
}

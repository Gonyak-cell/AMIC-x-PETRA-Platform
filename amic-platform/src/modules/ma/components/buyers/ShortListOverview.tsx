import { useState } from "react";
import { toast } from "sonner";
import {
  Mail,
  Phone,
  User,
  ChevronDown,
  ChevronRight,
  Plus,
} from "lucide-react";
import {
  Badge,
  Button,
  Card,
  DataTable,
  EmptyState,
  Input,
  Modal,
  Select,
} from "@/components/ui";
import type { Column } from "@/components/ui";
import type { BuyerCandidate } from "@/modules/ma/types/buyer";
import type {
  MarketingLog,
  MarketingLogCreate,
  BuyerStageSummary,
} from "@/modules/ma/types/marketing_log";
import {
  MARKETING_STAGE_OPTIONS,
  MARKETING_STAGE_LABELS,
  BUYER_TIER_LABELS,
} from "@/modules/ma/constants";
import BuyerTierBadge from "./BuyerTierBadge";
import DealRoleBadge from "./DealRoleBadge";
import MarketingStageTracker from "./MarketingStageTracker";
import {
  useMarketingLogs,
  useCreateMarketingLog,
  useDeleteMarketingLog,
} from "@/modules/ma/hooks/useMarketingLogs";
import { useDartFinancialSummary } from "@/modules/ma/hooks/useDartIntegration";
import { useUpdateBuyer } from "@/modules/ma/hooks/useTransactions";

interface ShortListOverviewProps {
  txnId: string;
  buyers: BuyerCandidate[];
  overviewData: BuyerStageSummary[];
  canWrite: boolean;
}

/** 펼쳤을 때만 마운트 — 로그/DART API 호출을 지연시켜 N+1 방지 */
function ExpandedContent({
  buyer,
  txnId,
  canWrite,
  stageSummary,
}: {
  buyer: BuyerCandidate;
  txnId: string;
  canWrite: boolean;
  stageSummary: BuyerStageSummary | undefined;
}) {
  const { data: logs } = useMarketingLogs(txnId, buyer.id);
  const { data: dartSummary } = useDartFinancialSummary(
    txnId,
    buyer.id,
    !!buyer.corp_code,
  );
  const createLog = useCreateMarketingLog(txnId, buyer.id);
  const deleteLog = useDeleteMarketingLog(txnId, buyer.id);
  const updateBuyer = useUpdateBuyer(txnId);

  const [showLogModal, setShowLogModal] = useState(false);
  const [logForm, setLogForm] = useState<MarketingLogCreate>({
    stage: "IDENTIFIED",
    log_date: new Date().toISOString().slice(0, 10),
    content: "",
  });

  const logColumns: Column<MarketingLog>[] = [
    {
      key: "log_date",
      header: "일자",
      render: (r) => <span className="text-xs font-mono">{r.log_date}</span>,
    },
    {
      key: "stage",
      header: "단계",
      render: (r) => (
        <Badge variant="info">
          {MARKETING_STAGE_LABELS[r.stage] ?? r.stage}
        </Badge>
      ),
    },
    {
      key: "content",
      header: "내용",
      render: (r) => (
        <span className="text-xs text-text-secondary line-clamp-2">
          {r.content || "-"}
        </span>
      ),
    },
  ];

  if (canWrite) {
    logColumns.push({
      key: "actions" as keyof MarketingLog,
      header: "",
      render: (r) => (
        <button
          className="text-xs text-negative hover:underline"
          onClick={(e) => {
            e.stopPropagation();
            deleteLog.mutate(r.id);
          }}
        >
          삭제
        </button>
      ),
    });
  }

  return (
    <div className="px-4 pb-4 pt-1 space-y-3">
      {/* Stage Tracker (full) */}
      {stageSummary && (
        <div className="p-3 bg-bg-cool/30 rounded-dr">
          <MarketingStageTracker summary={stageSummary} />
        </div>
      )}

      {/* DART Financial Summary */}
      {buyer.corp_code && dartSummary && (
        <div className="grid grid-cols-4 gap-3">
          <DartMetric label="매출" value={dartSummary.revenue} />
          <DartMetric label="영업이익" value={dartSummary.operating_profit} />
          <DartMetric label="순이익" value={dartSummary.net_income} />
          <DartMetric
            label="부채비율"
            value={dartSummary.debt_ratio}
            suffix="%"
          />
        </div>
      )}

      {/* Log Table */}
      <div className="flex items-center justify-between">
        <h4 className="text-xs font-medium text-text-secondary">활동 로그</h4>
        {canWrite && (
          <Button
            icon={Plus}
            size="sm"
            variant="ghost"
            onClick={() => setShowLogModal(true)}
          >
            로그 추가
          </Button>
        )}
      </div>

      {logs && logs.length > 0 ? (
        <DataTable columns={logColumns} data={logs} keyField="id" compact />
      ) : (
        <p className="text-xs text-text-muted py-2">
          아직 활동 로그가 없습니다.
        </p>
      )}

      {/* Log Create Modal */}
      {showLogModal && (
        <Modal
          open
          onClose={() => setShowLogModal(false)}
          title="마케팅 로그 추가"
        >
          <form
            className="space-y-4"
            onSubmit={(e) => {
              e.preventDefault();
              createLog.mutate(logForm, {
                onSuccess: () => {
                  setShowLogModal(false);
                  if (
                    logForm.stage === "NDA_SIGNED" &&
                    buyer.status !== "NDA_SIGNED"
                  ) {
                    toast.info("파이프라인 상태를 NDA 체결로 업데이트할까요?", {
                      action: {
                        label: "업데이트",
                        onClick: () =>
                          updateBuyer.mutate({
                            buyerId: buyer.id,
                            body: { status: "NDA_SIGNED" },
                          }),
                      },
                      duration: 8000,
                    });
                  }
                },
              });
            }}
          >
            <Select
              label="단계"
              options={MARKETING_STAGE_OPTIONS}
              value={logForm.stage}
              onChange={(e) =>
                setLogForm((p) => ({
                  ...p,
                  stage: e.target.value as MarketingLogCreate["stage"],
                }))
              }
            />
            <Input
              label="일자"
              type="date"
              value={logForm.log_date}
              onChange={(e) =>
                setLogForm((p) => ({ ...p, log_date: e.target.value }))
              }
              required
            />
            <Input
              label="내용"
              value={logForm.content ?? ""}
              onChange={(e) =>
                setLogForm((p) => ({ ...p, content: e.target.value }))
              }
              placeholder="활동 내용 메모"
            />
            <div className="flex justify-end gap-2 pt-2">
              <Button
                variant="ghost"
                type="button"
                onClick={() => setShowLogModal(false)}
              >
                취소
              </Button>
              <Button type="submit" loading={createLog.isPending}>
                추가
              </Button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  );
}

function BuyerRow({
  buyer,
  txnId,
  canWrite,
  stageSummary,
}: {
  buyer: BuyerCandidate;
  txnId: string;
  canWrite: boolean;
  stageSummary: BuyerStageSummary | undefined;
}) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="border-b border-border last:border-0">
      {/* Header Row */}
      <button
        className="flex w-full items-center gap-3 px-4 py-3 text-left hover:bg-bg-cool/50 transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        {expanded ? (
          <ChevronDown className="h-4 w-4 text-text-muted flex-shrink-0" />
        ) : (
          <ChevronRight className="h-4 w-4 text-text-muted flex-shrink-0" />
        )}

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-medium text-sm">{buyer.company_name}</span>
            <BuyerTierBadge tier={buyer.tier} />
            <DealRoleBadge role={buyer.deal_role} />
          </div>
          <div className="flex items-center gap-3 mt-0.5 text-xs text-text-muted">
            {buyer.contact_name && (
              <span className="flex items-center gap-1">
                <User className="h-3 w-3" />
                {buyer.contact_name}
              </span>
            )}
            {buyer.contact_email && (
              <span className="flex items-center gap-1">
                <Mail className="h-3 w-3" />
                {buyer.contact_email}
              </span>
            )}
            {buyer.contact_phone && (
              <span className="flex items-center gap-1">
                <Phone className="h-3 w-3" />
                {buyer.contact_phone}
              </span>
            )}
          </div>
        </div>

        <div className="flex-shrink-0">
          {stageSummary && (
            <MarketingStageTracker summary={stageSummary} compact />
          )}
        </div>
      </button>

      {/* Expanded — 펼칠 때만 마운트하여 로그/DART API 호출 지연 */}
      {expanded && (
        <ExpandedContent
          buyer={buyer}
          txnId={txnId}
          canWrite={canWrite}
          stageSummary={stageSummary}
        />
      )}
    </div>
  );
}

function DartMetric({
  label,
  value,
  suffix,
}: {
  label: string;
  value: number | null;
  suffix?: string;
}) {
  const display =
    value != null
      ? `${value >= 1_0000_0000 ? `${(value / 1_0000_0000).toFixed(1)}억` : value.toLocaleString()}${suffix ?? ""}`
      : "-";

  return (
    <div className="rounded-dr border border-border px-3 py-2">
      <div className="text-[10px] text-text-muted">{label}</div>
      <div className="text-sm font-semibold font-mono">{display}</div>
    </div>
  );
}

export default function ShortListOverview({
  txnId,
  buyers,
  overviewData,
  canWrite,
}: ShortListOverviewProps) {
  const tierOrder = ["TIER_1", "TIER_2", "TIER_3"];
  const shortListBuyers = buyers.filter(
    (b) => b.tier && tierOrder.includes(b.tier),
  );

  if (!shortListBuyers.length) {
    return (
      <EmptyState
        icon={User}
        title="Short List 후보 없음"
        description="Long List에서 Tier를 지정하면 여기에 표시됩니다."
      />
    );
  }

  // overviewData에서 buyer_id → BuyerStageSummary 매핑 (개별 API 호출 방지)
  const summaryMap = new Map(overviewData.map((s) => [s.buyer_id, s]));

  const grouped = tierOrder
    .map((tier) => ({
      tier,
      label: BUYER_TIER_LABELS[tier] ?? tier,
      buyers: shortListBuyers.filter((b) => b.tier === tier),
    }))
    .filter((g) => g.buyers.length > 0);

  return (
    <div className="space-y-4">
      {grouped.map((group) => (
        <Card
          key={group.tier}
          title={`${group.label} (${group.buyers.length})`}
          headerBar
          padding="none"
        >
          {group.buyers.map((buyer) => (
            <BuyerRow
              key={buyer.id}
              buyer={buyer}
              txnId={txnId}
              canWrite={canWrite}
              stageSummary={summaryMap.get(buyer.id)}
            />
          ))}
        </Card>
      ))}
    </div>
  );
}

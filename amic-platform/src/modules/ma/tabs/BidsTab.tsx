import { useState } from "react";
import { Plus, Trash2, DollarSign } from "lucide-react";
import {
  useBids,
  useBidComparison,
  useCreateBid,
  useUpdateBid,
  useDeleteBid,
} from "@/modules/ma/hooks/useBids";
import { useBuyers } from "@/modules/ma/hooks/useTransactions";
import type {
  BidCreate,
  BidType,
  BidStatus as BidStatusType,
  ValuationMethod,
} from "@/modules/ma/types/bid";
import {
  BID_TYPE_OPTIONS,
  BID_STATUS_OPTIONS,
  VALUATION_METHOD_OPTIONS,
  BUYER_TYPE_OPTIONS,
} from "@/modules/ma/constants";
import FileUploadZone from "@/modules/ma/components/FileUploadZone";

import {
  Badge,
  Button,
  Card,
  DataTable,
  EmptyState,
  INLINE_INPUT_CLS,
  Input,
  Modal,
  Select,
} from "@/components/ui";

import { formatKRW as formatAmount } from "@/modules/ma/utils/format";

interface BidsTabProps {
  txnId: string;
  canWrite: boolean;
}

export default function BidsTab({ txnId, canWrite }: BidsTabProps) {
  const { data: bids } = useBids(txnId);
  const { data: bidComparison } = useBidComparison(txnId);
  const { data: buyers } = useBuyers(txnId);
  const createBid = useCreateBid(txnId);
  const updateBid = useUpdateBid(txnId);
  const deleteBid = useDeleteBid(txnId);

  const [showBidModal, setShowBidModal] = useState(false);
  const [bidForm, setBidForm] = useState<BidCreate>({
    buyer_candidate_id: "",
    bid_type: "IOI" as BidType,
  });

  return (
    <div className="space-y-4">
      {/* 비교 매트릭스 */}
      {bidComparison && bidComparison.length > 0 && (
        <Card title="입찰 비교 매트릭스" headerBar padding="none">
          <DataTable
            columns={[
              { key: "buyer_name", header: "매수자", minWidth: "140px" },
              {
                key: "buyer_type",
                header: "유형",
                minWidth: "100px",
                render: (r) => (
                  <Badge variant="neutral">
                    {BUYER_TYPE_OPTIONS.find((o) => o.value === r.buyer_type)
                      ?.label ?? r.buyer_type}
                  </Badge>
                ),
              },
              {
                key: "ioi",
                header: "IOI",
                minWidth: "80px",
                align: "right",
                mono: true,
                render: (r) => (r.ioi ? formatAmount(r.ioi.amount) : "-"),
              },
              {
                key: "loi",
                header: "LOI",
                minWidth: "80px",
                align: "right",
                mono: true,
                render: (r) => (r.loi ? formatAmount(r.loi.amount) : "-"),
              },
              {
                key: "final_offer",
                header: "최종 제안",
                minWidth: "80px",
                align: "right",
                mono: true,
                render: (r) =>
                  r.final_offer ? formatAmount(r.final_offer.amount) : "-",
              },
            ]}
            data={bidComparison}
            keyField="buyer_id"
          />
        </Card>
      )}

      {/* 전체 입찰 목록 */}
      <Card
        title="입찰 이력"
        headerBar
        padding="none"
        actions={
          canWrite ? (
            <Button
              icon={Plus}
              onClick={() => setShowBidModal(true)}
              variant="ghost"
            >
              입찰 추가
            </Button>
          ) : undefined
        }
      >
        {!bids?.length ? (
          <EmptyState
            icon={DollarSign}
            title="입찰 없음"
            description="IOI/LOI/최종 제안을 등록하세요."
            actionLabel={canWrite ? "입찰 추가" : undefined}
            onAction={canWrite ? () => setShowBidModal(true) : undefined}
          />
        ) : (
          <DataTable
            columns={[
              {
                key: "buyer_candidate_id",
                header: "매수자",
                render: (r) => {
                  const buyer = buyers?.find(
                    (b) => b.id === r.buyer_candidate_id,
                  );
                  return (
                    buyer?.company_name ?? r.buyer_candidate_id.slice(0, 8)
                  );
                },
              },
              {
                key: "bid_type",
                header: "유형",
                render: (r) => (
                  <Badge variant="info">
                    {BID_TYPE_OPTIONS.find((o) => o.value === r.bid_type)
                      ?.label ?? r.bid_type}
                  </Badge>
                ),
              },
              {
                key: "amount",
                header: "금액",
                align: "right",
                render: (r) => (
                  <input
                    key={`${r.id}-amount-${r.amount}`}
                    type="number"
                    className={`${INLINE_INPUT_CLS} w-28 text-right font-mono`}
                    defaultValue={r.amount ?? ""}
                    placeholder="금액"
                    onBlur={(e) => {
                      const v = e.target.value
                        ? Number(e.target.value)
                        : undefined;
                      if (v !== (r.amount ?? undefined)) {
                        updateBid.mutate({
                          bidId: r.id,
                          body: { amount: v },
                        });
                      }
                    }}
                    disabled={!canWrite}
                  />
                ),
              },
              {
                key: "valuation_method",
                header: "밸류에이션",
                render: (r) =>
                  r.valuation_method
                    ? (VALUATION_METHOD_OPTIONS.find(
                        (o) => o.value === r.valuation_method,
                      )?.label ?? r.valuation_method)
                    : "-",
              },
              {
                key: "multiple",
                header: "배수",
                align: "right",
                mono: true,
                render: (r) => (r.multiple != null ? `${r.multiple}x` : "-"),
              },
              {
                key: "status",
                header: "상태",
                render: (r) => (
                  <Select
                    options={BID_STATUS_OPTIONS}
                    value={r.status}
                    onChange={(e) =>
                      updateBid.mutate({
                        bidId: r.id,
                        body: { status: e.target.value as BidStatusType },
                      })
                    }
                    className="!py-0.5 !px-1.5 !text-xs"
                    disabled={!canWrite}
                  />
                ),
              },
              {
                key: "submitted_at",
                header: "제출일",
                render: (r) => (
                  <input
                    key={`${r.id}-submitted-${r.submitted_at}`}
                    type="date"
                    className={`${INLINE_INPUT_CLS} w-32`}
                    defaultValue={r.submitted_at ?? ""}
                    onChange={(e) =>
                      updateBid.mutate({
                        bidId: r.id,
                        body: { submitted_at: e.target.value || undefined },
                      })
                    }
                    disabled={!canWrite}
                  />
                ),
              },
              {
                key: "actions",
                header: "",
                width: "40px",
                render: (r) =>
                  canWrite ? (
                    <button
                      className="text-text-muted hover:text-negative p-1 rounded transition-colors"
                      title="삭제"
                      onClick={() => {
                        if (confirm("이 입찰을 삭제하시겠습니까?")) {
                          deleteBid.mutate(r.id);
                        }
                      }}
                    >
                      <Trash2 size={14} />
                    </button>
                  ) : null,
              },
            ]}
            data={bids}
            keyField="id"
          />
        )}
        <FileUploadZone txnId={txnId} entityType="BID" embedded />
      </Card>

      {/* Bid 추가 모달 */}
      <Modal
        open={showBidModal}
        onClose={() => setShowBidModal(false)}
        title="입찰 등록"
      >
        <form
          onSubmit={(e) => {
            e.preventDefault();
            createBid.mutate(bidForm, {
              onSuccess: () => {
                setShowBidModal(false);
                setBidForm({ buyer_candidate_id: "", bid_type: "IOI" });
              },
            });
          }}
          className="space-y-4"
        >
          <Select
            label="매수자"
            options={(buyers ?? []).map((b) => ({
              value: b.id,
              label: b.company_name,
            }))}
            value={bidForm.buyer_candidate_id}
            onChange={(e) =>
              setBidForm({ ...bidForm, buyer_candidate_id: e.target.value })
            }
          />
          <div className="grid grid-cols-2 gap-4">
            <Select
              label="입찰 유형"
              options={BID_TYPE_OPTIONS}
              value={bidForm.bid_type}
              onChange={(e) =>
                setBidForm({ ...bidForm, bid_type: e.target.value as BidType })
              }
            />
            <Input
              label="금액 (원)"
              type="number"
              value={bidForm.amount ?? ""}
              onChange={(e) =>
                setBidForm({
                  ...bidForm,
                  amount: e.target.value ? Number(e.target.value) : undefined,
                })
              }
              placeholder="50000000000"
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Select
              label="밸류에이션"
              options={VALUATION_METHOD_OPTIONS}
              value={bidForm.valuation_method ?? ""}
              onChange={(e) =>
                setBidForm({
                  ...bidForm,
                  valuation_method: (e.target.value || undefined) as
                    | ValuationMethod
                    | undefined,
                })
              }
            />
            <Input
              label="배수"
              type="number"
              step="0.1"
              value={bidForm.multiple ?? ""}
              onChange={(e) =>
                setBidForm({
                  ...bidForm,
                  multiple: e.target.value ? Number(e.target.value) : undefined,
                })
              }
              placeholder="8.5"
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="제출일"
              type="date"
              value={bidForm.submitted_at ?? ""}
              onChange={(e) =>
                setBidForm({
                  ...bidForm,
                  submitted_at: e.target.value || undefined,
                })
              }
            />
            <Input
              label="유효기간"
              type="date"
              value={bidForm.valid_until ?? ""}
              onChange={(e) =>
                setBidForm({
                  ...bidForm,
                  valid_until: e.target.value || undefined,
                })
              }
            />
          </div>
          <Input
            label="조건 / 비고"
            value={bidForm.conditions ?? ""}
            onChange={(e) =>
              setBidForm({
                ...bidForm,
                conditions: e.target.value || undefined,
              })
            }
          />
          <div className="flex justify-end gap-2 pt-2">
            <Button
              variant="ghost"
              type="button"
              onClick={() => setShowBidModal(false)}
            >
              취소
            </Button>
            <Button type="submit" loading={createBid.isPending}>
              등록
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}

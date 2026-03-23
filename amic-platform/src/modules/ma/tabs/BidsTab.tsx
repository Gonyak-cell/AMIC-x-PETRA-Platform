import { useMemo, useState } from "react";
import { Plus, Trash2 } from "lucide-react";

import {
  BID_STATUS_OPTIONS,
  BID_TYPE_OPTIONS,
  BUYER_TYPE_OPTIONS,
  VALUATION_METHOD_OPTIONS,
} from "@/modules/ma/constants";
import AttachmentUploadActionButton from "@/modules/ma/components/AttachmentUploadActionButton";
import FileUploadZone from "@/modules/ma/components/FileUploadZone";
import {
  useBidComparison,
  useBids,
  useCreateBid,
  useDeleteBid,
  useImportBidFromAttachment,
  useUpdateBid,
} from "@/modules/ma/hooks/useBids";
import { useBuyers } from "@/modules/ma/hooks/useTransactions";
import type {
  BidCreate,
  BidStatus as BidStatusType,
  BidType,
  ValuationMethod,
} from "@/modules/ma/types/bid";
import { formatKRW as formatAmount } from "@/modules/ma/utils/format";

import {
  Badge,
  Button,
  Card,
  DataTable,
  INLINE_INPUT_CLS,
  Input,
  Modal,
  Select,
} from "@/components/ui";

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
  const importBidFromAttachment = useImportBidFromAttachment(txnId);

  const [showBidModal, setShowBidModal] = useState(false);
  const [uploadBuyerId, setUploadBuyerId] = useState("");
  const [uploadBidType, setUploadBidType] = useState("");
  const [bidForm, setBidForm] = useState<BidCreate>({
    buyer_candidate_id: "",
    bid_type: "IOI" as BidType,
  });

  const buyerOptions = useMemo(
    () => [
      { value: "", label: "문서에서 자동 추론" },
      ...((buyers ?? []).map((buyer) => ({
        value: buyer.id,
        label: buyer.company_name,
      })) || []),
    ],
    [buyers],
  );

  const bidTypeAssistOptions = useMemo(
    () => [
      { value: "", label: "문서에서 자동 감지" },
      ...BID_TYPE_OPTIONS,
    ],
    [],
  );

  return (
    <div className="space-y-4">
      {bidComparison && bidComparison.length > 0 && (
        <Card title="입찰 비교 매트릭스" headerBar padding="none">
          <DataTable
            columns={[
              { key: "buyer_name", header: "매수자", minWidth: "140px" },
              {
                key: "buyer_type",
                header: "유형",
                minWidth: "100px",
                render: (row) => (
                  <Badge variant="neutral">
                    {BUYER_TYPE_OPTIONS.find(
                      (option) => option.value === row.buyer_type,
                    )?.label ?? row.buyer_type}
                  </Badge>
                ),
              },
              {
                key: "ioi",
                header: "IOI",
                minWidth: "80px",
                align: "right",
                mono: true,
                render: (row) => (row.ioi ? formatAmount(row.ioi.amount) : "-"),
              },
              {
                key: "loi",
                header: "LOI",
                minWidth: "80px",
                align: "right",
                mono: true,
                render: (row) => (row.loi ? formatAmount(row.loi.amount) : "-"),
              },
              {
                key: "final_offer",
                header: "최종 제안",
                minWidth: "100px",
                align: "right",
                mono: true,
                render: (row) =>
                  row.final_offer ? formatAmount(row.final_offer.amount) : "-",
              },
            ]}
            data={bidComparison}
            keyField="buyer_id"
          />
        </Card>
      )}

      <Card
        title="입찰 이력"
        headerBar
        padding="none"
        actions={
          canWrite ? (
            <>
              <AttachmentUploadActionButton
                txnId={txnId}
                entityType="BID"
                onUploaded={async (attachment) => {
                  await importBidFromAttachment.mutateAsync({
                    attachmentId: attachment.id,
                    buyerCandidateId: uploadBuyerId || undefined,
                    bidType: (uploadBidType || undefined) as
                      | BidType
                      | undefined,
                  });
                }}
              />
              <Button
                icon={Plus}
                size="sm"
                onClick={() => setShowBidModal(true)}
                variant="ghost"
              >
              입찰 추가
            </Button>
            </>
          ) : undefined
        }
      >
        {bids?.length ? (
          <DataTable
            columns={[
              {
                key: "buyer_candidate_id",
                header: "매수자",
                render: (row) => {
                  const buyer = buyers?.find(
                    (candidate) => candidate.id === row.buyer_candidate_id,
                  );
                  return buyer?.company_name ?? row.buyer_candidate_id.slice(0, 8);
                },
              },
              {
                key: "bid_type",
                header: "유형",
                render: (row) => (
                  <Badge variant="info">
                    {BID_TYPE_OPTIONS.find(
                      (option) => option.value === row.bid_type,
                    )?.label ?? row.bid_type}
                  </Badge>
                ),
              },
              {
                key: "amount",
                header: "금액",
                align: "right",
                render: (row) => (
                  <input
                    key={`${row.id}-amount-${row.amount}`}
                    type="number"
                    className={`${INLINE_INPUT_CLS} w-28 text-right font-mono`}
                    defaultValue={row.amount ?? ""}
                    placeholder="금액"
                    onBlur={(event) => {
                      const value = event.target.value
                        ? Number(event.target.value)
                        : undefined;
                      if (value !== (row.amount ?? undefined)) {
                        updateBid.mutate({
                          bidId: row.id,
                          body: { amount: value },
                        });
                      }
                    }}
                    disabled={!canWrite}
                  />
                ),
              },
              {
                key: "valuation_method",
                header: "가치평가 방식",
                render: (row) =>
                  row.valuation_method
                    ? (VALUATION_METHOD_OPTIONS.find(
                        (option) => option.value === row.valuation_method,
                      )?.label ?? row.valuation_method)
                    : "-",
              },
              {
                key: "multiple",
                header: "배수",
                align: "right",
                mono: true,
                render: (row) =>
                  row.multiple != null ? `${row.multiple}x` : "-",
              },
              {
                key: "status",
                header: "상태",
                render: (row) => (
                  <Select
                    options={BID_STATUS_OPTIONS}
                    value={row.status}
                    onChange={(event) =>
                      updateBid.mutate({
                        bidId: row.id,
                        body: {
                          status: event.target.value as BidStatusType,
                        },
                      })
                    }
                    className="!px-1.5 !py-0.5 !text-xs"
                    disabled={!canWrite}
                  />
                ),
              },
              {
                key: "submitted_at",
                header: "제출일",
                render: (row) => (
                  <input
                    key={`${row.id}-submitted-${row.submitted_at}`}
                    type="date"
                    className={`${INLINE_INPUT_CLS} w-32`}
                    defaultValue={row.submitted_at ?? ""}
                    onChange={(event) =>
                      updateBid.mutate({
                        bidId: row.id,
                        body: {
                          submitted_at: event.target.value || undefined,
                        },
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
                render: (row) =>
                  canWrite ? (
                    <button
                      type="button"
                      className="rounded p-1 text-text-muted transition-colors hover:text-negative"
                      title="삭제"
                      onClick={() => {
                        if (confirm("이 입찰을 삭제하시겠습니까?")) {
                          deleteBid.mutate(row.id);
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
        ) : null}

        {canWrite && (
          <div className="border-t border-gray-border px-5 py-5">
            <div className="grid gap-4 xl:grid-cols-[minmax(0,240px)_minmax(0,240px)_minmax(0,1fr)] xl:items-start">
              <Select
                label="매수후보 우선 지정"
                options={buyerOptions}
                value={uploadBuyerId}
                onChange={(event) => setUploadBuyerId(event.target.value)}
                hint="비워두면 문서와 파일명에서 자동 추론합니다."
              />
              <Select
                label="입찰 유형 우선 지정"
                options={bidTypeAssistOptions}
                value={uploadBidType}
                onChange={(event) => setUploadBidType(event.target.value)}
                hint="비워두면 IOI, LOI, Final Offer를 자동 감지합니다."
              />
              <p className="rounded-2xl border border-gray-border bg-bg-cool/50 px-4 py-4 text-sm leading-6 text-text-secondary xl:self-start">
                LOI, IOI, Final Offer 문서를 업로드하면 금액, 제출일, 유효기간,
                밸류에이션 방식을 자동으로 기재합니다.
              </p>
            </div>
          </div>
        )}

        <FileUploadZone
          txnId={txnId}
          entityType="BID"
          embedded
          readOnly={!canWrite}
          embeddedLabel={bids?.length ? "입찰 문서" : "입찰 업로드"}
          uploadLabel="파일 업로드"
          emptyDescription="입찰 자료를 바로 업로드하세요."
          emptyHint="최대 50MB · PDF, DOCX, XLSX, PPTX, HWP 등"
          embeddedSeparator={false}
          showUploadAction={false}
          onUploaded={async (attachment) => {
            await importBidFromAttachment.mutateAsync({
              attachmentId: attachment.id,
              buyerCandidateId: uploadBuyerId || undefined,
              bidType: (uploadBidType || undefined) as BidType | undefined,
            });
          }}
        />
      </Card>

      <Modal
        open={showBidModal}
        onClose={() => setShowBidModal(false)}
        title="입찰 등록"
      >
        <form
          onSubmit={(event) => {
            event.preventDefault();
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
            options={(buyers ?? []).map((buyer) => ({
              value: buyer.id,
              label: buyer.company_name,
            }))}
            value={bidForm.buyer_candidate_id}
            onChange={(event) =>
              setBidForm({
                ...bidForm,
                buyer_candidate_id: event.target.value,
              })
            }
          />

          <div className="grid grid-cols-2 gap-4">
            <Select
              label="입찰 유형"
              options={BID_TYPE_OPTIONS}
              value={bidForm.bid_type}
              onChange={(event) =>
                setBidForm({
                  ...bidForm,
                  bid_type: event.target.value as BidType,
                })
              }
            />
            <Input
              label="금액 (원)"
              type="number"
              value={bidForm.amount ?? ""}
              onChange={(event) =>
                setBidForm({
                  ...bidForm,
                  amount: event.target.value
                    ? Number(event.target.value)
                    : undefined,
                })
              }
              placeholder="50000000000"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <Select
              label="가치평가 방식"
              options={VALUATION_METHOD_OPTIONS}
              value={bidForm.valuation_method ?? ""}
              onChange={(event) =>
                setBidForm({
                  ...bidForm,
                  valuation_method: (event.target.value || undefined) as
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
              onChange={(event) =>
                setBidForm({
                  ...bidForm,
                  multiple: event.target.value
                    ? Number(event.target.value)
                    : undefined,
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
              onChange={(event) =>
                setBidForm({
                  ...bidForm,
                  submitted_at: event.target.value || undefined,
                })
              }
            />
            <Input
              label="유효기간"
              type="date"
              value={bidForm.valid_until ?? ""}
              onChange={(event) =>
                setBidForm({
                  ...bidForm,
                  valid_until: event.target.value || undefined,
                })
              }
            />
          </div>

          <Input
            label="조건 / 비고"
            value={bidForm.conditions ?? ""}
            onChange={(event) =>
              setBidForm({
                ...bidForm,
                conditions: event.target.value || undefined,
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

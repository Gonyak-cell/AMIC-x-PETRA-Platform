import { useEffect, useMemo, useState } from "react";
import { FileText, Plus, Trash2 } from "lucide-react";
import {
  useCreateNda,
  useDeleteNda,
  useNdas,
  useUpdateNda,
} from "@/modules/ma/hooks/useNdas";
import { useUpdateBuyer } from "@/modules/ma/hooks/useTransactions";
import type { BuyerCandidate } from "@/modules/ma/types/buyer";
import type { NDACreate, NdaStatus } from "@/modules/ma/types/nda";
import { NDA_STATUS_OPTIONS, NDA_TYPE_OPTIONS } from "@/modules/ma/constants";
import NdaVersionPanel from "@/modules/ma/components/NdaVersionPanel";
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

interface BuyerNdaSectionProps {
  txnId: string;
  buyer: BuyerCandidate;
  canWrite: boolean;
}

function createInitialForm(buyerId: string): NDACreate {
  return {
    party_type: "BUYER",
    buyer_candidate_id: buyerId,
    nda_type: "MUTUAL",
  };
}

function shouldAdvanceToSent(status: BuyerCandidate["status"]) {
  return status === "IDENTIFIED" || status === "CONTACTED";
}

function shouldAdvanceToSigned(status: BuyerCandidate["status"]) {
  return (
    status === "IDENTIFIED" ||
    status === "CONTACTED" ||
    status === "NDA_SENT"
  );
}

export default function BuyerNdaSection({
  txnId,
  buyer,
  canWrite,
}: BuyerNdaSectionProps) {
  const { data: ndas } = useNdas(txnId, {
    buyerId: buyer.id,
    partyType: "BUYER",
  });
  const createNda = useCreateNda(txnId);
  const updateNda = useUpdateNda(txnId);
  const deleteNda = useDeleteNda(txnId);
  const updateBuyer = useUpdateBuyer(txnId);

  const [showModal, setShowModal] = useState(false);
  const [versionPanelNdaId, setVersionPanelNdaId] = useState<string | null>(
    null,
  );
  const [ndaForm, setNdaForm] = useState<NDACreate>(createInitialForm(buyer.id));

  useEffect(() => {
    setNdaForm(createInitialForm(buyer.id));
  }, [buyer.id]);

  const sortedNdas = useMemo(
    () =>
      [...(ndas ?? [])].sort((a, b) =>
        b.created_at.localeCompare(a.created_at),
      ),
    [ndas],
  );

  const maybeAdvanceBuyerStatus = (nextStatus: NdaStatus) => {
    if (!canWrite) return;

    if (nextStatus === "SIGNED" && shouldAdvanceToSigned(buyer.status)) {
      updateBuyer.mutate({
        buyerId: buyer.id,
        body: { status: "NDA_SIGNED" },
      });
      return;
    }

    if (nextStatus === "SENT" && shouldAdvanceToSent(buyer.status)) {
      updateBuyer.mutate({
        buyerId: buyer.id,
        body: { status: "NDA_SENT" },
      });
    }
  };

  const handleStatusChange = (ndaId: string, status: NdaStatus) => {
    updateNda.mutate(
      {
        ndaId,
        body: { status },
      },
      {
        onSuccess: () => maybeAdvanceBuyerStatus(status),
      },
    );
  };

  const handleSignedDateChange = (ndaId: string, signedAt?: string) => {
    updateNda.mutate(
      {
        ndaId,
        body: { signed_at: signedAt },
      },
      {
        onSuccess: () => {
          if (signedAt) {
            maybeAdvanceBuyerStatus("SIGNED");
          }
        },
      },
    );
  };

  return (
    <div className="space-y-4">
      <Card
        title="매수자 NDA"
        headerBar
        padding="none"
        actions={
          canWrite ? (
            <Button
              icon={Plus}
              size="sm"
              onClick={() => setShowModal(true)}
              variant="ghost"
            >
              NDA 추가
            </Button>
          ) : undefined
        }
      >
        {sortedNdas.length ? (
          <DataTable
            columns={[
              {
                key: "nda_type",
                header: "유형",
                render: (row) => (
                  <Badge variant="neutral">
                    {NDA_TYPE_OPTIONS.find((option) => option.value === row.nda_type)
                      ?.label ?? row.nda_type}
                  </Badge>
                ),
              },
              {
                key: "status",
                header: "상태",
                render: (row) =>
                  canWrite ? (
                    <Select
                      options={NDA_STATUS_OPTIONS}
                      value={row.status}
                      onChange={(event) =>
                        handleStatusChange(
                          row.id,
                          event.target.value as NdaStatus,
                        )
                      }
                      className="!py-0.5 !px-1.5 !text-xs"
                    />
                  ) : (
                    <span className="text-sm text-text-body">
                      {NDA_STATUS_OPTIONS.find(
                        (option) => option.value === row.status,
                      )?.label ?? row.status}
                    </span>
                  ),
              },
              {
                key: "sent_at",
                header: "발송일",
                render: (row) =>
                  canWrite ? (
                    <input
                      key={`${row.id}-sent-${row.sent_at}`}
                      type="date"
                      className={`${INLINE_INPUT_CLS} w-32`}
                      defaultValue={row.sent_at ?? ""}
                      onChange={(event) =>
                        updateNda.mutate({
                          ndaId: row.id,
                          body: { sent_at: event.target.value || undefined },
                        })
                      }
                    />
                  ) : (
                    row.sent_at ?? "-"
                  ),
              },
              {
                key: "signed_at",
                header: "체결일",
                render: (row) =>
                  canWrite ? (
                    <input
                      key={`${row.id}-signed-${row.signed_at}`}
                      type="date"
                      className={`${INLINE_INPUT_CLS} w-32`}
                      defaultValue={row.signed_at ?? ""}
                      onChange={(event) =>
                        handleSignedDateChange(
                          row.id,
                          event.target.value || undefined,
                        )
                      }
                    />
                  ) : (
                    row.signed_at ?? "-"
                  ),
              },
              {
                key: "expires_at",
                header: "만료일",
                render: (row) =>
                  canWrite ? (
                    <input
                      key={`${row.id}-expires-${row.expires_at}`}
                      type="date"
                      className={`${INLINE_INPUT_CLS} w-32`}
                      defaultValue={row.expires_at ?? ""}
                      onChange={(event) =>
                        updateNda.mutate({
                          ndaId: row.id,
                          body: { expires_at: event.target.value || undefined },
                        })
                      }
                    />
                  ) : (
                    row.expires_at ?? "-"
                  ),
              },
              {
                key: "notes",
                header: "비고",
                render: (row) => row.notes ?? "-",
              },
              {
                key: "version",
                header: "버전",
                width: "88px",
                render: (row) => (
                  <Button
                    type="button"
                    size="sm"
                    variant="ghost"
                    onClick={() => setVersionPanelNdaId(row.id)}
                    className="!px-2 !py-0.5 text-xs"
                  >
                    버전
                  </Button>
                ),
              },
              {
                key: "actions",
                header: "",
                width: "44px",
                render: (row) =>
                  canWrite ? (
                    <button
                      type="button"
                      className="rounded p-1 text-text-muted transition-colors hover:text-negative"
                      title="삭제"
                      onClick={() => {
                        if (window.confirm("이 NDA를 삭제하시겠습니까?")) {
                          deleteNda.mutate(row.id);
                        }
                      }}
                    >
                      <Trash2 size={14} />
                    </button>
                  ) : null,
              },
            ]}
            data={sortedNdas}
            keyField="id"
          />
        ) : (
          <EmptyState
            icon={FileText}
            title="NDA 없음"
            description={`${buyer.company_name}와 체결한 NDA를 등록하세요.`}
          />
        )}
      </Card>

      <Modal
        open={showModal}
        onClose={() => setShowModal(false)}
        title="NDA 추가"
      >
        <form
          onSubmit={(event) => {
            event.preventDefault();
            createNda.mutate(ndaForm, {
              onSuccess: () => {
                setShowModal(false);
                setNdaForm(createInitialForm(buyer.id));
              },
            });
          }}
          className="space-y-4"
        >
          <Input label="매수자" value={buyer.company_name} disabled />
          <Select
            label="NDA 유형"
            options={NDA_TYPE_OPTIONS}
            value={ndaForm.nda_type ?? "MUTUAL"}
            onChange={(event) =>
              setNdaForm({
                ...ndaForm,
                nda_type: event.target.value as NDACreate["nda_type"],
              })
            }
          />
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="발송일"
              type="date"
              value={ndaForm.sent_at ?? ""}
              onChange={(event) =>
                setNdaForm({
                  ...ndaForm,
                  sent_at: event.target.value || undefined,
                })
              }
            />
            <Input
              label="만료일"
              type="date"
              value={ndaForm.expires_at ?? ""}
              onChange={(event) =>
                setNdaForm({
                  ...ndaForm,
                  expires_at: event.target.value || undefined,
                })
              }
            />
          </div>
          <Input
            label="비고"
            value={ndaForm.notes ?? ""}
            onChange={(event) =>
              setNdaForm({
                ...ndaForm,
                notes: event.target.value || undefined,
              })
            }
          />
          <div className="flex justify-end gap-2 pt-2">
            <Button
              variant="ghost"
              type="button"
              onClick={() => {
                setShowModal(false);
                setNdaForm(createInitialForm(buyer.id));
              }}
            >
              취소
            </Button>
            <Button type="submit" loading={createNda.isPending}>
              등록
            </Button>
          </div>
        </form>
      </Modal>

      {versionPanelNdaId && (
        <NdaVersionPanel
          open={Boolean(versionPanelNdaId)}
          onClose={() => setVersionPanelNdaId(null)}
          txnId={txnId}
          ndaId={versionPanelNdaId}
          ndaLabel={buyer.company_name}
          canWrite={canWrite}
        />
      )}
    </div>
  );
}

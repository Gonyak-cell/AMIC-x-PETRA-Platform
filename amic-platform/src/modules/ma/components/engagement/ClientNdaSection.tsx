import { useEffect, useRef, useState } from "react";
import { FileText, Plus, Trash2, Upload } from "lucide-react";
import FileUploadZone from "@/modules/ma/components/FileUploadZone";
import ExtractionReviewModal from "@/modules/ma/components/extraction/ExtractionReviewModal";
import { useAttachmentExtractionFlow } from "@/modules/ma/hooks/useAttachmentExtractionFlow";
import {
  useCreateNda,
  useDeleteNda,
  useNdas,
  useUpdateNda,
} from "@/modules/ma/hooks/useNdas";
import { useTransaction } from "@/modules/ma/hooks/useTransactions";
import { NDA_STATUS_OPTIONS, NDA_TYPE_OPTIONS } from "@/modules/ma/constants";
import type { NDACreate, NdaStatus } from "@/modules/ma/types/nda";
import {
  Button,
  Card,
  DataTable,
  EmptyState,
  INLINE_INPUT_CLS,
  Input,
  Modal,
  Select,
} from "@/components/ui";

interface ClientNdaSectionProps {
  txnId: string;
  canWrite: boolean;
}

function createInitialForm(counterpartyName?: string): NDACreate {
  return {
    party_type: "CLIENT",
    counterparty_name: counterpartyName ?? "",
    nda_type: "MUTUAL",
  };
}

export default function ClientNdaSection({
  txnId,
  canWrite,
}: ClientNdaSectionProps) {
  const { data: transaction } = useTransaction(txnId);
  const { data: ndas } = useNdas(txnId, { partyType: "CLIENT" });
  const { activeReview, closeReview, startExtractionFromUpload } =
    useAttachmentExtractionFlow(txnId);
  const createNda = useCreateNda(txnId);
  const updateNda = useUpdateNda(txnId);
  const deleteNda = useDeleteNda(txnId);

  const [showModal, setShowModal] = useState(false);
  const [ndaForm, setNdaForm] = useState<NDACreate>(createInitialForm());
  const openUploadPickerRef = useRef<(() => void) | null>(null);

  useEffect(() => {
    setNdaForm((current) => {
      if (current.counterparty_name?.trim()) {
        return current;
      }
      return createInitialForm(transaction?.client_name);
    });
  }, [transaction?.client_name]);

  return (
    <Card
      title="클라이언트 NDA"
      headerBar
      padding="none"
      actions={
        <div className="flex flex-wrap items-center justify-end gap-1">
          <Button
            icon={Upload}
            size="sm"
            onClick={() => openUploadPickerRef.current?.()}
            variant="ghost"
          >
            NDA 업로드
          </Button>
          {canWrite ? (
            <Button
              icon={Plus}
              size="sm"
              onClick={() => setShowModal(true)}
              variant="ghost"
            >
              NDA 추가
            </Button>
          ) : null}
        </div>
      }
    >
      {ndas?.length ? (
        <DataTable
          columns={[
            {
              key: "counterparty_name",
              header: "상대방",
              render: (row) =>
                row.counterparty_name ??
                transaction?.client_name ??
                transaction?.target_company_name ??
                "-",
            },
            {
              key: "nda_type",
              header: "유형",
              render: (row) => (
                <span className="text-sm text-text-body">
                  {NDA_TYPE_OPTIONS.find((option) => option.value === row.nda_type)
                    ?.label ?? row.nda_type}
                </span>
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
                      updateNda.mutate({
                        ndaId: row.id,
                        body: { status: event.target.value as NdaStatus },
                      })
                    }
                    className="!py-0.5 !px-1.5 !text-xs"
                  />
                ) : (
                  <span className="text-sm text-text-body">
                    {NDA_STATUS_OPTIONS.find((option) => option.value === row.status)
                      ?.label ?? row.status}
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
                      updateNda.mutate({
                        ndaId: row.id,
                        body: { signed_at: event.target.value || undefined },
                      })
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
              key: "actions",
              header: "",
              width: "40px",
              render: (row) =>
                canWrite ? (
                  <button
                    type="button"
                    className="rounded p-1 text-text-muted transition-colors hover:text-negative"
                    title="삭제"
                    aria-label="클라이언트 NDA 삭제"
                    onClick={() => {
                      if (window.confirm("이 클라이언트 NDA를 삭제하시겠습니까?")) {
                        deleteNda.mutate(row.id);
                      }
                    }}
                  >
                    <Trash2 size={14} />
                  </button>
                ) : null,
            },
          ]}
          data={ndas}
          keyField="id"
        />
      ) : (
        <EmptyState
          icon={FileText}
          title="클라이언트 NDA 없음"
          description={`페트라브릿지파트너스와 ${transaction?.client_name ?? "클라이언트"} 간 NDA를 등록하세요.`}
        />
      )}

      <FileUploadZone
        txnId={txnId}
        entityType="NDA"
        embedded
        embeddedLabel={ndas?.length ? "Client NDA Files" : "Client NDA Upload"}
        uploadLabel="Upload Files"
        emptyDescription="Drop the client NDA PDF here to run OCR and prefill the review form."
        emptyHint="OCR starts for PDF uploads after VDR sync succeeds. Other files stay attached without auto-fill."
        embeddedSeparator={Boolean(ndas?.length)}
        showUploadAction={false}
        registerOpenPicker={(openPicker) => {
          openUploadPickerRef.current = openPicker;
        }}
        onUploaded={(attachment, file) =>
          startExtractionFromUpload({
            attachment,
            file,
            docCategoryHint: "NDA",
            reviewContext: { source: "client-nda" },
          })
        }
      />

      <Modal
        open={showModal}
        onClose={() => setShowModal(false)}
        title="클라이언트 NDA 추가"
      >
        <form
          onSubmit={(event) => {
            event.preventDefault();
            createNda.mutate(
              {
                ...ndaForm,
                party_type: "CLIENT",
                counterparty_name:
                  ndaForm.counterparty_name?.trim() ||
                  transaction?.client_name ||
                  undefined,
              },
              {
                onSuccess: () => {
                  setShowModal(false);
                  setNdaForm(createInitialForm(transaction?.client_name));
                },
              },
            );
          }}
          className="space-y-4"
        >
          <Input
            label="상대방"
            value={ndaForm.counterparty_name ?? ""}
            onChange={(event) =>
              setNdaForm({
                ...ndaForm,
                counterparty_name: event.target.value,
              })
            }
            placeholder={transaction?.client_name ?? "대상기업(클라이언트)"}
          />
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
                setNdaForm(createInitialForm(transaction?.client_name));
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

      <ExtractionReviewModal
        txnId={txnId}
        extraction={activeReview?.extraction ?? null}
        reviewContext={activeReview?.context}
        open={activeReview !== null}
        onClose={closeReview}
      />
    </Card>
  );
}

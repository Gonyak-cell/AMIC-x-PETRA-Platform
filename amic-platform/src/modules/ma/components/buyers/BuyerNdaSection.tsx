import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Plus, Trash2, Upload } from "lucide-react";
import { toast } from "sonner";

import { extractApiError } from "@/api/errors";
import { maApi } from "@/api/maClient";
import {
  Badge,
  Button,
  Card,
  DataTable,
  InlineSelect,
  INLINE_INPUT_CLS,
  Input,
  Modal,
  Select,
} from "@/components/ui";
import FileUploadZone from "@/modules/ma/components/FileUploadZone";
import NdaVersionPanel from "@/modules/ma/components/NdaVersionPanel";
import BuyerTeaserSection from "@/modules/ma/components/buyers/BuyerTeaserSection";
import ExtractionReviewModal from "@/modules/ma/components/extraction/ExtractionReviewModal";
import { NDA_STATUS_OPTIONS, NDA_TYPE_OPTIONS } from "@/modules/ma/constants";
import { useAttachments } from "@/modules/ma/hooks/useAttachments";
import {
  canStartExtractionFromUpload,
  useAttachmentExtractionFlow,
} from "@/modules/ma/hooks/useAttachmentExtractionFlow";
import { useCreateMarketingMaterial } from "@/modules/ma/hooks/useMarketingMaterials";
import {
  useCreateNda,
  useDeleteNda,
  useNdas,
  useUpdateNda,
} from "@/modules/ma/hooks/useNdas";
import type { Attachment } from "@/modules/ma/types/attachment";
import type { BuyerCandidate } from "@/modules/ma/types/buyer";
import type { NDACreate, NdaStatus } from "@/modules/ma/types/nda";
import type { NdaMarkup } from "@/modules/ma/types/nda_markup";

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

function getLocalDateString() {
  return new Date().toISOString().slice(0, 10);
}

function buildUploadedVersionLabel(fileName: string) {
  const stem = fileName.trim().replace(/\.[^.]+$/, "").trim();
  return stem || "업로드본";
}

function buildUploadedMarketingMaterialTitle(fileName: string, fallback: string) {
  const stem = fileName.trim().replace(/\.[^.]+$/, "").trim();
  return stem || fallback;
}

export default function BuyerNdaSection({
  txnId,
  buyer,
  canWrite,
}: BuyerNdaSectionProps) {
  const queryClient = useQueryClient();
  const { data: ndas } = useNdas(txnId, {
    buyerId: buyer.id,
    partyType: "BUYER",
  });
  const createNda = useCreateNda(txnId);
  const createMarketingMaterial = useCreateMarketingMaterial(txnId);
  const updateNda = useUpdateNda(txnId);
  const deleteNda = useDeleteNda(txnId);
  const { activeReview, closeReview, startExtractionFromUpload } =
    useAttachmentExtractionFlow(txnId);

  const [showModal, setShowModal] = useState(false);
  const [versionPanelNdaId, setVersionPanelNdaId] = useState<string | null>(
    null,
  );
  const [ndaForm, setNdaForm] = useState<NDACreate>(createInitialForm(buyer.id));
  const [pendingNdaExtractions, setPendingNdaExtractions] = useState<
    Record<string, { file: File }>
  >({});
  const openUploadPickerRef = useRef<(() => void) | null>(null);

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
  const hasNdas = sortedNdas.length > 0;
  const buyerNdaIds = useMemo(
    () => sortedNdas.map((nda) => nda.id),
    [sortedNdas],
  );

  const { data: ndaAttachmentsData } = useAttachments(txnId, "NDA", undefined, {
    refetchWhileProcessing: true,
  });
  const buyerNdaAttachments = useMemo(() => {
    if (buyerNdaIds.length === 0) {
      return [] as Attachment[];
    }

    const ndaIdSet = new Set(buyerNdaIds);
    return (ndaAttachmentsData?.items ?? []).filter(
      (attachment) =>
        attachment.entity_id !== null && ndaIdSet.has(attachment.entity_id),
    );
  }, [buyerNdaIds, ndaAttachmentsData?.items]);

  const handleStatusChange = useCallback(
    (ndaId: string, status: NdaStatus) => {
      updateNda.mutate({
        ndaId,
        body: { status },
      });
    },
    [updateNda],
  );

  const handleSignedDateChange = useCallback(
    (ndaId: string, signedAt?: string) => {
      updateNda.mutate({
        ndaId,
        body: { signed_at: signedAt },
      });
    },
    [updateNda],
  );

  const ensureBuyerNdaId = useCallback(async () => {
    const existing = sortedNdas[0];
    if (existing) {
      return existing.id;
    }

    const created = await createNda.mutateAsync({
      party_type: "BUYER",
      buyer_candidate_id: buyer.id,
      counterparty_name: buyer.company_name,
      nda_type: "MUTUAL",
    });
    return created.id;
  }, [buyer.company_name, buyer.id, createNda, sortedNdas]);

  const handleNdaUploaded = useCallback(
    async (attachment: Attachment, file: File) => {
      try {
        const targetNdaId = attachment.entity_id ?? (await ensureBuyerNdaId());
        const formData = new FormData();
        formData.append("attachment_id", attachment.id);
        formData.append("version_label", buildUploadedVersionLabel(file.name));
        formData.append("version_date", getLocalDateString());
        formData.append("changes_summary", "Buyer detail NDA upload");

        await maApi.post<NdaMarkup>(
          `/transactions/${txnId}/ndas/${targetNdaId}/markups`,
          formData,
        );

        await queryClient.invalidateQueries({
          queryKey: ["ma", "transactions", txnId, "ndas", targetNdaId, "markups"],
        });
      } catch (error) {
        toast.error(
          extractApiError(
            error,
            "파일은 업로드됐지만 NDA 버전 생성에는 실패했습니다.",
          ),
        );
        return;
      }

      if (canStartExtractionFromUpload(attachment, file)) {
        await startExtractionFromUpload(
          {
            attachment,
            file,
            docCategoryHint: "NDA",
            reviewContext: {
              source: "buyer-nda",
              buyerCandidateId: buyer.id,
            },
          },
          {
            successToast: "NDA OCR 분석을 시작했습니다.",
            failureToast:
              "파일은 업로드됐지만 OCR 시작에는 실패했습니다.",
            failureToastVariant: "warning",
          },
        );
        return;
      }

      setPendingNdaExtractions((current) => ({
        ...current,
        [attachment.id]: { file },
      }));
    },
    [buyer.id, ensureBuyerNdaId, queryClient, startExtractionFromUpload, txnId],
  );

  useEffect(() => {
    const pendingEntries = Object.entries(pendingNdaExtractions);
    if (pendingEntries.length === 0) {
      return;
    }

    const latestById = new Map(
      buyerNdaAttachments.map((attachment) => [attachment.id, attachment]),
    );
    const resolvedIds: string[] = [];

    for (const [attachmentId, pendingUpload] of pendingEntries) {
      const latestAttachment = latestById.get(attachmentId);
      if (!latestAttachment) {
        continue;
      }

      if (canStartExtractionFromUpload(latestAttachment, pendingUpload.file)) {
        resolvedIds.push(attachmentId);
        void startExtractionFromUpload(
          {
            attachment: latestAttachment,
            file: pendingUpload.file,
            docCategoryHint: "NDA",
            reviewContext: {
              source: "buyer-nda",
              buyerCandidateId: buyer.id,
            },
          },
          {
            successToast: "NDA OCR 분석을 시작했습니다.",
            failureToast:
              "파일은 업로드됐지만 OCR 시작에는 실패했습니다.",
            failureToastVariant: "warning",
          },
        );
        continue;
      }

      if (latestAttachment.processing_status === "FAILED") {
        resolvedIds.push(attachmentId);
        toast.warning(
          latestAttachment.processing_error ??
            "NDA 파일은 업로드됐지만 후속 VDR/OCR 처리에는 실패했습니다. 첨부 목록에서 재시도해 주세요.",
        );
      } else if (latestAttachment.processing_status === "SKIPPED") {
        resolvedIds.push(attachmentId);
        toast.info(
          latestAttachment.processing_error ??
            "NDA 파일은 업로드됐지만 후속 VDR/OCR 처리는 생략되었습니다.",
        );
      }
    }

    if (resolvedIds.length > 0) {
      setPendingNdaExtractions((current) => {
        const next = { ...current };
        for (const attachmentId of resolvedIds) {
          delete next[attachmentId];
        }
        return next;
      });
    }
  }, [
    buyer.id,
    buyerNdaAttachments,
    pendingNdaExtractions,
    startExtractionFromUpload,
  ]);

  const handleTeaserUploaded = useCallback(
    async (attachment: Attachment, file: File) => {
      try {
        const material = await createMarketingMaterial.mutateAsync({
          doc_type: "TM",
          title: buildUploadedMarketingMaterialTitle(
            file.name,
            `${buyer.company_name} Teaser`,
          ),
          attachment_id: attachment.id,
          distributed_to: [buyer.company_name],
          distributed_at: new Date().toISOString(),
        });

        if (!canStartExtractionFromUpload(attachment, file)) {
          return;
        }

        await startExtractionFromUpload({
          attachment,
          file,
          docCategoryHint: "TEASER_IM",
          reviewContext: {
            source: "marketing-material",
            marketingDocType: "TM",
            marketingMaterialId: material.id,
          },
        });
      } catch {
        // The upload/material hooks already show their own error toasts.
      }
    },
    [buyer.company_name, createMarketingMaterial, startExtractionFromUpload],
  );

  return (
    <div className="space-y-4">
      <Card
        title="매수자 NDA"
        headerBar
        padding="none"
        actions={
          canWrite ? (
            <div className="flex flex-wrap items-center justify-end gap-1">
              <Button
                icon={Upload}
                size="sm"
                onClick={() => openUploadPickerRef.current?.()}
                variant="ghost"
              >
                NDA 업로드
              </Button>
              <Button
                icon={Plus}
                size="sm"
                onClick={() => setShowModal(true)}
                variant="ghost"
              >
                NDA 추가
              </Button>
            </div>
          ) : undefined
        }
      >
        {hasNdas ? (
          <DataTable
            compact
            className="[&_th]:whitespace-nowrap [&_td]:align-middle"
            columns={[
              {
                key: "nda_type",
                header: <span className="whitespace-nowrap">유형</span>,
                width: "112px",
                minWidth: "112px",
                render: (row) => (
                  <Badge
                    variant="neutral"
                    className="max-w-full whitespace-nowrap !px-2 !py-1 text-[11px]"
                  >
                    {NDA_TYPE_OPTIONS.find((option) => option.value === row.nda_type)
                      ?.label ?? row.nda_type}
                  </Badge>
                ),
              },
              {
                key: "status",
                header: <span className="whitespace-nowrap">상태</span>,
                width: "88px",
                minWidth: "88px",
                render: (row) =>
                  canWrite ? (
                    <InlineSelect
                      options={NDA_STATUS_OPTIONS}
                      value={row.status}
                      onChange={(value) =>
                        handleStatusChange(row.id, value as NdaStatus)
                      }
                      className="w-[72px]"
                    />
                  ) : (
                    <span className="block whitespace-nowrap text-xs text-text-body">
                      {NDA_STATUS_OPTIONS.find(
                        (option) => option.value === row.status,
                      )?.label ?? row.status}
                    </span>
                  ),
              },
              {
                key: "sent_at",
                header: <span className="whitespace-nowrap">발송일</span>,
                width: "136px",
                minWidth: "136px",
                render: (row) =>
                  canWrite ? (
                    <input
                      key={`${row.id}-sent-${row.sent_at}`}
                      type="date"
                      className={`${INLINE_INPUT_CLS} w-[118px] min-w-0 text-[11px]`}
                      defaultValue={row.sent_at ?? ""}
                      onChange={(event) =>
                        updateNda.mutate({
                          ndaId: row.id,
                          body: { sent_at: event.target.value || undefined },
                        })
                      }
                    />
                  ) : (
                    <span className="block whitespace-nowrap text-xs">
                      {row.sent_at ?? "-"}
                    </span>
                  ),
              },
              {
                key: "signed_at",
                header: <span className="whitespace-nowrap">체결일</span>,
                width: "136px",
                minWidth: "136px",
                render: (row) =>
                  canWrite ? (
                    <input
                      key={`${row.id}-signed-${row.signed_at}`}
                      type="date"
                      className={`${INLINE_INPUT_CLS} w-[118px] min-w-0 text-[11px]`}
                      defaultValue={row.signed_at ?? ""}
                      onChange={(event) =>
                        handleSignedDateChange(
                          row.id,
                          event.target.value || undefined,
                        )
                      }
                    />
                  ) : (
                    <span className="block whitespace-nowrap text-xs">
                      {row.signed_at ?? "-"}
                    </span>
                  ),
              },
              {
                key: "expires_at",
                header: <span className="whitespace-nowrap">만료일</span>,
                width: "136px",
                minWidth: "136px",
                render: (row) =>
                  canWrite ? (
                    <input
                      key={`${row.id}-expires-${row.expires_at}`}
                      type="date"
                      className={`${INLINE_INPUT_CLS} w-[118px] min-w-0 text-[11px]`}
                      defaultValue={row.expires_at ?? ""}
                      onChange={(event) =>
                        updateNda.mutate({
                          ndaId: row.id,
                          body: { expires_at: event.target.value || undefined },
                        })
                      }
                    />
                  ) : (
                    <span className="block whitespace-nowrap text-xs">
                      {row.expires_at ?? "-"}
                    </span>
                  ),
              },
              {
                key: "notes",
                header: <span className="whitespace-nowrap">비고</span>,
                width: "52px",
                minWidth: "52px",
                render: (row) => (
                  <span
                    className="block max-w-[36px] truncate text-xs text-text-secondary"
                    title={row.notes ?? "-"}
                  >
                    {row.notes ?? "-"}
                  </span>
                ),
              },
              {
                key: "version",
                header: <span className="whitespace-nowrap">버전</span>,
                width: "56px",
                minWidth: "56px",
                render: (row) => (
                  <Button
                    type="button"
                    size="sm"
                    variant="ghost"
                    onClick={() => setVersionPanelNdaId(row.id)}
                    className="!px-1.5 !py-0.5 text-[11px]"
                  >
                    보기
                  </Button>
                ),
              },
              {
                key: "actions",
                header: "",
                width: "32px",
                minWidth: "32px",
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
        ) : null}

        <FileUploadZone
          txnId={txnId}
          entityType="NDA"
          entityIds={buyerNdaIds}
          resolveEntityId={ensureBuyerNdaId}
          embedded
          readOnly={!canWrite}
          emptyVariant="dashed"
          embeddedLabel={hasNdas ? "NDA 파일" : ""}
          uploadLabel="NDA 업로드"
          emptyTitle={hasNdas ? undefined : "NDA 없음"}
          emptyDescription={
            hasNdas
              ? "NDA PDF를 여기에 드롭하거나 클릭해 추가하세요."
              : `${buyer.company_name}와 체결한 NDA를 등록하세요.`
          }
          emptyHint={
            hasNdas
              ? "PDF 업로드 후 NDA 버전이 생성되고, 후속 VDR/OCR 처리는 상태에 따라 이어집니다."
              : "NDA PDF를 드롭하면 업로드 후 NDA 버전이 생성되고, 후속 VDR/OCR 처리는 상태에 따라 이어집니다."
          }
          embeddedSeparator={hasNdas}
          showUploadAction={false}
          registerOpenPicker={(openPicker) => {
            openUploadPickerRef.current = openPicker;
          }}
          onUploaded={handleNdaUploaded}
        />
      </Card>

      <BuyerTeaserSection
        txnId={txnId}
        buyer={buyer}
        canWrite={canWrite}
        onUploaded={handleTeaserUploaded}
      />

      <Modal open={showModal} onClose={() => setShowModal(false)} title="NDA 추가">
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

      {versionPanelNdaId ? (
        <NdaVersionPanel
          open={Boolean(versionPanelNdaId)}
          onClose={() => setVersionPanelNdaId(null)}
          txnId={txnId}
          ndaId={versionPanelNdaId}
          ndaLabel={buyer.company_name}
          canWrite={canWrite}
        />
      ) : null}

      <ExtractionReviewModal
        txnId={txnId}
        extraction={activeReview?.extraction ?? null}
        open={Boolean(activeReview)}
        onClose={closeReview}
        reviewContext={activeReview?.context}
      />
    </div>
  );
}

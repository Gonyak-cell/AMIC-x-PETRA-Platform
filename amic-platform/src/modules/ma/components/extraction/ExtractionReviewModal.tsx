import { useEffect, useMemo, useState } from "react";

import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { ENGAGEMENT_TYPE_OPTIONS, NDA_TYPE_OPTIONS } from "@/modules/ma/constants";
import { useNdas } from "@/modules/ma/hooks/useNdas";
import {
  useConfirmExtraction,
  useExtraction,
} from "@/modules/ma/hooks/useDocumentExtraction";
import {
  useBuyers,
  useEngagements,
  useTransaction,
} from "@/modules/ma/hooks/useTransactions";
import type { BuyerCandidate } from "@/modules/ma/types/buyer";
import {
  CATEGORY_LABELS,
  EXTRACTABLE_CATEGORIES,
  FIELD_LABELS,
  TARGET_MODEL_LABELS,
  getExtractionStatusLabel,
  hasMeaningfulExtractionData,
  sortDirectorsByPosition,
} from "@/modules/ma/types/document_extraction";
import type {
  DocumentExtraction,
  ExtractionConfirmRequest,
  ExtractionReviewContext,
  TargetModel,
} from "@/modules/ma/types/document_extraction";
import type { Engagement } from "@/modules/ma/types/engagement";
import type { NDA, NdaPartyType } from "@/modules/ma/types/nda";

interface Props {
  txnId: string;
  extraction: DocumentExtraction | null;
  open: boolean;
  onClose: () => void;
  reviewContext?: ExtractionReviewContext | null;
}

interface TargetOption {
  value: string;
  label: string;
}

const CATEGORY_DEFAULT_TARGET: Partial<Record<string, TargetModel>> = {
  NDA: "nda",
  ENGAGEMENT_CONTRACT: "engagement",
  LOI_MOU: "bid",
  SPA_BTA: "contract",
  CORPORATE_DOCS: "transaction",
  REGISTRY_DOCS: "transaction",
  BIZ_REG_DOCS: "transaction",
  TAX_FILING: "transaction",
  TEASER_IM: "marketing_material",
};

const CATEGORY_ALLOWED_TARGETS: Partial<Record<string, TargetModel[]>> = {
  NDA: ["nda"],
  ENGAGEMENT_CONTRACT: ["engagement"],
  LOI_MOU: ["bid"],
  SPA_BTA: ["contract"],
  CORPORATE_DOCS: ["transaction"],
  REGISTRY_DOCS: ["transaction"],
  BIZ_REG_DOCS: ["transaction"],
  TAX_FILING: ["transaction"],
  TEASER_IM: ["marketing_material"],
};

const EMPTY_BUYERS: BuyerCandidate[] = [];
const EMPTY_NDAS: NDA[] = [];
const EMPTY_ENGAGEMENTS: Engagement[] = [];

function normalizeCounterpartyName(value: string | null | undefined) {
  return (value ?? "")
    .toLowerCase()
    .replace(/\(주\)|주식회사|inc\.?|corp\.?|corporation|co\.?|ltd\.?|llc/gi, "")
    .replace(/[^a-z0-9가-힣]/gi, "");
}

function findBuyerMatches(
  counterpartyName: string | null | undefined,
  buyers: BuyerCandidate[],
) {
  const normalized = normalizeCounterpartyName(counterpartyName);
  if (!normalized) {
    return [];
  }

  return buyers.filter((buyer) => {
    const candidate = normalizeCounterpartyName(buyer.company_name);
    return (
      candidate === normalized ||
      candidate.includes(normalized) ||
      normalized.includes(candidate)
    );
  });
}

function formatNdaTargetLabel(
  nda: NDA,
  buyers: BuyerCandidate[],
  clientName?: string | null,
) {
  const buyerName =
    nda.party_type === "BUYER"
      ? buyers.find((buyer) => buyer.id === nda.buyer_candidate_id)?.company_name ??
        nda.counterparty_name ??
        "매수자 NDA"
      : nda.counterparty_name ?? clientName ?? "클라이언트 NDA";
  const dateLabel = nda.signed_at ?? nda.sent_at ?? nda.created_at.slice(0, 10);
  return `${buyerName} · ${dateLabel}`;
}

function formatEngagementTargetLabel(engagement: Engagement) {
  const typeLabel =
    ENGAGEMENT_TYPE_OPTIONS.find((option) => option.value === engagement.type)
      ?.label ?? engagement.type;
  const dateLabel =
    engagement.signed_at ?? engagement.created_at.slice(0, 10) ?? "-";
  return `${typeLabel} · ${dateLabel}`;
}

function buildConfirmedData({
  editedData,
  targetModel,
  ndaPartyType,
  selectedBuyerId,
  clientName,
  reviewContext,
}: {
  editedData: Record<string, unknown>;
  targetModel: TargetModel;
  ndaPartyType: NdaPartyType;
  selectedBuyerId: string;
  clientName?: string | null;
  reviewContext?: ExtractionReviewContext | null;
}) {
  const confirmedData = { ...editedData };

  if (targetModel === "nda") {
    confirmedData.party_type = ndaPartyType;
    if (ndaPartyType === "BUYER") {
      if (selectedBuyerId) {
        confirmedData.buyer_candidate_id = selectedBuyerId;
      }
    } else {
      delete confirmedData.buyer_candidate_id;
      if (
        typeof confirmedData.counterparty_name !== "string" ||
        !confirmedData.counterparty_name.trim()
      ) {
        confirmedData.counterparty_name = clientName ?? null;
      }
    }
  }

  if (
    targetModel === "marketing_material" &&
    reviewContext?.marketingDocType &&
    !confirmedData.doc_type
  ) {
    confirmedData.doc_type = reviewContext.marketingDocType;
  }

  return confirmedData;
}

export default function ExtractionReviewModal({
  txnId,
  extraction,
  open,
  onClose,
  reviewContext,
}: Props) {
  const confirm = useConfirmExtraction(txnId);
  const extractionId = open ? extraction?.id ?? "" : "";
  const { data: latestExtraction } = useExtraction(txnId, extractionId);
  const { data: buyersData } = useBuyers(txnId, open);
  const { data: clientNdasData } = useNdas(txnId, {
    partyType: "CLIENT",
    active: open,
  });
  const { data: buyerNdasData } = useNdas(txnId, {
    partyType: "BUYER",
    active: open,
  });
  const { data: engagementsData } = useEngagements(txnId, open);
  const { data: transaction } = useTransaction(txnId);

  const currentExtraction = latestExtraction ?? extraction;
  const buyers = useMemo(() => buyersData ?? EMPTY_BUYERS, [buyersData]);
  const clientNdas = useMemo(
    () => clientNdasData ?? EMPTY_NDAS,
    [clientNdasData],
  );
  const buyerNdas = useMemo(
    () => buyerNdasData ?? EMPTY_NDAS,
    [buyerNdasData],
  );
  const engagements = useMemo(
    () => engagementsData ?? EMPTY_ENGAGEMENTS,
    [engagementsData],
  );

  const [editedData, setEditedData] = useState<Record<string, unknown>>({});
  const [targetModel, setTargetModel] = useState<TargetModel>("nda");
  const [createNew, setCreateNew] = useState(true);
  const [targetId, setTargetId] = useState<string | undefined>(undefined);
  const [ndaPartyType, setNdaPartyType] = useState<NdaPartyType>("BUYER");
  const [selectedBuyerId, setSelectedBuyerId] = useState("");

  useEffect(() => {
    if (!currentExtraction) {
      return;
    }

    const nextEditedData = { ...(currentExtraction.extracted_data ?? {}) };
    const nextTargetModel =
      currentExtraction.target_model ??
      (currentExtraction.doc_category
        ? CATEGORY_DEFAULT_TARGET[currentExtraction.doc_category] ?? "transaction"
        : "transaction");

    let nextCreateNew = currentExtraction.target_id ? false : true;
    let nextTargetId = currentExtraction.target_id ?? undefined;
    let nextNdaPartyType =
      reviewContext?.source === "client-nda"
        ? "CLIENT"
        : ((nextEditedData.party_type as NdaPartyType | undefined) ?? "BUYER");
    let nextBuyerId =
      typeof nextEditedData.buyer_candidate_id === "string"
        ? nextEditedData.buyer_candidate_id
        : "";

    if (
      reviewContext?.source === "marketing-material" &&
      reviewContext.marketingDocType &&
      !nextEditedData.doc_type
    ) {
      nextEditedData.doc_type = reviewContext.marketingDocType;
    }

    if (nextTargetModel === "nda") {
      if (reviewContext?.source === "buyer-nda") {
        nextNdaPartyType = "BUYER";
        if (reviewContext.buyerCandidateId) {
          nextBuyerId = reviewContext.buyerCandidateId;
          nextEditedData.buyer_candidate_id = reviewContext.buyerCandidateId;
        }
      }

      nextEditedData.party_type = nextNdaPartyType;
      if (nextNdaPartyType === "BUYER") {
        if (!nextBuyerId) {
          const matches = findBuyerMatches(
            typeof nextEditedData.counterparty_name === "string"
              ? nextEditedData.counterparty_name
              : null,
            buyers,
          );
          if (matches.length === 1) {
            nextBuyerId = matches[0].id;
            nextEditedData.buyer_candidate_id = matches[0].id;
          } else {
            delete nextEditedData.buyer_candidate_id;
          }
        }

        if (!currentExtraction.target_id) {
          const existingBuyerNdas = nextBuyerId
            ? buyerNdas.filter((nda) => nda.buyer_candidate_id === nextBuyerId)
            : [];
          if (existingBuyerNdas.length > 0) {
            nextCreateNew = false;
            nextTargetId = existingBuyerNdas[0].id;
          } else {
            nextCreateNew = true;
            nextTargetId = undefined;
          }
        }
      } else {
        delete nextEditedData.buyer_candidate_id;
        if (
          !nextEditedData.counterparty_name &&
          transaction?.client_name
        ) {
          nextEditedData.counterparty_name = transaction.client_name;
        }
        if (!currentExtraction.target_id) {
          if (clientNdas.length === 1) {
            nextCreateNew = false;
            nextTargetId = clientNdas[0].id;
          } else {
            nextCreateNew = true;
            nextTargetId = undefined;
          }
        }
      }
    }

    if (nextTargetModel === "engagement" && !currentExtraction.target_id) {
      const extractedType =
        typeof nextEditedData.type === "string" ? nextEditedData.type : null;
      const sameTypeEngagements = extractedType
        ? engagements.filter((engagement) => engagement.type === extractedType)
        : [];
      if (sameTypeEngagements.length === 1) {
        nextCreateNew = false;
        nextTargetId = sameTypeEngagements[0].id;
      } else {
        nextCreateNew = true;
        nextTargetId = undefined;
      }
    }

    if (nextTargetModel === "marketing_material" && !currentExtraction.target_id) {
      nextCreateNew = true;
      nextTargetId = undefined;
    }

    setEditedData(nextEditedData);
    setTargetModel(nextTargetModel);
    setCreateNew(nextCreateNew);
    setTargetId(nextTargetId);
    setNdaPartyType(nextNdaPartyType);
    setSelectedBuyerId(nextBuyerId);
  }, [
    buyerNdas,
    buyers,
    clientNdas,
    currentExtraction,
    engagements,
    reviewContext,
    transaction?.client_name,
  ]);

  const category = currentExtraction?.doc_category;
  const fieldLabels = category ? (FIELD_LABELS[category] ?? {}) : {};
  const isExtractable = category ? EXTRACTABLE_CATEGORIES.has(category) : false;
  const allowedTargets = category
    ? (CATEGORY_ALLOWED_TARGETS[category] ?? [])
    : [];
  const hasMeaningfulData = hasMeaningfulExtractionData(editedData);
  const showEmptyExtractionNotice =
    currentExtraction?.status === "COMPLETED" &&
    isExtractable &&
    !hasMeaningfulData;

  const confidencePct = currentExtraction?.classification_confidence
    ? Math.round(currentExtraction.classification_confidence * 100)
    : null;

  const ndaTargetOptions = useMemo<TargetOption[]>(() => {
    const ndaItems =
      ndaPartyType === "CLIENT"
        ? clientNdas
        : buyerNdas.filter((nda) => nda.buyer_candidate_id === selectedBuyerId);

    return ndaItems.map((nda) => ({
      value: nda.id,
      label: formatNdaTargetLabel(nda, buyers, transaction?.client_name),
    }));
  }, [
    buyerNdas,
    buyers,
    clientNdas,
    ndaPartyType,
    selectedBuyerId,
    transaction?.client_name,
  ]);

  const engagementTargetOptions = useMemo<TargetOption[]>(
    () =>
      engagements.map((engagement) => ({
        value: engagement.id,
        label: formatEngagementTargetLabel(engagement),
      })),
    [engagements],
  );

  const targetOptions = useMemo<TargetOption[]>(() => {
    switch (targetModel) {
      case "nda":
        return ndaTargetOptions;
      case "engagement":
        return engagementTargetOptions;
      default:
        return [];
    }
  }, [engagementTargetOptions, ndaTargetOptions, targetModel]);

  useEffect(() => {
    if (createNew || targetModel === "transaction" || targetModel === "marketing_material") {
      return;
    }
    if (targetOptions.length === 0) {
      setCreateNew(true);
      setTargetId(undefined);
      return;
    }
    if (!targetId || !targetOptions.some((option) => option.value === targetId)) {
      setTargetId(targetOptions[0].value);
    }
  }, [createNew, targetId, targetModel, targetOptions]);

  if (!currentExtraction) {
    return null;
  }

  const handleFieldChange = (key: string, value: unknown) => {
    setEditedData((prev) => ({ ...prev, [key]: value }));
  };

  const handleConfirm = () => {
    const confirmedData = buildConfirmedData({
      editedData,
      targetModel,
      ndaPartyType,
      selectedBuyerId,
      clientName: transaction?.client_name,
      reviewContext,
    });
    const body: ExtractionConfirmRequest = {
      confirmed_data: confirmedData,
      target_model: targetModel,
      create_new: createNew,
      target_id:
        createNew || targetModel === "transaction" || targetModel === "marketing_material"
          ? undefined
          : targetId,
    };
    confirm.mutate(
      { extractionId: currentExtraction.id, body },
      { onSuccess: () => onClose() },
    );
  };

  const requiresBuyerSelection =
    targetModel === "nda" && ndaPartyType === "BUYER" && createNew;
  const requiresExistingTarget =
    !createNew && targetModel !== "transaction" && targetModel !== "marketing_material";
  const isConfirmable =
    currentExtraction.status === "COMPLETED" &&
    isExtractable &&
    hasMeaningfulData &&
    (!requiresBuyerSelection || Boolean(selectedBuyerId)) &&
    (!requiresExistingTarget || Boolean(targetId));

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="AI 추출 결과 검토"
      size="lg"
      footer={
        isConfirmable ? (
          <>
            <Button variant="ghost" onClick={onClose}>
              취소
            </Button>
            <Button
              variant="primary"
              onClick={handleConfirm}
              disabled={confirm.isPending}
            >
              {confirm.isPending ? "확정 중..." : "확정"}
            </Button>
          </>
        ) : (
          <Button variant="ghost" onClick={onClose}>
            닫기
          </Button>
        )
      }
    >
      <div className="space-y-5">
        <div className="flex flex-wrap items-center gap-3">
          {category && (
            <Badge variant="info" pill>
              {CATEGORY_LABELS[category] ?? category}
            </Badge>
          )}
          {confidencePct !== null && (
            <Badge variant={confidencePct >= 80 ? "success" : "warning"} pill>
              신뢰도 {confidencePct}%
            </Badge>
          )}
          <Badge
            variant={
              currentExtraction.status === "COMPLETED"
                ? hasMeaningfulData
                  ? "warning"
                  : "neutral"
                : currentExtraction.status === "CONFIRMED"
                  ? "success"
                  : currentExtraction.status === "FAILED"
                    ? "error"
                    : "info"
            }
            pill
          >
            {getExtractionStatusLabel(
              currentExtraction.status,
              editedData,
            )}
          </Badge>
          {currentExtraction.llm_cost_usd > 0 && (
            <span className="text-xs text-text-secondary">
              비용: ${currentExtraction.llm_cost_usd.toFixed(3)}
            </span>
          )}
        </div>

        {currentExtraction.error_message && (
          <div className="rounded-md bg-red-50 p-3 text-sm text-negative">
            {currentExtraction.error_message}
          </div>
        )}

        {showEmptyExtractionNotice && (
          <div className="rounded-md bg-amber-50 p-3 text-sm text-caution">
            AI가 문서에서 채울 값을 찾지 못했습니다. 필요한 항목을 직접 입력한 뒤
            확정하거나 문서 유형을 다시 확인해 주세요.
          </div>
        )}

        {isExtractable && Object.keys(fieldLabels).length > 0 && (
          <div className="space-y-3">
            <h3 className="text-sm font-semibold text-text-dark">
              추출 데이터
            </h3>
            <div className="grid grid-cols-1 gap-3">
              {Object.entries(fieldLabels).map(([key, label]) => (
                <FieldEditor
                  key={key}
                  fieldKey={key}
                  label={label}
                  value={editedData[key]}
                  onChange={(value) => handleFieldChange(key, value)}
                  disabled={currentExtraction.status === "CONFIRMED"}
                />
              ))}
            </div>
          </div>
        )}

        {!isExtractable && category && (
          <div className="rounded-md bg-bg-cool p-4 text-sm text-text-secondary">
            이 문서 유형({CATEGORY_LABELS[category]})은 현재 자동 추출을 지원하지
            않습니다. 분류 결과만 기록됩니다.
          </div>
        )}

        {isConfirmable && allowedTargets.length > 0 && (
          <div className="space-y-3 border-t border-gray-border pt-4">
            <h3 className="text-sm font-semibold text-text-dark">저장 대상</h3>

            <div className="flex items-center gap-4">
              <select
                className="flex-1 rounded border px-3 py-2 text-sm"
                value={targetModel}
                onChange={(event) =>
                  setTargetModel(event.target.value as TargetModel)
                }
              >
                {allowedTargets.map((target) => (
                  <option key={target} value={target}>
                    {TARGET_MODEL_LABELS[target]}
                  </option>
                ))}
              </select>
              {targetModel !== "transaction" && targetModel !== "marketing_material" && (
                <label className="flex items-center gap-2 text-sm text-text-secondary">
                  <input
                    type="checkbox"
                    checked={createNew}
                    onChange={(event) => setCreateNew(event.target.checked)}
                    className="rounded"
                  />
                  신규 생성
                </label>
              )}
            </div>

            {targetModel === "nda" && (
              <div className="grid gap-3 md:grid-cols-2">
                <div>
                  <label className="mb-1 block text-xs font-medium text-text-secondary">
                    NDA 대상
                  </label>
                  <select
                    className="w-full rounded border px-3 py-2 text-sm"
                    value={ndaPartyType}
                    onChange={(event) => {
                      const nextPartyType = event.target.value as NdaPartyType;
                      setNdaPartyType(nextPartyType);
                      setCreateNew(true);
                      setTargetId(undefined);
                      if (nextPartyType === "CLIENT") {
                        setSelectedBuyerId("");
                      }
                    }}
                  >
                    <option value="BUYER">매수자 NDA</option>
                    <option value="CLIENT">클라이언트 NDA</option>
                  </select>
                </div>

                {ndaPartyType === "BUYER" && (
                  <div>
                    <label className="mb-1 block text-xs font-medium text-text-secondary">
                      매수자
                    </label>
                    <select
                      className="w-full rounded border px-3 py-2 text-sm"
                      value={selectedBuyerId}
                      onChange={(event) => {
                        setSelectedBuyerId(event.target.value);
                        if (createNew) {
                          setTargetId(undefined);
                        }
                      }}
                    >
                      <option value="">매수자를 선택하세요</option>
                      {buyers.map((buyer) => (
                        <option key={buyer.id} value={buyer.id}>
                          {buyer.company_name}
                        </option>
                      ))}
                    </select>
                  </div>
                )}
              </div>
            )}

            {!createNew && targetOptions.length > 0 && (
              <div>
                <label className="mb-1 block text-xs font-medium text-text-secondary">
                  기존 레코드
                </label>
                <select
                  className="w-full rounded border px-3 py-2 text-sm"
                  value={targetId ?? ""}
                  onChange={(event) => setTargetId(event.target.value || undefined)}
                >
                  {targetOptions.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </div>
            )}
          </div>
        )}
      </div>
    </Modal>
  );
}

interface FieldEditorProps {
  fieldKey: string;
  label: string;
  value: unknown;
  onChange: (value: unknown) => void;
  disabled: boolean;
}

function FieldEditor({
  fieldKey,
  label,
  value,
  onChange,
  disabled,
}: FieldEditorProps) {
  if (fieldKey === "type") {
    return (
      <div>
        <label className="mb-1 block text-xs font-medium text-text-secondary">
          {label}
        </label>
        <select
          className="w-full rounded border px-3 py-2 text-sm"
          value={(value as string) ?? ""}
          onChange={(event) => onChange(event.target.value || null)}
          disabled={disabled}
        >
          <option value="">선택 안 함</option>
          {ENGAGEMENT_TYPE_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </div>
    );
  }

  if (fieldKey === "doc_type") {
    return (
      <div>
        <label className="mb-1 block text-xs font-medium text-text-secondary">
          {label}
        </label>
        <select
          className="w-full rounded border px-3 py-2 text-sm"
          value={(value as string) ?? ""}
          onChange={(event) => onChange(event.target.value || null)}
          disabled={disabled}
        >
          <option value="">선택 안 함</option>
          <option value="TM">TM</option>
          <option value="DM">DM</option>
          <option value="IM">IM</option>
        </select>
      </div>
    );
  }

  if (fieldKey === "nda_type") {
    return (
      <div>
        <label className="mb-1 block text-xs font-medium text-text-secondary">
          {label}
        </label>
        <select
          className="w-full rounded border px-3 py-2 text-sm"
          value={(value as string) ?? ""}
          onChange={(event) => onChange(event.target.value || null)}
          disabled={disabled}
        >
          <option value="">선택 안 함</option>
          {NDA_TYPE_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </div>
    );
  }

  if (fieldKey === "fee_structure") {
    const feeStructure =
      value && typeof value === "object" && !Array.isArray(value)
        ? (value as Record<string, unknown>)
        : {};
    const updateField = (key: string, nextValue: unknown) =>
      onChange({ ...feeStructure, [key]: nextValue });

    return (
      <div className="space-y-2">
        <label className="block text-xs font-medium text-text-secondary">
          {label}
        </label>
        <div className="grid grid-cols-2 gap-3">
          {[
            ["retainer_fee", "착수금"],
            ["success_fee_rate", "성공보수율"],
            ["minimum_fee", "최소보수"],
            ["expense_cap", "비용 한도"],
          ].map(([key, fieldLabel]) => (
            <div key={key}>
              <label className="mb-1 block text-xs text-text-secondary">
                {fieldLabel}
              </label>
              <input
                type="number"
                className="w-full rounded border px-3 py-2 text-sm"
                value={(feeStructure[key] as number | null) ?? ""}
                onChange={(event) =>
                  updateField(
                    key,
                    event.target.value ? Number(event.target.value) : null,
                  )
                }
                disabled={disabled}
              />
            </div>
          ))}
        </div>
        <div>
          <label className="mb-1 block text-xs text-text-secondary">
            보충 메모
          </label>
          <textarea
            className="w-full rounded border px-3 py-2 text-sm"
            rows={2}
            value={(feeStructure.notes as string | null) ?? ""}
            onChange={(event) => updateField("notes", event.target.value || null)}
            disabled={disabled}
          />
        </div>
      </div>
    );
  }

  if (Array.isArray(value)) {
    if (
      fieldKey === "directors" &&
      value.length > 0 &&
      typeof value[0] === "object"
    ) {
      return (
        <div>
          <label className="mb-1 block text-xs font-medium text-text-secondary">
            {label}
          </label>
          <div className="space-y-1.5">
            {sortDirectorsByPosition(
              value as Array<{
                position: string;
                name: string;
                birth_date: string | null;
                appointment_date: string | null;
              }>,
            ).map((director, index) => (
              <div key={index} className="flex items-center gap-2 text-sm">
                <span className="inline-flex items-center rounded bg-bg-cool px-1.5 py-0.5 text-xs font-medium text-text-secondary whitespace-nowrap">
                  {director.position}
                </span>
                <span className="font-medium text-text-dark">
                  {director.name}
                </span>
                {director.birth_date && (
                  <span className="text-xs text-text-tertiary">
                    {director.birth_date}
                  </span>
                )}
                {director.appointment_date && (
                  <span className="text-xs text-text-tertiary">
                    취임 {director.appointment_date}
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>
      );
    }

    return (
      <div>
        <label className="mb-1 block text-xs font-medium text-text-secondary">
          {label}
        </label>
        <textarea
          className="w-full rounded border px-3 py-2 text-sm"
          rows={Math.max(2, value.length)}
          value={value.join("\n")}
          onChange={(event) =>
            onChange(event.target.value.split("\n").filter((item) => item.trim()))
          }
          disabled={disabled}
          placeholder="한 줄에 하나씩 입력"
        />
      </div>
    );
  }

  if (typeof value === "number" || value === null) {
    const isMoneyField = [
      "proposed_amount",
      "final_purchase_price",
      "rw_cap_amount",
      "capital_amount",
      "par_value_per_share",
      "revenue",
      "cost_of_goods_sold",
      "gross_profit",
      "sga_expenses",
      "operating_income",
      "non_operating_income",
      "non_operating_expenses",
      "income_before_tax",
      "corporate_tax",
      "net_income",
      "total_assets",
      "total_liabilities",
      "total_equity",
    ].includes(fieldKey);

    return (
      <div>
        <label className="mb-1 block text-xs font-medium text-text-secondary">
          {label}
          {isMoneyField && (
            <span className="ml-1 text-text-tertiary">(원)</span>
          )}
        </label>
        <input
          type="number"
          className="w-full rounded border px-3 py-2 text-sm"
          value={value ?? ""}
          onChange={(event) =>
            onChange(event.target.value ? Number(event.target.value) : null)
          }
          disabled={disabled}
        />
      </div>
    );
  }

  if (
    fieldKey === "risk_summary" ||
    fieldKey === "service_scope_summary" ||
    fieldKey === "notes"
  ) {
    return (
      <div>
        <label className="mb-1 block text-xs font-medium text-text-secondary">
          {label}
        </label>
        <textarea
          className="w-full rounded border px-3 py-2 text-sm"
          rows={3}
          value={(value as string) ?? ""}
          onChange={(event) => onChange(event.target.value || null)}
          disabled={disabled}
        />
      </div>
    );
  }

  return (
    <div>
      <label className="mb-1 block text-xs font-medium text-text-secondary">
        {label}
      </label>
      <input
        type="text"
        className="w-full rounded border px-3 py-2 text-sm"
        value={(value as string) ?? ""}
        onChange={(event) => onChange(event.target.value || null)}
        disabled={disabled}
      />
    </div>
  );
}

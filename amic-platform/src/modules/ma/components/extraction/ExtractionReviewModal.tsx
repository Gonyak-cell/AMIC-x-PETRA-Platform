import { useState, useEffect } from "react";
import { Modal } from "@/components/ui/Modal";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { useConfirmExtraction } from "@/modules/ma/hooks/useDocumentExtraction";
import {
  CATEGORY_LABELS,
  FIELD_LABELS,
  EXTRACTABLE_CATEGORIES,
  TARGET_MODEL_LABELS,
  getExtractionStatusLabel,
  hasMeaningfulExtractionData,
  sortDirectorsByPosition,
} from "@/modules/ma/types/document_extraction";
import type {
  DocumentExtraction,
  TargetModel,
  ExtractionConfirmRequest,
} from "@/modules/ma/types/document_extraction";

interface Props {
  txnId: string;
  extraction: DocumentExtraction | null;
  open: boolean;
  onClose: () => void;
}

/** 카테고리 → 기본 매핑 대상 */
const CATEGORY_DEFAULT_TARGET: Partial<Record<string, TargetModel>> = {
  NDA: "nda",
  LOI_MOU: "bid",
  SPA_BTA: "contract",
  CORPORATE_DOCS: "transaction",
  REGISTRY_DOCS: "transaction",
  BIZ_REG_DOCS: "transaction",
  TAX_FILING: "transaction",
};

/** 카테고리별 허용 매핑 대상 */
const CATEGORY_ALLOWED_TARGETS: Partial<Record<string, TargetModel[]>> = {
  NDA: ["nda"],
  LOI_MOU: ["bid"],
  SPA_BTA: ["contract"],
  CORPORATE_DOCS: ["transaction"],
  REGISTRY_DOCS: ["transaction"],
  BIZ_REG_DOCS: ["transaction"],
  TAX_FILING: ["transaction"],
};

export default function ExtractionReviewModal({
  txnId,
  extraction,
  open,
  onClose,
}: Props) {
  const confirm = useConfirmExtraction(txnId);

  // 편집 가능한 추출 데이터 로컬 상태
  const [editedData, setEditedData] = useState<Record<string, unknown>>({});
  const [targetModel, setTargetModel] = useState<TargetModel>("nda");
  const [createNew, setCreateNew] = useState(true);

  // extraction 변경 시 로컬 상태 초기화
  useEffect(() => {
    if (extraction?.extracted_data) {
      setEditedData({ ...extraction.extracted_data });
    } else {
      setEditedData({});
    }
    if (extraction?.doc_category) {
      const defaultTarget =
        CATEGORY_DEFAULT_TARGET[extraction.doc_category] ?? "transaction";
      setTargetModel(defaultTarget);
    }
    setCreateNew(true);
  }, [extraction?.id, extraction?.extracted_data, extraction?.doc_category]);

  if (!extraction) return null;

  const category = extraction.doc_category;
  const fieldLabels = category ? (FIELD_LABELS[category] ?? {}) : {};
  const isExtractable = category ? EXTRACTABLE_CATEGORIES.has(category) : false;
  const allowedTargets = category
    ? (CATEGORY_ALLOWED_TARGETS[category] ?? [])
    : [];
  const hasMeaningfulData = hasMeaningfulExtractionData(editedData);
  const showEmptyExtractionNotice =
    extraction.status === "COMPLETED" && isExtractable && !hasMeaningfulData;

  const confidencePct = extraction.classification_confidence
    ? Math.round(extraction.classification_confidence * 100)
    : null;

  const handleFieldChange = (key: string, value: unknown) => {
    setEditedData((prev) => ({ ...prev, [key]: value }));
  };

  const handleConfirm = () => {
    const body: ExtractionConfirmRequest = {
      confirmed_data: editedData,
      target_model: targetModel,
      create_new: createNew,
    };
    confirm.mutate(
      { extractionId: extraction.id, body },
      { onSuccess: () => onClose() },
    );
  };

  const isConfirmable =
    extraction.status === "COMPLETED" && isExtractable && hasMeaningfulData;

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
        {/* 상단: 분류 정보 */}
        <div className="flex items-center gap-3 flex-wrap">
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
              extraction.status === "COMPLETED"
                ? hasMeaningfulData
                  ? "warning"
                  : "neutral"
                : extraction.status === "CONFIRMED"
                  ? "success"
                  : extraction.status === "FAILED"
                    ? "error"
                    : "info"
            }
            pill
          >
            {getExtractionStatusLabel(extraction.status, editedData)}
          </Badge>
          {extraction.llm_cost_usd > 0 && (
            <span className="text-xs text-text-secondary">
              비용: ${extraction.llm_cost_usd.toFixed(3)}
            </span>
          )}
        </div>

        {/* 에러 메시지 */}
        {extraction.error_message && (
          <div className="rounded-md bg-red-50 p-3 text-sm text-negative">
            {extraction.error_message}
          </div>
        )}

        {showEmptyExtractionNotice && (
          <div className="rounded-md bg-amber-50 p-3 text-sm text-caution">
            AI가 문서에서 채울 값을 찾지 못했습니다. 필요한 항목을 직접 입력한 뒤
            확정하거나, 문서 유형을 다시 선택해 재분석해 주세요.
          </div>
        )}

        {/* 추출 데이터 편집 폼 */}
        {isExtractable && Object.keys(fieldLabels).length > 0 && (
          <div className="space-y-3">
            <h3 className="text-sm font-semibold text-text-dark">
              추출 데이터
            </h3>
            <div className="grid grid-cols-1 gap-3">
              {Object.entries(fieldLabels).map(([key, label]) => {
                const value = editedData[key];
                return (
                  <FieldEditor
                    key={key}
                    fieldKey={key}
                    label={label}
                    value={value}
                    onChange={(v) => handleFieldChange(key, v)}
                    disabled={extraction.status === "CONFIRMED"}
                  />
                );
              })}
            </div>
          </div>
        )}

        {/* 비추출 카테고리 안내 */}
        {!isExtractable && category && (
          <div className="rounded-md bg-bg-cool p-4 text-sm text-text-secondary">
            이 문서 유형({CATEGORY_LABELS[category]})은 현재 자동 추출을
            지원하지 않습니다. 분류 결과만 기록됩니다.
          </div>
        )}

        {/* 매핑 대상 선택 */}
        {isConfirmable && allowedTargets.length > 0 && (
          <div className="space-y-3 border-t border-gray-border pt-4">
            <h3 className="text-sm font-semibold text-text-dark">매핑 대상</h3>
            <div className="flex items-center gap-4">
              <select
                className="border rounded px-3 py-2 text-sm flex-1"
                value={targetModel}
                onChange={(e) => setTargetModel(e.target.value as TargetModel)}
              >
                {allowedTargets.map((t) => (
                  <option key={t} value={t}>
                    {TARGET_MODEL_LABELS[t]}
                  </option>
                ))}
              </select>
              <label className="flex items-center gap-2 text-sm text-text-secondary">
                <input
                  type="checkbox"
                  checked={createNew}
                  onChange={(e) => setCreateNew(e.target.checked)}
                  className="rounded"
                />
                신규 생성
              </label>
            </div>
          </div>
        )}
      </div>
    </Modal>
  );
}

// ── 필드 에디터 ────────────────────────────────────────────

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
  // 배열 필드 (conditions_precedent, key_conditions, directors)
  if (Array.isArray(value)) {
    if (
      fieldKey === "directors" &&
      value.length > 0 &&
      typeof value[0] === "object"
    ) {
      return (
        <div>
          <label className="block text-xs font-medium text-text-secondary mb-1">
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
            ).map((dir, i) => {
              return (
                <div key={i} className="flex items-center gap-2 text-sm">
                  <span className="inline-flex items-center rounded bg-bg-cool px-1.5 py-0.5 text-xs font-medium text-text-secondary whitespace-nowrap">
                    {dir.position}
                  </span>
                  <span className="font-medium text-text-dark">{dir.name}</span>
                  {dir.birth_date && (
                    <span className="text-xs text-text-tertiary">
                      {dir.birth_date}
                    </span>
                  )}
                  {dir.appointment_date && (
                    <span className="text-xs text-text-tertiary">
                      취임 {dir.appointment_date}
                    </span>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      );
    }

    return (
      <div>
        <label className="block text-xs font-medium text-text-secondary mb-1">
          {label}
        </label>
        <textarea
          className="w-full border rounded px-3 py-2 text-sm"
          rows={Math.max(2, value.length)}
          value={value.join("\n")}
          onChange={(e) =>
            onChange(e.target.value.split("\n").filter((s) => s.trim()))
          }
          disabled={disabled}
          placeholder="한 줄에 하나씩 입력"
        />
      </div>
    );
  }

  // null 또는 숫자
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
        <label className="block text-xs font-medium text-text-secondary mb-1">
          {label}
          {isMoneyField && (
            <span className="text-text-tertiary ml-1">(원)</span>
          )}
        </label>
        <input
          type="number"
          className="w-full border rounded px-3 py-2 text-sm"
          value={value ?? ""}
          onChange={(e) =>
            onChange(e.target.value ? Number(e.target.value) : null)
          }
          disabled={disabled}
        />
      </div>
    );
  }

  // 긴 텍스트 (risk_summary, corporate_purpose)
  if (fieldKey === "risk_summary") {
    return (
      <div>
        <label className="block text-xs font-medium text-text-secondary mb-1">
          {label}
        </label>
        <textarea
          className="w-full border rounded px-3 py-2 text-sm"
          rows={3}
          value={(value as string) ?? ""}
          onChange={(e) => onChange(e.target.value || null)}
          disabled={disabled}
        />
      </div>
    );
  }

  // 기본: 문자열 인풋
  return (
    <div>
      <label className="block text-xs font-medium text-text-secondary mb-1">
        {label}
      </label>
      <input
        type="text"
        className="w-full border rounded px-3 py-2 text-sm"
        value={(value as string) ?? ""}
        onChange={(e) => onChange(e.target.value || null)}
        disabled={disabled}
      />
    </div>
  );
}

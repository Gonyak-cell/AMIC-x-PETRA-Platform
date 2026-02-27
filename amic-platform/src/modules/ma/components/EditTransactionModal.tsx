import { useState, useEffect } from "react";
import { ChevronDown } from "lucide-react";

import { useUpdateTransaction } from "@/modules/ma/hooks/useTransactions";
import type {
  Transaction,
  TransactionUpdate,
  TransactionSide,
  DealStructure,
  InvestmentType,
  Currency,
} from "@/modules/ma/types/transaction";
import {
  TRANSACTION_SIDE_OPTIONS,
  CURRENCY_OPTIONS,
  DEAL_STRUCTURE_OPTIONS,
  INVESTMENT_TYPE_OPTIONS,
} from "@/modules/ma/constants";

import { Button, Input, Modal, Select } from "@/components/ui";

const SIDE_OPTIONS = TRANSACTION_SIDE_OPTIONS.filter((o) => o.value !== "");

interface Props {
  open: boolean;
  onClose: () => void;
  transaction: Transaction;
}

export default function EditTransactionModal({
  open,
  onClose,
  transaction,
}: Props) {
  const updateTxn = useUpdateTransaction(transaction.id);
  const [form, setForm] = useState<TransactionUpdate>({});
  const [showOptional, setShowOptional] = useState(false);

  // 모달 열릴 때 폼 초기화
  useEffect(() => {
    if (open) {
      setForm({
        name: transaction.name,
        code_name: transaction.code_name,
        side: transaction.side,
        target_company_name: transaction.target_company_name,
        client_name: transaction.client_name,
        lead_advisor_email: transaction.lead_advisor_email,
        target_corp_code: transaction.target_corp_code ?? undefined,
        deal_structure: transaction.deal_structure,
        investment_type: transaction.investment_type,
        estimated_deal_value: transaction.estimated_deal_value,
        currency: transaction.currency,
        industry: transaction.industry,
        target_close_date: transaction.target_close_date,
        deal_captain_email: transaction.deal_captain_email,
      });
      setShowOptional(false);
    }
  }, [open, transaction]);

  const set = <K extends keyof TransactionUpdate>(
    key: K,
    val: TransactionUpdate[K],
  ) => setForm((prev) => ({ ...prev, [key]: val }));

  const canSubmit =
    (form.name ?? "").toString().trim() &&
    (form.code_name ?? "").toString().trim() &&
    (form.target_company_name ?? "").toString().trim() &&
    (form.client_name ?? "").toString().trim() &&
    (form.lead_advisor_email ?? "").toString().trim();

  // 변경된 필드만 추출
  const buildPatch = (): TransactionUpdate => {
    const patch: TransactionUpdate = {};
    if (form.name !== transaction.name) patch.name = form.name;
    if (form.code_name !== transaction.code_name)
      patch.code_name = form.code_name;
    if (form.side !== transaction.side) patch.side = form.side;
    if (form.target_company_name !== transaction.target_company_name)
      patch.target_company_name = form.target_company_name;
    if (form.client_name !== transaction.client_name)
      patch.client_name = form.client_name;
    if (form.lead_advisor_email !== transaction.lead_advisor_email)
      patch.lead_advisor_email = form.lead_advisor_email;

    const corpCode = form.target_corp_code || undefined;
    if (corpCode !== (transaction.target_corp_code ?? undefined))
      patch.target_corp_code = corpCode;

    if (form.deal_structure !== transaction.deal_structure)
      patch.deal_structure = form.deal_structure;
    if (form.investment_type !== transaction.investment_type)
      patch.investment_type = form.investment_type;
    if (form.estimated_deal_value !== transaction.estimated_deal_value)
      patch.estimated_deal_value = form.estimated_deal_value;
    if (form.currency !== transaction.currency) patch.currency = form.currency;

    const industry = form.industry || null;
    if (industry !== transaction.industry) patch.industry = industry;

    const closeDate = form.target_close_date || null;
    if (closeDate !== transaction.target_close_date)
      patch.target_close_date = closeDate;

    const captain = form.deal_captain_email || null;
    if (captain !== transaction.deal_captain_email)
      patch.deal_captain_email = captain;

    return patch;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!canSubmit) return;

    const patch = buildPatch();
    if (Object.keys(patch).length === 0) {
      onClose();
      return;
    }

    updateTxn.mutate(patch, { onSuccess: () => onClose() });
  };

  return (
    <Modal open={open} onClose={onClose} title="거래 정보 수정" size="lg">
      <form onSubmit={handleSubmit} className="space-y-5">
        {/* 필수 필드 */}
        <fieldset className="space-y-4">
          <legend className="text-xs font-semibold uppercase tracking-wider text-text-muted mb-1">
            Required
          </legend>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Input
              label="거래명"
              required
              value={form.name ?? ""}
              onChange={(e) => set("name", e.target.value)}
              placeholder="프로젝트 명칭"
            />
            <Input
              label="코드네임"
              required
              value={form.code_name ?? ""}
              onChange={(e) => set("code_name", e.target.value)}
              placeholder="보안 코드"
            />
          </div>

          <Select
            label="자문 유형"
            options={SIDE_OPTIONS}
            value={form.side ?? "SELL"}
            onChange={(e) => set("side", e.target.value as TransactionSide)}
          />

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Input
              label="대상 기업"
              required
              value={form.target_company_name ?? ""}
              onChange={(e) => set("target_company_name", e.target.value)}
              placeholder="인수/매각 대상 기업명"
            />
            <Input
              label="클라이언트"
              required
              value={form.client_name ?? ""}
              onChange={(e) => set("client_name", e.target.value)}
              placeholder="의뢰인 명칭"
            />
          </div>

          <Input
            label="리드 어드바이저 이메일"
            type="email"
            required
            value={form.lead_advisor_email ?? ""}
            onChange={(e) => set("lead_advisor_email", e.target.value)}
            placeholder="advisor@company.com"
          />
        </fieldset>

        {/* 선택 필드 토글 */}
        <button
          type="button"
          aria-expanded={showOptional}
          onClick={() => setShowOptional(!showOptional)}
          className="flex items-center gap-1.5 text-sm font-medium text-accent hover:text-accent/80 transition-colors"
        >
          <ChevronDown
            size={16}
            className={`transition-transform ${showOptional ? "rotate-180" : ""}`}
          />
          {showOptional ? "옵션 접기" : "추가 정보 수정"}
        </button>

        {showOptional && (
          <fieldset className="space-y-4 animate-fade-in">
            <legend className="text-xs font-semibold uppercase tracking-wider text-text-muted mb-1">
              Optional
            </legend>

            <Input
              label="DART Corp Code"
              value={form.target_corp_code ?? ""}
              onChange={(e) =>
                set("target_corp_code", e.target.value || undefined)
              }
              placeholder="8자리 기업 코드"
            />

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Select
                label="딜 구조"
                options={DEAL_STRUCTURE_OPTIONS}
                value={form.deal_structure ?? ""}
                onChange={(e) =>
                  set(
                    "deal_structure",
                    (e.target.value || null) as DealStructure | null,
                  )
                }
              />
              <Select
                label="투자 유형"
                options={INVESTMENT_TYPE_OPTIONS}
                value={form.investment_type ?? ""}
                onChange={(e) =>
                  set(
                    "investment_type",
                    (e.target.value || null) as InvestmentType | null,
                  )
                }
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Input
                label="예상 거래 금액"
                type="number"
                value={
                  form.estimated_deal_value != null
                    ? String(form.estimated_deal_value)
                    : ""
                }
                onChange={(e) =>
                  set(
                    "estimated_deal_value",
                    e.target.value ? Number(e.target.value) : null,
                  )
                }
                placeholder="0"
              />
              <Select
                label="통화"
                options={CURRENCY_OPTIONS}
                value={form.currency ?? "KRW"}
                onChange={(e) => set("currency", e.target.value as Currency)}
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Input
                label="산업"
                value={form.industry ?? ""}
                onChange={(e) => set("industry", e.target.value || null)}
                placeholder="산업 분류"
              />
              <Input
                label="목표 종결일"
                type="date"
                value={form.target_close_date ?? ""}
                onChange={(e) =>
                  set("target_close_date", e.target.value || null)
                }
              />
            </div>

            <Input
              label="딜 캡틴 이메일"
              type="email"
              value={form.deal_captain_email ?? ""}
              onChange={(e) =>
                set("deal_captain_email", e.target.value || null)
              }
              placeholder="captain@company.com"
            />
          </fieldset>
        )}

        {/* 제출 */}
        <div className="flex justify-end gap-3 pt-4 border-t">
          <Button variant="ghost" type="button" onClick={onClose}>
            취소
          </Button>
          <Button
            type="submit"
            disabled={!canSubmit}
            loading={updateTxn.isPending}
          >
            저장
          </Button>
        </div>
      </form>
    </Modal>
  );
}

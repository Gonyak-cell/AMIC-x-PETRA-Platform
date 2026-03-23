import { useEffect, useMemo, useState } from "react";

import { Button, Input, Modal, Select } from "@/components/ui";
import { BUYER_TIER_OPTIONS, DEAL_ROLE_OPTIONS } from "@/modules/ma/constants";
import { useAddBuyer } from "@/modules/ma/hooks/useTransactions";
import type {
  BuyerCandidateCreate,
  BuyerTier,
  DealRole,
} from "@/modules/ma/types/buyer";

type ManualBuyerKind = "FI" | "SI";

interface ManualBuyerAddModalProps {
  open: boolean;
  onClose: () => void;
  txnId: string;
  kind: ManualBuyerKind;
  existingCompanyNames: string[];
}

interface ManualBuyerFormState {
  company_name: string;
  contact_name: string;
  contact_email: string;
  contact_phone: string;
  tier: string;
  deal_role: string;
  notes: string;
}

const INITIAL_FORM: ManualBuyerFormState = {
  company_name: "",
  contact_name: "",
  contact_email: "",
  contact_phone: "",
  tier: "",
  deal_role: "",
  notes: "",
};

const PRESET_BY_KIND: Record<
  ManualBuyerKind,
  {
    title: string;
    description: string;
    buyerType: BuyerCandidateCreate["buyer_type"];
    badgeLabel: string;
  }
> = {
  FI: {
    title: "FI 추가",
    description: "재무적 투자자 후보를 Long List에 직접 추가합니다.",
    buyerType: "FINANCIAL_SPONSOR",
    badgeLabel: "재무적 투자자 (FI)",
  },
  SI: {
    title: "SI 추가",
    description: "전략적 투자자 후보를 Long List에 직접 추가합니다.",
    buyerType: "STRATEGIC",
    badgeLabel: "전략적 투자자 (SI)",
  },
};

function trimOrUndefined(value: string) {
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : undefined;
}

export default function ManualBuyerAddModal({
  open,
  onClose,
  txnId,
  kind,
  existingCompanyNames,
}: ManualBuyerAddModalProps) {
  const addBuyer = useAddBuyer(txnId);
  const preset = PRESET_BY_KIND[kind];
  const [form, setForm] = useState<ManualBuyerFormState>(INITIAL_FORM);
  const [submitAttempted, setSubmitAttempted] = useState(false);

  useEffect(() => {
    if (!open) return;
    setForm(INITIAL_FORM);
    setSubmitAttempted(false);
  }, [open, kind]);

  const existingNameSet = useMemo(
    () =>
      new Set(
        existingCompanyNames
          .map((name) => name.trim().toLowerCase())
          .filter(Boolean),
      ),
    [existingCompanyNames],
  );

  const normalizedCompanyName = form.company_name.trim();
  const isDuplicateCompanyName =
    normalizedCompanyName.length > 0 &&
    existingNameSet.has(normalizedCompanyName.toLowerCase());
  const companyNameError =
    submitAttempted && !normalizedCompanyName
      ? "회사명을 입력해주세요."
      : isDuplicateCompanyName
        ? "이미 Long List에 등록된 회사입니다."
        : undefined;

  const tierOptions = useMemo(
    () => [
      { value: "", label: "선택 안 함" },
      ...BUYER_TIER_OPTIONS.filter((option) => option.value !== ""),
    ],
    [],
  );

  const dealRoleOptions = useMemo(
    () => [
      { value: "", label: "선택 안 함" },
      ...DEAL_ROLE_OPTIONS.filter((option) => option.value !== ""),
    ],
    [],
  );

  const handleClose = () => {
    if (addBuyer.isPending) return;
    onClose();
  };

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setSubmitAttempted(true);

    if (!normalizedCompanyName || isDuplicateCompanyName) {
      return;
    }

    addBuyer.mutate(
      {
        company_name: normalizedCompanyName,
        contact_name: trimOrUndefined(form.contact_name),
        contact_email: trimOrUndefined(form.contact_email),
        contact_phone: trimOrUndefined(form.contact_phone),
        buyer_type: preset.buyerType,
        tier: (form.tier || undefined) as BuyerTier | undefined,
        deal_role: (form.deal_role || undefined) as DealRole | undefined,
        notes: trimOrUndefined(form.notes),
      },
      {
        onSuccess: () => {
          setForm(INITIAL_FORM);
          setSubmitAttempted(false);
          onClose();
        },
      },
    );
  };

  return (
    <Modal open={open} onClose={handleClose} title={preset.title}>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="rounded-xl border border-accent/10 bg-accent/5 px-4 py-3">
          <div className="flex flex-wrap items-center gap-2">
            <span className="inline-flex rounded-full bg-white px-2.5 py-1 text-xs font-medium text-accent shadow-sm">
              {preset.badgeLabel}
            </span>
            <p className="text-sm text-text-secondary">{preset.description}</p>
          </div>
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          <Input
            label="회사명"
            required
            value={form.company_name}
            onChange={(e) => setForm({ ...form, company_name: e.target.value })}
            error={companyNameError}
            placeholder="회사명을 입력하세요"
          />
          <Input
            label="담당자"
            value={form.contact_name}
            onChange={(e) => setForm({ ...form, contact_name: e.target.value })}
            placeholder="선택 입력"
          />
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          <Input
            label="이메일"
            type="email"
            value={form.contact_email}
            onChange={(e) =>
              setForm({ ...form, contact_email: e.target.value })
            }
            placeholder="name@example.com"
          />
          <Input
            label="전화번호"
            value={form.contact_phone}
            onChange={(e) =>
              setForm({ ...form, contact_phone: e.target.value })
            }
            placeholder="선택 입력"
          />
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          <Select
            label="Tier"
            options={tierOptions}
            value={form.tier}
            onChange={(e) => setForm({ ...form, tier: e.target.value })}
          />
          <Select
            label="역할"
            options={dealRoleOptions}
            value={form.deal_role}
            onChange={(e) => setForm({ ...form, deal_role: e.target.value })}
          />
        </div>

        <div>
          <label
            htmlFor={`${kind.toLowerCase()}-manual-buyer-notes`}
            className="mb-1.5 block text-sm font-medium text-text-body"
          >
            메모
          </label>
          <textarea
            id={`${kind.toLowerCase()}-manual-buyer-notes`}
            rows={3}
            value={form.notes}
            onChange={(e) => setForm({ ...form, notes: e.target.value })}
            placeholder="필요한 메모가 있으면 남겨주세요"
            className="w-full rounded-dr-sm border border-gray-border bg-white px-3 py-2 text-sm text-text-body shadow-sm transition-colors placeholder:text-text-secondary hover:border-amic-400 focus:border-amic focus:outline-none focus:ring-2 focus:ring-accent/30"
          />
        </div>

        <div className="flex justify-end gap-2 pt-2">
          <Button
            variant="ghost"
            type="button"
            onClick={handleClose}
            disabled={addBuyer.isPending}
          >
            취소
          </Button>
          <Button type="submit" loading={addBuyer.isPending}>
            추가
          </Button>
        </div>
      </form>
    </Modal>
  );
}

export type { ManualBuyerKind };

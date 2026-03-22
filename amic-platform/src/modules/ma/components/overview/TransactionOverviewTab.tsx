import { useAuth } from "@/hooks/useAuth";
import { cn } from "@/lib/cn";
import { toast } from "sonner";

import { useUpdateTransaction } from "@/modules/ma/hooks/useTransactions";
import { getTransactionTextError } from "@/modules/ma/utils/transactionText";
import type {
  Currency,
  DealType,
  DealStructure,
  InvestmentType,
  SaleProcess,
  ControlTransfer,
  ValuationBasis,
  CrossBorder,
} from "@/modules/ma/types/transaction";
import type { Transaction } from "@/modules/ma/types/transaction";
import {
  DEAL_TYPE_OPTIONS,
  DEAL_STRUCTURE_OPTIONS,
  INVESTMENT_TYPE_OPTIONS,
  CURRENCY_OPTIONS,
  SALE_PROCESS_OPTIONS,
  CONTROL_TRANSFER_OPTIONS,
  VALUATION_BASIS_OPTIONS,
  CROSS_BORDER_OPTIONS,
  TARGET_BUYER_TYPE_OPTIONS,
  TEAM_MEMBERS,
} from "@/modules/ma/constants";
import CompanyInfoCard from "@/modules/ma/components/overview/CompanyInfoCard";

import { Card, InlineSelect, InlineCombobox, INLINE_INPUT_CLS } from "@/components/ui";

interface TransactionOverviewTabProps {
  txn: Transaction;
}

export default function TransactionOverviewTab({
  txn,
}: TransactionOverviewTabProps) {
  const { canWrite } = useAuth();
  const updateTxn = useUpdateTransaction(txn.id);

  const handleValidatedTextBlur = (
    event: React.FocusEvent<HTMLInputElement>,
    currentValue: string,
    onValid: (value: string) => void,
  ) => {
    const nextValue = event.currentTarget.value.trim();

    if (!nextValue) {
      event.currentTarget.value = currentValue;
      return;
    }

    const error = getTransactionTextError(nextValue);
    if (error) {
      toast.error(error);
      event.currentTarget.value = currentValue;
      return;
    }

    if (nextValue !== currentValue) {
      onValid(nextValue);
      return;
    }

    event.currentTarget.value = currentValue;
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* 거래 정보 — 2-Column */}
      <Card
        title="거래 정보"
        headerBar
        className="lg:col-span-2"
        data-onboarding="deal-info"
      >
        <div className="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-0 p-1 md:items-start">
          {/* ── 좌측 열: 기본 딜 정보 ── */}
          <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-3 text-sm items-center">
            <dt className="text-text-muted">거래명</dt>
            <dd>
              <input
                key={`name-${txn.updated_at}`}
                type="text"
                className={cn(INLINE_INPUT_CLS, "w-64")}
                defaultValue={txn.name}
                onBlur={(e) =>
                  handleValidatedTextBlur(e, txn.name, (value) =>
                    updateTxn.mutate({ name: value }),
                  )
                }
                disabled={!canWrite()}
              />
            </dd>
            <dt className="text-text-muted">코드네임</dt>
            <dd>
              <span className="font-mono text-sm font-medium text-accent select-all">
                {txn.code_name}
              </span>
            </dd>
            <dt className="text-text-muted">대상기업</dt>
            <dd>
              <input
                key={`target-${txn.updated_at}`}
                type="text"
                className={cn(INLINE_INPUT_CLS, "w-48")}
                defaultValue={txn.target_company_name}
                onBlur={(e) =>
                  handleValidatedTextBlur(e, txn.target_company_name, (value) =>
                    updateTxn.mutate({ target_company_name: value }),
                  )
                }
                disabled={!canWrite()}
              />
            </dd>
            <dt className="text-text-muted">클라이언트</dt>
            <dd>
              <input
                key={`client-${txn.updated_at}`}
                type="text"
                className={cn(INLINE_INPUT_CLS, "w-48")}
                defaultValue={txn.client_name}
                onBlur={(e) =>
                  handleValidatedTextBlur(e, txn.client_name, (value) =>
                    updateTxn.mutate({ client_name: value }),
                  )
                }
                disabled={!canWrite()}
              />
            </dd>
            <dt className="text-text-muted">딜 구조</dt>
            <dd>
              <InlineSelect
                options={DEAL_TYPE_OPTIONS}
                value={txn.deal_type}
                onChange={(v) =>
                  updateTxn.mutate({
                    deal_type: (v || "SE") as DealType,
                  })
                }
                disabled={!canWrite()}
              />
            </dd>
            <dt className="text-text-muted">세부 거래 구조</dt>
            <dd>
              <InlineSelect
                options={DEAL_STRUCTURE_OPTIONS}
                value={txn.deal_structure ?? ""}
                onChange={(v) =>
                  updateTxn.mutate({
                    deal_structure: (v || null) as DealStructure | null,
                  })
                }
                disabled={!canWrite()}
              />
            </dd>
            <dt className="text-text-muted">투자 유형</dt>
            <dd>
              <InlineSelect
                options={INVESTMENT_TYPE_OPTIONS}
                value={txn.investment_type ?? ""}
                onChange={(v) =>
                  updateTxn.mutate({
                    investment_type: (v || null) as InvestmentType | null,
                  })
                }
                disabled={!canWrite()}
              />
            </dd>
            <dt className="text-text-muted">산업</dt>
            <dd>
              <input
                key={`industry-${txn.updated_at}`}
                type="text"
                className={cn(INLINE_INPUT_CLS, "w-40")}
                defaultValue={txn.industry ?? ""}
                onBlur={(e) => {
                  const v = e.target.value.trim();
                  if (v !== (txn.industry ?? ""))
                    updateTxn.mutate({ industry: v || null });
                }}
                disabled={!canWrite()}
                placeholder="-"
              />
            </dd>
            <dt className="text-text-muted">예상 금액</dt>
            <dd className="flex items-center gap-1">
              <input
                key={`deal-val-${txn.updated_at}`}
                type="number"
                className={cn(INLINE_INPUT_CLS, "w-32 text-right font-mono")}
                defaultValue={txn.estimated_deal_value ?? ""}
                onBlur={(e) => {
                  const v = e.target.value || null;
                  if (v !== txn.estimated_deal_value)
                    updateTxn.mutate({ estimated_deal_value: v });
                }}
                disabled={!canWrite()}
                placeholder="-"
              />
              <InlineSelect
                options={CURRENCY_OPTIONS}
                value={txn.currency}
                onChange={(v) => updateTxn.mutate({ currency: v as Currency })}
                disabled={!canWrite()}
              />
            </dd>
            <dt className="text-text-muted">목표 종결일</dt>
            <dd>
              <input
                type="date"
                className={cn(INLINE_INPUT_CLS, "w-36")}
                value={txn.target_close_date ?? ""}
                onChange={(e) =>
                  updateTxn.mutate({
                    target_close_date: e.target.value || null,
                  })
                }
                disabled={!canWrite()}
              />
            </dd>
            <dt className="text-text-muted">리드 어드바이저</dt>
            <dd>
              <InlineCombobox
                options={TEAM_MEMBERS.map((m) => ({
                  value: m.email,
                  label: `${m.name} (${m.title})`,
                  description: m.email,
                }))}
                value={txn.lead_advisor_email}
                onChange={(v) => {
                  if (v && v !== txn.lead_advisor_email)
                    updateTxn.mutate({ lead_advisor_email: v });
                }}
                disabled={!canWrite()}
                placeholder="담당자 검색..."
                clearable={false}
              />
            </dd>
            <dt className="text-text-muted">딜 캡틴</dt>
            <dd>
              <InlineCombobox
                options={TEAM_MEMBERS.map((m) => ({
                  value: m.email,
                  label: `${m.name} (${m.title})`,
                  description: m.email,
                }))}
                value={txn.deal_captain_email ?? ""}
                onChange={(v) => {
                  if (v !== (txn.deal_captain_email ?? ""))
                    updateTxn.mutate({ deal_captain_email: v || null });
                }}
                disabled={!canWrite()}
                placeholder="담당자 검색..."
              />
            </dd>
          </dl>

          {/* ── 우측 열: 딜 상세 구조 ── */}
          <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-3 text-sm items-center">
            <dt className="text-text-muted">매각 방식</dt>
            <dd>
              <InlineSelect
                options={SALE_PROCESS_OPTIONS}
                value={txn.sale_process ?? ""}
                onChange={(v) =>
                  updateTxn.mutate({
                    sale_process: (v || null) as SaleProcess | null,
                  })
                }
                disabled={!canWrite()}
              />
            </dd>
            <dt className="text-text-muted">경영권</dt>
            <dd>
              <InlineSelect
                options={CONTROL_TRANSFER_OPTIONS}
                value={txn.control_transfer ?? ""}
                onChange={(v) =>
                  updateTxn.mutate({
                    control_transfer: (v || null) as ControlTransfer | null,
                  })
                }
                disabled={!canWrite()}
              />
            </dd>
            <dt className="text-text-muted">대상 지분율</dt>
            <dd className="flex items-center gap-1">
              <input
                key={`stake-${txn.updated_at}`}
                type="number"
                className={cn(INLINE_INPUT_CLS, "w-20 text-right font-mono")}
                defaultValue={txn.target_stake ?? ""}
                min={0}
                max={100}
                step={0.01}
                onBlur={(e) => {
                  const v = e.target.value ? Number(e.target.value) : null;
                  if (v !== txn.target_stake)
                    updateTxn.mutate({ target_stake: v });
                }}
                disabled={!canWrite()}
                placeholder="-"
              />
              <span className="text-xs text-text-muted">%</span>
            </dd>
            <dt className="text-text-muted">신주/구주</dt>
            <dd className="flex items-center gap-1">
              <input
                key={`new-share-${txn.updated_at}`}
                type="number"
                className={cn(INLINE_INPUT_CLS, "w-16 text-right font-mono")}
                defaultValue={txn.new_share_ratio ?? ""}
                min={0}
                max={100}
                step={0.01}
                onBlur={(e) => {
                  const v = e.target.value ? Number(e.target.value) : null;
                  if (v !== txn.new_share_ratio)
                    updateTxn.mutate({ new_share_ratio: v });
                }}
                disabled={!canWrite()}
                placeholder="신주"
              />
              <span className="text-xs text-text-muted">/</span>
              <input
                key={`old-share-${txn.updated_at}`}
                type="number"
                className={cn(INLINE_INPUT_CLS, "w-16 text-right font-mono")}
                defaultValue={txn.old_share_ratio ?? ""}
                min={0}
                max={100}
                step={0.01}
                onBlur={(e) => {
                  const v = e.target.value ? Number(e.target.value) : null;
                  if (v !== txn.old_share_ratio)
                    updateTxn.mutate({ old_share_ratio: v });
                }}
                disabled={!canWrite()}
                placeholder="구주"
              />
              <span className="text-xs text-text-muted">%</span>
            </dd>
            <dt className="text-text-muted">밸류에이션 기준</dt>
            <dd>
              <InlineSelect
                options={VALUATION_BASIS_OPTIONS}
                value={txn.valuation_basis ?? ""}
                onChange={(v) =>
                  updateTxn.mutate({
                    valuation_basis: (v || null) as ValuationBasis | null,
                  })
                }
                disabled={!canWrite()}
              />
            </dd>
            <dt className="text-text-muted">Cross-border</dt>
            <dd>
              <InlineSelect
                options={CROSS_BORDER_OPTIONS}
                value={txn.cross_border ?? ""}
                onChange={(v) =>
                  updateTxn.mutate({
                    cross_border: (v || null) as CrossBorder | null,
                  })
                }
                disabled={!canWrite()}
              />
            </dd>
            <dt className="text-text-muted">타겟 매수자</dt>
            <dd className="flex items-center gap-1.5 flex-wrap">
              {TARGET_BUYER_TYPE_OPTIONS.map((opt) => {
                const selected = (txn.target_buyer_types ?? []).includes(
                  opt.value as "STRATEGIC" | "FINANCIAL_SPONSOR",
                );
                return (
                  <button
                    key={opt.value}
                    type="button"
                    disabled={!canWrite()}
                    className={cn(
                      "px-2 py-0.5 rounded-full text-xs border transition-colors",
                      selected
                        ? "bg-amic/10 border-amic text-amic font-medium"
                        : "bg-transparent border-gray-border text-text-secondary hover:border-amic/50",
                    )}
                    onClick={() => {
                      const current = txn.target_buyer_types ?? [];
                      const next = selected
                        ? current.filter((v) => v !== opt.value)
                        : [
                            ...current,
                            opt.value as "STRATEGIC" | "FINANCIAL_SPONSOR",
                          ];
                      updateTxn.mutate({
                        target_buyer_types: next.length > 0 ? next : null,
                      });
                    }}
                  >
                    {opt.label}
                  </button>
                );
              })}
            </dd>
            <dt className="text-text-muted">배타적 협상권</dt>
            <dd className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={txn.exclusivity ?? false}
                onChange={(e) => {
                  const checked = e.target.checked;
                  updateTxn.mutate({
                    exclusivity: checked,
                    ...(checked ? {} : { exclusivity_deadline: null }),
                  });
                }}
                disabled={!canWrite()}
                className="h-3.5 w-3.5 rounded border-gray-border accent-amic"
              />
              {txn.exclusivity && (
                <input
                  type="date"
                  className={cn(INLINE_INPUT_CLS, "w-36")}
                  value={txn.exclusivity_deadline ?? ""}
                  onChange={(e) =>
                    updateTxn.mutate({
                      exclusivity_deadline: e.target.value || null,
                    })
                  }
                  disabled={!canWrite()}
                />
              )}
            </dd>
          </dl>
        </div>
      </Card>
      {/* 회사 정보 — 전체 너비 */}
      <div className="lg:col-span-2" data-onboarding="company-info">
        <CompanyInfoCard txn={txn} canWrite={canWrite()} />
      </div>

    </div>
  );
}

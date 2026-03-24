import { useEffect, useState, type ReactNode } from "react";
import { toast } from "sonner";

import { Badge, Button, Input, Select, Spinner } from "@/components/ui";
import {
  BUYER_STATUS_OPTIONS,
  BUYER_TIER_OPTIONS,
  BUYER_TYPE_OPTIONS,
  DEAL_ROLE_OPTIONS,
} from "@/modules/ma/constants";
import { useDartFinancialSummary } from "@/modules/ma/hooks/useDartIntegration";
import { useUpdateBuyer } from "@/modules/ma/hooks/useTransactions";
import type {
  BuyerCandidate,
  BuyerCandidateUpdate,
  BuyerTier,
  DealRole,
} from "@/modules/ma/types/buyer";
import type { BuyerStageSummary } from "@/modules/ma/types/marketing_log";
import {
  getBuyerLogoUrl,
  mergeBuyerLogoExtraData,
  normalizeBuyerLogoUrl,
} from "@/modules/ma/utils/buyerLogo";

import BuyerCompanyLogo from "./BuyerCompanyLogo";
import BuyerTierBadge from "./BuyerTierBadge";
import DealRoleBadge from "./DealRoleBadge";
import MarketingStageTracker from "./MarketingStageTracker";

interface BuyerSummarySectionProps {
  buyer: BuyerCandidate;
  txnId: string;
  stageSummary: BuyerStageSummary | undefined;
  canWrite: boolean;
}

interface BuyerSummaryFormState {
  company_name: string;
  logo_url: string;
  buyer_type: BuyerCandidate["buyer_type"];
  tier: BuyerTier | "";
  deal_role: DealRole | "";
  contact_name: string;
  contact_email: string;
  contact_phone: string;
  notes: string;
}

function createInitialForm(buyer: BuyerCandidate): BuyerSummaryFormState {
  return {
    company_name: buyer.company_name,
    logo_url: getBuyerLogoUrl(buyer.extra_data) ?? "",
    buyer_type: buyer.buyer_type,
    tier: buyer.tier ?? "",
    deal_role: buyer.deal_role ?? "",
    contact_name: buyer.contact_name ?? "",
    contact_email: buyer.contact_email ?? "",
    contact_phone: buyer.contact_phone ?? "",
    notes: buyer.notes ?? "",
  };
}

function trimToNull(value: string): string | null {
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : null;
}

function getOptionLabel(
  options: { value: string; label: string }[],
  value: string,
): string {
  const match = options.find((option) => option.value === value);
  return match?.label ?? value;
}

function formatAmountKRW(value: number): string {
  if (Math.abs(value) >= 1_0000_0000) {
    return `${(value / 1_0000_0000).toLocaleString("ko-KR", {
      maximumFractionDigits: 1,
    })}억원`;
  }
  if (Math.abs(value) >= 1_0000) {
    return `${(value / 1_0000).toLocaleString("ko-KR", {
      maximumFractionDigits: 0,
    })}만원`;
  }
  return `${value.toLocaleString("ko-KR")}원`;
}

function InfoItem({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}) {
  return (
    <div>
      <dt className="text-xs text-text-muted">{label}</dt>
      <dd className="mt-0.5 text-sm font-medium">{children}</dd>
    </div>
  );
}

export default function BuyerSummarySection({
  buyer,
  txnId,
  stageSummary,
  canWrite,
}: BuyerSummarySectionProps) {
  const hasDart = !!buyer.corp_code;
  const { data: dartSummary, isLoading: dartLoading, isError: dartError } =
    useDartFinancialSummary(txnId, buyer.id, hasDart);
  const updateBuyer = useUpdateBuyer(txnId);
  const [isEditing, setIsEditing] = useState(false);
  const [form, setForm] = useState<BuyerSummaryFormState>(() =>
    createInitialForm(buyer),
  );

  useEffect(() => {
    setForm(createInitialForm(buyer));
    setIsEditing(false);
  }, [buyer]);

  const statusLabel = getOptionLabel(BUYER_STATUS_OPTIONS, buyer.status);
  const typeLabel = getOptionLabel(BUYER_TYPE_OPTIONS, buyer.buyer_type);
  const currentLogoUrl = getBuyerLogoUrl(buyer.extra_data);

  const handleSave = () => {
    const companyName = form.company_name.trim();
    if (!companyName) {
      toast.error("회사명을 입력해 주세요.");
      return;
    }

    const rawLogoUrl = form.logo_url.trim();
    const normalizedLogoUrl = normalizeBuyerLogoUrl(rawLogoUrl);
    if (rawLogoUrl && !normalizedLogoUrl) {
      toast.error(
        "로고 URL은 https://, http://, / 로 시작하거나 data:image 형식이어야 합니다.",
      );
      return;
    }

    const body: BuyerCandidateUpdate = {
      company_name: companyName,
      buyer_type: form.buyer_type,
      tier: form.tier || null,
      deal_role: form.deal_role || null,
      contact_name: trimToNull(form.contact_name),
      contact_email: trimToNull(form.contact_email),
      contact_phone: trimToNull(form.contact_phone),
      notes: trimToNull(form.notes),
      extra_data: mergeBuyerLogoExtraData(buyer.extra_data, normalizedLogoUrl),
    };

    updateBuyer.mutate(
      {
        buyerId: buyer.id,
        body,
      },
      {
        onSuccess: () => {
          setIsEditing(false);
        },
      },
    );
  };

  const handleCancel = () => {
    setForm(createInitialForm(buyer));
    setIsEditing(false);
  };

  return (
    <div className="space-y-6">
      <section>
        <div className="mb-3 flex items-center justify-between gap-3">
          <h3 className="text-sm font-semibold text-text-dark">기본 정보</h3>
          {canWrite && (
            <div className="flex items-center gap-2">
              {isEditing ? (
                <>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={handleCancel}
                    disabled={updateBuyer.isPending}
                  >
                    취소
                  </Button>
                  <Button
                    type="button"
                    size="sm"
                    onClick={handleSave}
                    loading={updateBuyer.isPending}
                  >
                    저장
                  </Button>
                </>
              ) : (
                <Button
                  type="button"
                  variant="secondary"
                  size="sm"
                  onClick={() => setIsEditing(true)}
                >
                  롱리스트 정보 수정
                </Button>
              )}
            </div>
          )}
        </div>

        {isEditing ? (
          <div className="space-y-4 rounded-dr border border-gray-border bg-bg-secondary/40 p-4">
            <div className="grid gap-4 md:grid-cols-2">
              <Input
                label="회사명"
                value={form.company_name}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    company_name: event.target.value,
                  }))
                }
              />
              <Select
                label="유형"
                options={BUYER_TYPE_OPTIONS.filter((option) => option.value)}
                value={form.buyer_type}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    buyer_type: event.target.value as BuyerCandidate["buyer_type"],
                  }))
                }
              />
              <div className="md:col-span-2">
                <Input
                  label="로고 URL"
                  type="url"
                  value={form.logo_url}
                  onChange={(event) =>
                    setForm((current) => ({
                      ...current,
                      logo_url: event.target.value,
                    }))
                  }
                  placeholder="https://... 또는 /buyer-logos/...png"
                  hint="나중에 전달받은 로고 파일을 public 경로에 두고 연결할 수 있습니다."
                />
                <div className="mt-2 flex items-center gap-3 rounded-dr border border-dashed border-gray-border bg-white/80 px-3 py-2">
                  <BuyerCompanyLogo
                    logoUrl={normalizeBuyerLogoUrl(form.logo_url)}
                    name={form.company_name || buyer.company_name}
                    size="md"
                  />
                  <div className="min-w-0">
                    <p className="text-xs font-medium text-text-dark">
                      회사명 왼쪽에 표시될 로고 미리보기입니다.
                    </p>
                    <p className="mt-1 text-xs text-text-secondary">
                      외부 URL이나 <code>/buyer-logos/...</code> 같은 정적 경로를
                      저장해 둘 수 있습니다.
                    </p>
                  </div>
                </div>
              </div>
              <Select
                label="Tier"
                options={[
                  { value: "", label: "-" },
                  ...BUYER_TIER_OPTIONS.filter((option) => option.value),
                ]}
                value={form.tier}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    tier: event.target.value as BuyerTier | "",
                  }))
                }
              />
              <Select
                label="역할"
                options={[
                  { value: "", label: "-" },
                  ...DEAL_ROLE_OPTIONS.filter((option) => option.value),
                ]}
                value={form.deal_role}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    deal_role: event.target.value as DealRole | "",
                  }))
                }
              />
              <Input
                label="담당자"
                value={form.contact_name}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    contact_name: event.target.value,
                  }))
                }
              />
              <Input
                label="이메일"
                type="email"
                value={form.contact_email}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    contact_email: event.target.value,
                  }))
                }
              />
              <Input
                label="전화"
                value={form.contact_phone}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    contact_phone: event.target.value,
                  }))
                }
              />
            </div>

            <div>
              <label className="mb-1.5 block text-sm font-medium text-text-body">
                비고
              </label>
              <textarea
                aria-label="비고"
                value={form.notes}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    notes: event.target.value,
                  }))
                }
                rows={4}
                className="w-full rounded-dr-sm border border-gray-border bg-white px-3 py-2 text-sm text-text-body shadow-sm transition-colors placeholder:text-text-secondary focus:border-amic focus:outline-none focus:ring-2 focus:ring-accent/30 hover:border-amic-400"
              />
            </div>
          </div>
        ) : (
          <dl className="grid grid-cols-2 gap-4">
            <InfoItem label="회사명">
              <div className="flex items-center gap-3">
                <BuyerCompanyLogo
                  logoUrl={currentLogoUrl}
                  name={buyer.company_name}
                  size="md"
                />
                <span>{buyer.company_name}</span>
              </div>
            </InfoItem>
            <InfoItem label="유형">{typeLabel}</InfoItem>
            <InfoItem label="Tier">
              <BuyerTierBadge tier={buyer.tier} />
            </InfoItem>
            <InfoItem label="역할">
              <DealRoleBadge role={buyer.deal_role} />
            </InfoItem>
            <InfoItem label="담당자">{buyer.contact_name ?? "-"}</InfoItem>
            <InfoItem label="이메일">{buyer.contact_email ?? "-"}</InfoItem>
            <InfoItem label="전화">{buyer.contact_phone ?? "-"}</InfoItem>
            <InfoItem label="상태">
              <Badge variant="neutral">{statusLabel}</Badge>
            </InfoItem>
            <InfoItem label="비고">
              <span className="text-text-secondary">{buyer.notes ?? "-"}</span>
            </InfoItem>
          </dl>
        )}
      </section>

      {stageSummary && (
        <section>
          <h3 className="mb-3 text-sm font-semibold text-text-dark">
            마케팅 진행 현황
          </h3>
          <MarketingStageTracker summary={stageSummary} />
        </section>
      )}

      {(buyer.ioi_value != null ||
        buyer.ioi_date != null ||
        buyer.loi_value != null ||
        buyer.loi_date != null) && (
        <section>
          <h3 className="mb-3 text-sm font-semibold text-text-dark">
            거래 정보
          </h3>
          <dl className="grid grid-cols-2 gap-4">
            <InfoItem label="IOI 금액">
              {buyer.ioi_value ? formatAmountKRW(Number(buyer.ioi_value)) : "-"}
            </InfoItem>
            <InfoItem label="IOI 일자">{buyer.ioi_date ?? "-"}</InfoItem>
            <InfoItem label="LOI 금액">
              {buyer.loi_value ? formatAmountKRW(Number(buyer.loi_value)) : "-"}
            </InfoItem>
            <InfoItem label="LOI 일자">{buyer.loi_date ?? "-"}</InfoItem>
            {buyer.final_offer_value && (
              <InfoItem label="최종 제안가">
                {formatAmountKRW(Number(buyer.final_offer_value))}
              </InfoItem>
            )}
          </dl>
        </section>
      )}

      {hasDart && (
        <section>
          <h3 className="mb-3 text-sm font-semibold text-text-dark">
            DART 재무 요약
          </h3>
          <div aria-live="polite">
            {dartLoading ? (
              <div className="flex items-center justify-center py-6">
                <Spinner size="sm" />
              </div>
            ) : dartError ? (
              <p className="text-xs text-red-500">
                재무 정보를 불러오지 못했습니다.
              </p>
            ) : dartSummary ? (
              <div>
                {dartSummary.fiscal_year && (
                  <p className="mb-2 text-xs text-text-muted">
                    기준: {dartSummary.fiscal_year}
                  </p>
                )}
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                  <FinancialMetric
                    label="매출"
                    value={dartSummary.revenue}
                    format="amount"
                  />
                  <FinancialMetric
                    label="영업이익"
                    value={dartSummary.operating_profit}
                    format="amount"
                  />
                  <FinancialMetric
                    label="순이익"
                    value={dartSummary.net_income}
                    format="amount"
                  />
                  <FinancialMetric
                    label="부채비율"
                    value={dartSummary.debt_ratio}
                    format="percent"
                  />
                </div>
              </div>
            ) : null}
          </div>
        </section>
      )}
    </div>
  );
}

function FinancialMetric({
  label,
  value,
  format,
}: {
  label: string;
  value: string | number | null;
  format: "amount" | "percent";
}) {
  const num =
    value == null ? null : typeof value === "string" ? parseFloat(value) : value;

  return (
    <div className="rounded-dr border border-gray-border p-3">
      <p className="text-xs text-text-muted">{label}</p>
      <p className="mt-1 text-sm font-semibold">
        {num == null || Number.isNaN(num)
          ? "-"
          : format === "percent"
            ? `${num.toLocaleString("ko-KR", {
                maximumFractionDigits: 1,
              })}%`
            : formatAmountKRW(num)}
      </p>
    </div>
  );
}

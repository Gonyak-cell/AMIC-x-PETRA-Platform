import { Badge, Spinner } from "@/components/ui";
import type { BuyerCandidate } from "@/modules/ma/types/buyer";
import type { BuyerStageSummary } from "@/modules/ma/types/marketing_log";
import {
  BUYER_TYPE_OPTIONS,
  BUYER_STATUS_OPTIONS,
} from "@/modules/ma/constants";
import BuyerTierBadge from "./BuyerTierBadge";
import DealRoleBadge from "./DealRoleBadge";
import MarketingStageTracker from "./MarketingStageTracker";
import { useDartFinancialSummary } from "@/modules/ma/hooks/useDartIntegration";

interface BuyerSummarySectionProps {
  buyer: BuyerCandidate;
  txnId: string;
  stageSummary: BuyerStageSummary | undefined;
}

function getOptionLabel(
  options: { value: string; label: string }[],
  value: string,
): string {
  const match = options.find((o) => o.value === value);
  return match?.label ?? value;
}

function formatAmountKRW(value: number): string {
  if (Math.abs(value) >= 1_0000_0000) {
    return `${(value / 1_0000_0000).toLocaleString("ko-KR", { maximumFractionDigits: 1 })}억 원`;
  }
  if (Math.abs(value) >= 1_0000) {
    return `${(value / 1_0000).toLocaleString("ko-KR", { maximumFractionDigits: 0 })}만 원`;
  }
  return `${value.toLocaleString("ko-KR")} 원`;
}

function InfoItem({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <dt className="text-xs text-text-muted">{label}</dt>
      <dd className="text-sm font-medium mt-0.5">{children}</dd>
    </div>
  );
}

export default function BuyerSummarySection({
  buyer,
  txnId,
  stageSummary,
}: BuyerSummarySectionProps) {
  const hasDart = !!buyer.corp_code;
  const { data: dartSummary, isLoading: dartLoading, isError: dartError } = useDartFinancialSummary(
    txnId,
    buyer.id,
    hasDart,
  );

  const statusLabel = getOptionLabel(BUYER_STATUS_OPTIONS, buyer.status);
  const typeLabel = getOptionLabel(BUYER_TYPE_OPTIONS, buyer.buyer_type);

  return (
    <div className="space-y-6">
      {/* 섹션 1: 기본 정보 */}
      <section>
        <h3 className="text-sm font-semibold text-text-dark mb-3">기본 정보</h3>
        <dl className="grid grid-cols-2 gap-4">
          <InfoItem label="회사명">{buyer.company_name}</InfoItem>
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
            <Badge variant="neutral">
              {statusLabel}
            </Badge>
          </InfoItem>
          <InfoItem label="비고">
            <span className="text-text-secondary">{buyer.notes ?? "-"}</span>
          </InfoItem>
        </dl>
      </section>

      {/* 섹션 2: 마케팅 진행 상태 */}
      {stageSummary && (
        <section>
          <h3 className="text-sm font-semibold text-text-dark mb-3">
            마케팅 진행 현황
          </h3>
          <MarketingStageTracker summary={stageSummary} />
        </section>
      )}

      {/* 섹션 3: 거래 정보 (IOI/LOI) */}
      {(buyer.ioi_value != null || buyer.ioi_date != null || buyer.loi_value != null || buyer.loi_date != null) && (
        <section>
          <h3 className="text-sm font-semibold text-text-dark mb-3">거래 정보</h3>
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
              <InfoItem label="최종 제안가">{formatAmountKRW(Number(buyer.final_offer_value))}</InfoItem>
            )}
          </dl>
        </section>
      )}

      {/* 섹션 4: DART 재무 요약 */}
      {hasDart && (
        <section>
          <h3 className="text-sm font-semibold text-text-dark mb-3">
            DART 재무 요약
          </h3>
          {dartLoading ? (
            <div className="flex items-center justify-center py-6">
              <Spinner size="sm" />
            </div>
          ) : dartError ? (
            <p className="text-xs text-red-500">재무 정보를 불러올 수 없습니다.</p>
          ) : dartSummary ? (
            <div>
              {dartSummary.fiscal_year && (
                <p className="text-xs text-text-muted mb-2">
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
  value: number | null;
  format: "amount" | "percent";
}) {
  return (
    <div className="rounded-dr border border-gray-border p-3">
      <p className="text-xs text-text-muted">{label}</p>
      <p className="text-sm font-semibold mt-1">
        {value == null
          ? "-"
          : format === "percent"
            ? `${value.toLocaleString("ko-KR", { maximumFractionDigits: 1 })}%`
            : formatAmountKRW(value)}
      </p>
    </div>
  );
}

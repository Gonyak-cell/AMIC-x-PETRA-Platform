import {
  CalendarDays,
  CircleCheckBig,
  Handshake,
  ScrollText,
  Users,
  Wallet,
} from "lucide-react";
import { Badge, Card, KpiCard } from "@/components/ui";
import {
  DEAL_STRUCTURE_OPTIONS,
  DEAL_TYPE_LABELS,
  TRANSACTION_STATUS_OPTIONS,
} from "@/modules/ma/constants";
import type { Transaction } from "@/modules/ma/types/transaction";
import type { WorkspaceSummary } from "@/modules/ma/types/workspace";
import { formatAmountCompact, formatDate } from "@/lib/format";

interface TransactionCompletionOverviewProps {
  txn: Transaction;
  summary?: WorkspaceSummary;
}

function findOptionLabel(
  options: Array<{ value: string; label: string }>,
  value: string | null | undefined,
) {
  if (!value) return "-";
  return options.find((option) => option.value === value)?.label ?? value;
}

function SummaryRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-start justify-between gap-4 py-2.5">
      <dt className="text-sm text-text-muted">{label}</dt>
      <dd className="text-sm font-medium text-text-dark text-right">{value}</dd>
    </div>
  );
}

export default function TransactionCompletionOverview({
  txn,
  summary,
}: TransactionCompletionOverviewProps) {
  const estimatedDealValue = txn.estimated_deal_value
    ? `${formatAmountCompact(txn.estimated_deal_value, txn.currency)} ${txn.currency}`
    : "-";
  const statusLabel = findOptionLabel(TRANSACTION_STATUS_OPTIONS, txn.status);
  const dealStructureLabel = findOptionLabel(
    DEAL_STRUCTURE_OPTIONS,
    txn.deal_structure,
  );

  return (
    <div className="space-y-6">
      <Card
        padding="lg"
        className="border-accent/20 bg-[linear-gradient(135deg,rgba(34,197,94,0.08),rgba(255,255,255,0.96)_52%,rgba(240,253,244,0.94))]"
      >
        <div className="space-y-4">
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="success" pill>
              거래종결
            </Badge>
            <span className="text-sm text-text-secondary">
              클로징까지 정말 고생 많으셨습니다.
            </span>
          </div>
          <div className="space-y-2">
            <h2 className="text-2xl font-heading font-semibold text-text-dark">
              {txn.name} 거래가 성공적으로 마무리되었습니다.
            </h2>
            <p className="text-sm text-text-secondary">
              {txn.code_name} | {txn.target_company_name} | {txn.client_name}
            </p>
          </div>
        </div>
      </Card>

      <div className="grid grid-cols-2 gap-4 xl:grid-cols-6">
        <KpiCard
          label="현재 단계"
          value="거래종결"
          icon={CircleCheckBig}
          variant="positive"
        />
        <KpiCard
          label="예상 거래금액"
          value={estimatedDealValue}
          icon={Wallet}
        />
        <KpiCard
          label="매수자"
          value={String(summary?.buyer_count ?? 0)}
          icon={Users}
        />
        <KpiCard label="입찰" value={String(summary?.bid_count ?? 0)} icon={Handshake} />
        <KpiCard
          label="계약서"
          value={String(summary?.contract_count ?? 0)}
          icon={ScrollText}
        />
        <KpiCard
          label="Closing 항목"
          value={String(summary?.closing_item_count ?? 0)}
          icon={CalendarDays}
        />
      </div>

      <Card title="거래 전반 요약" headerBar>
        <div className="grid grid-cols-1 gap-x-8 md:grid-cols-2">
          <dl className="divide-y divide-gray-100">
            <SummaryRow label="거래명" value={txn.name} />
            <SummaryRow label="코드네임" value={txn.code_name} />
            <SummaryRow label="대상기업" value={txn.target_company_name} />
            <SummaryRow label="클라이언트" value={txn.client_name} />
            <SummaryRow
              label="딜 유형"
              value={DEAL_TYPE_LABELS[txn.deal_type] ?? txn.deal_type}
            />
          </dl>
          <dl className="divide-y divide-gray-100">
            <SummaryRow label="현재 상태" value={statusLabel} />
            <SummaryRow label="세부 거래 구조" value={dealStructureLabel} />
            <SummaryRow label="목표 종결일" value={formatDate(txn.target_close_date)} />
            <SummaryRow
              label="리드 어드바이저"
              value={txn.lead_advisor_email || "-"}
            />
            <SummaryRow
              label="딜 캡틴"
              value={txn.deal_captain_email || "-"}
            />
          </dl>
        </div>
      </Card>

      <Card title="프로세스 요약" headerBar>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          <KpiCard label="NDA" value={String(summary?.nda_count ?? 0)} />
          <KpiCard label="DD 항목" value={String(summary?.dd_item_count ?? 0)} />
          <KpiCard
            label="타임라인 이벤트"
            value={String(summary?.timeline_count ?? 0)}
            icon={CalendarDays}
          />
        </div>
      </Card>
    </div>
  );
}

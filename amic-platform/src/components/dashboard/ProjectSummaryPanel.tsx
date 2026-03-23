/** MY PROJECTS — 프로젝트 요약 패널 (외부 컨테이너 안에서 사용) */

import { Badge } from "@/components/ui";
import { PHASE_CONFIG } from "@/modules/ma/constants";
import { DEAL_TYPE_LABELS } from "@/modules/ma/constants/transaction";
import { TRANSACTION_STATUS_VARIANT } from "@/modules/ma/constants/status-variants";
import { TRANSACTION_STATUS_OPTIONS } from "@/modules/ma/constants/transaction";
import { formatDate } from "@/lib/format";
import type { Transaction } from "@/modules/ma/types/transaction";
import type { UserRole } from "@/types/auth";

const PHASE_LABEL: Record<string, string> = {};
for (const p of PHASE_CONFIG) {
  PHASE_LABEL[p.phase] = p.label;
}

const STATUS_LABEL: Record<string, string> = {};
for (const o of TRANSACTION_STATUS_OPTIONS) {
  if (o.value) STATUS_LABEL[o.value] = o.label;
}

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60_000);
  if (mins < 1) return "방금 전";
  if (mins < 60) return `${mins}분 전`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}시간 전`;
  const days = Math.floor(hrs / 24);
  return `${days}일 전`;
}

function getMyRole(
  txn: Transaction,
  email: string,
  userRole: UserRole | null,
): string {
  if (userRole === "CLIENT") return "Client";

  const isLead = txn.lead_advisor_email === email;
  const isCaptain = txn.deal_captain_email === email;
  if (isLead && isCaptain) return "Lead Advisor / Deal Captain";
  if (isLead) return "Lead Advisor";
  return "Deal Captain";
}

interface ProjectSummaryPanelProps {
  transaction: Transaction;
  userEmail: string;
  userRole: UserRole | null;
}

function Row({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex justify-between items-center py-2">
      <dt className="text-xs text-text-secondary">{label}</dt>
      <dd className="text-sm font-medium text-text-dark text-right">
        {children}
      </dd>
    </div>
  );
}

export default function ProjectSummaryPanel({
  transaction: txn,
  userEmail,
  userRole,
}: ProjectSummaryPanelProps) {
  const statusLabel = STATUS_LABEL[txn.status] ?? txn.status;
  const statusVariant = TRANSACTION_STATUS_VARIANT[txn.status] ?? "neutral";

  return (
    <div className="p-5">
      <dl className="divide-y divide-gray-100">
        <Row label="Deal Type">
          {DEAL_TYPE_LABELS[txn.deal_type] ?? txn.deal_type}
        </Row>
        <Row label="Phase">{PHASE_LABEL[txn.phase] ?? txn.phase}</Row>
        <Row label="Status">
          <Badge variant={statusVariant} className="text-[10px]">
            {statusLabel}
          </Badge>
        </Row>
        <Row label="Target Close">{formatDate(txn.target_close_date)}</Row>
        <Row label="My Role">{getMyRole(txn, userEmail, userRole)}</Row>
        <Row label="Last Updated">{timeAgo(txn.updated_at)}</Row>
      </dl>
    </div>
  );
}

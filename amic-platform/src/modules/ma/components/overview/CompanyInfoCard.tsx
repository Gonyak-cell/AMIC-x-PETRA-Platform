import { Card } from "@/components/ui/Card";
import type { Transaction } from "@/modules/ma/types/transaction";
import type {
  CorporateDocsExtractedData,
  CorporateDirector,
} from "@/modules/ma/types/document_extraction";
import { sortDirectorsByPosition } from "@/modules/ma/types/document_extraction";

interface Props {
  txn: Transaction;
}

// ── 유틸 ──────────────────────────────────────────────────

function formatKRW(amount: number): string {
  if (amount >= 1_0000_0000) {
    const eok = amount / 1_0000_0000;
    return `${eok.toLocaleString(undefined, { maximumFractionDigits: 1 })}억 원`;
  }
  if (amount >= 1_0000) {
    const man = amount / 1_0000;
    return `${man.toLocaleString(undefined, { maximumFractionDigits: 1 })}만 원`;
  }
  return `${amount.toLocaleString()}원`;
}

// ── 섹션별 서브 컴포넌트 ──────────────────────────────────

function FieldRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <>
      <dt className="text-text-muted text-sm">{label}</dt>
      <dd className="text-sm">{value ?? "-"}</dd>
    </>
  );
}

function BasicInfoSection({ ci }: { ci: CorporateDocsExtractedData }) {
  return (
    <dl className="grid grid-cols-[140px_1fr] gap-x-4 gap-y-2.5">
      <FieldRow label="상호" value={ci.company_name} />
      <FieldRow label="대표이사" value={ci.representative_name} />
      <FieldRow label="설립일" value={ci.establishment_date} />
      <FieldRow
        label="사업자등록번호"
        value={ci.business_registration_number && (
          <span className="font-mono text-xs">{ci.business_registration_number}</span>
        )}
      />
      <FieldRow
        label="법인등록번호"
        value={ci.corporate_registration_number && (
          <span className="font-mono text-xs">{ci.corporate_registration_number}</span>
        )}
      />
      <FieldRow label="본점 소재지" value={ci.head_office_address} />
      <FieldRow label="업태" value={ci.business_type} />
      <FieldRow label="종목" value={ci.business_item} />
    </dl>
  );
}

function CapitalSection({ ci }: { ci: CorporateDocsExtractedData }) {
  return (
    <div className="border-t border-gray-border pt-4">
      <h4 className="text-xs font-semibold text-text-secondary uppercase mb-3">
        자본 및 주식
      </h4>
      <dl className="grid grid-cols-[140px_1fr] gap-x-4 gap-y-2.5">
        <FieldRow
          label="자본금"
          value={ci.capital_amount != null && (
            <span className="font-mono">{formatKRW(ci.capital_amount)}</span>
          )}
        />
        <FieldRow
          label="발행주식총수"
          value={ci.total_shares_issued != null && (
            <span className="font-mono">{ci.total_shares_issued.toLocaleString()}주</span>
          )}
        />
        <FieldRow
          label="1주 금액"
          value={ci.par_value_per_share != null && (
            <span className="font-mono">{ci.par_value_per_share.toLocaleString()}원</span>
          )}
        />
        <FieldRow
          label="보통주"
          value={ci.common_shares != null && (
            <span className="font-mono">{ci.common_shares.toLocaleString()}주</span>
          )}
        />
        <FieldRow
          label="종류주"
          value={ci.preferred_shares != null && (
            <span className="font-mono">{ci.preferred_shares.toLocaleString()}주</span>
          )}
        />
      </dl>
    </div>
  );
}

function DirectorBadge({ position }: { position: string }) {
  return (
    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-amic-50 text-amic-600 shrink-0">
      {position}
    </span>
  );
}

function DirectorsSection({ directors }: { directors: CorporateDirector[] }) {
  const sorted = sortDirectorsByPosition(directors);
  if (sorted.length === 0) return null;

  return (
    <div className="border-t border-gray-border pt-4">
      <h4 className="text-xs font-semibold text-text-secondary uppercase mb-3">
        임원 정보
      </h4>
      <div className="space-y-1.5">
        {sorted.map((d, i) => (
          <div key={i} className="flex items-baseline gap-2 text-sm">
            <DirectorBadge position={d.position} />
            <span className="font-medium">{d.name}</span>
            {d.birth_date && (
              <span className="text-text-muted text-xs">{d.birth_date}</span>
            )}
            {d.appointment_date && (
              <span className="text-text-muted text-xs">취임 {d.appointment_date}</span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function PurposeSection({ purpose }: { purpose: string }) {
  return (
    <div className="border-t border-gray-border pt-4">
      <h4 className="text-xs font-semibold text-text-secondary uppercase mb-3">
        목적사항
      </h4>
      <p className="text-sm text-text-secondary whitespace-pre-line leading-relaxed">
        {purpose}
      </p>
    </div>
  );
}

// ── 메인 컴포넌트 ─────────────────────────────────────────

export default function CompanyInfoCard({ txn }: Props) {
  const ci = txn.corporate_info as unknown as CorporateDocsExtractedData | null;
  if (!ci) return null;

  return (
    <Card title="회사 정보" headerBar variant="accent-left">
      <div className="space-y-4 p-1">
        <BasicInfoSection ci={ci} />
        <CapitalSection ci={ci} />
        <DirectorsSection directors={ci.directors ?? []} />
        {ci.corporate_purpose && <PurposeSection purpose={ci.corporate_purpose} />}
      </div>
    </Card>
  );
}

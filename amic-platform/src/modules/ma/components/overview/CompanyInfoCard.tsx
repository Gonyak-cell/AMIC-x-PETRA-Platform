import { useState } from "react";
import { UploadCloud, CheckCircle2 } from "lucide-react";
import { Card } from "@/components/ui/Card";
import type { Transaction } from "@/modules/ma/types/transaction";
import type {
  CorporateDocsExtractedData,
  CorporateDirector,
} from "@/modules/ma/types/document_extraction";
import { sortDirectorsByPosition } from "@/modules/ma/types/document_extraction";
import EngagementDocUpload from "./EngagementDocUpload";

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

// ── 공통 컴포넌트 ──────────────────────────────────────────

function FieldRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <>
      <dt className="text-text-muted text-sm">{label}</dt>
      <dd className="text-sm">{value ?? "-"}</dd>
    </>
  );
}

// ── 섹션 헤더 ──────────────────────────────────────────────

interface SectionHeaderProps {
  title: string;
  isComplete: boolean;
  docName: string;
  uploadOpen: boolean;
  onUploadToggle: () => void;
}

function SectionHeader({
  title,
  isComplete,
  docName,
  uploadOpen,
  onUploadToggle,
}: SectionHeaderProps) {
  return (
    <div className="flex items-center justify-between mb-3">
      <h4 className="text-xs font-semibold text-text-secondary uppercase">
        {title}
      </h4>
      {isComplete ? (
        <span className="flex items-center gap-1 text-xs text-emerald-600 font-medium">
          <CheckCircle2 className="h-3.5 w-3.5" />
          업로드 완료
        </span>
      ) : (
        <button
          type="button"
          onClick={onUploadToggle}
          className="flex items-center gap-1 text-xs text-text-tertiary hover:text-text-secondary transition-colors"
        >
          <UploadCloud className="h-3 w-3" />
          {uploadOpen ? "닫기" : `${docName}를 업로드하세요`}
        </button>
      )}
    </div>
  );
}

// ── 법인등기부 섹션 ────────────────────────────────────────

function RegistryBasicInfoSection({ ci }: { ci: CorporateDocsExtractedData }) {
  return (
    <dl className="grid grid-cols-[140px_1fr] gap-x-4 gap-y-2.5">
      <FieldRow label="상호" value={ci.company_name} />
      <FieldRow label="대표이사" value={ci.representative_name} />
      <FieldRow label="설립일" value={ci.establishment_date} />
      <FieldRow
        label="법인등록번호"
        value={
          ci.corporate_registration_number && (
            <span className="font-mono text-xs">
              {ci.corporate_registration_number}
            </span>
          )
        }
      />
      <FieldRow label="본점 소재지" value={ci.head_office_address} />
      <FieldRow label="사업 목적" value={ci.business_item} />
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
          value={
            ci.capital_amount != null && (
              <span className="font-mono">{formatKRW(ci.capital_amount)}</span>
            )
          }
        />
        <FieldRow
          label="발행주식총수"
          value={
            ci.total_shares_issued != null && (
              <span className="font-mono">
                {ci.total_shares_issued.toLocaleString()}주
              </span>
            )
          }
        />
        <FieldRow
          label="1주 금액"
          value={
            ci.par_value_per_share != null && (
              <span className="font-mono">
                {ci.par_value_per_share.toLocaleString()}원
              </span>
            )
          }
        />
        <FieldRow
          label="보통주"
          value={
            ci.common_shares != null && (
              <span className="font-mono">
                {ci.common_shares.toLocaleString()}주
              </span>
            )
          }
        />
        <FieldRow
          label="종류주"
          value={
            ci.preferred_shares != null && (
              <span className="font-mono">
                {ci.preferred_shares.toLocaleString()}주
              </span>
            )
          }
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
              <span className="text-text-muted text-xs">
                취임 {d.appointment_date}
              </span>
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

// ── 사업자등록증 섹션 ──────────────────────────────────────

function BizRegInfoSection({ ci }: { ci: CorporateDocsExtractedData }) {
  return (
    <dl className="grid grid-cols-[140px_1fr] gap-x-4 gap-y-2.5">
      <FieldRow
        label="사업자등록번호"
        value={
          ci.business_registration_number && (
            <span className="font-mono text-xs">
              {ci.business_registration_number}
            </span>
          )
        }
      />
      <FieldRow label="업태" value={ci.business_type} />
      <FieldRow label="종목" value={ci.business_item} />
    </dl>
  );
}

// ── 카드 헤더 배지 ─────────────────────────────────────────

function BothCompleteActions() {
  return (
    <span className="flex items-center gap-1 text-xs text-emerald-600 font-medium">
      <CheckCircle2 className="h-3.5 w-3.5" />
      법인등기부/사업자등록증 업로드 완료
    </span>
  );
}

// ── 메인 컴포넌트 ─────────────────────────────────────────

export default function CompanyInfoCard({ txn }: Props) {
  const ci = txn.corporate_info as unknown as CorporateDocsExtractedData | null;
  const [showRegistryUpload, setShowRegistryUpload] = useState(false);
  const [showBizRegUpload, setShowBizRegUpload] = useState(false);

  const hasRegistry = !!(ci?.corporate_registration_number || ci?.company_name);
  const hasBizReg = !!(ci?.business_registration_number || ci?.business_type);
  const bothComplete = hasRegistry && hasBizReg;

  return (
    <Card
      title="회사 정보"
      headerBar
      variant="accent-left"
      actions={bothComplete ? <BothCompleteActions /> : undefined}
    >
      <div className="space-y-4 p-1">
        {/* ── 법인등기부 섹션 ── */}
        <div>
          <SectionHeader
            title="법인등기부"
            isComplete={hasRegistry}
            docName="법인등기부"
            uploadOpen={showRegistryUpload}
            onUploadToggle={() => setShowRegistryUpload((v) => !v)}
          />
          {hasRegistry && ci ? (
            <div className="space-y-4">
              <RegistryBasicInfoSection ci={ci} />
              <CapitalSection ci={ci} />
              <DirectorsSection directors={ci.directors ?? []} />
              {ci.corporate_purpose && (
                <PurposeSection purpose={ci.corporate_purpose} />
              )}
            </div>
          ) : (
            showRegistryUpload && (
              <div className="mt-3">
                <EngagementDocUpload
                  txnId={txn.id}
                  docCategoryHint="CORPORATE_DOCS"
                />
              </div>
            )
          )}
        </div>

        {/* ── 구분선 ── */}
        <hr className="border-gray-border" />

        {/* ── 사업자등록증 섹션 ── */}
        <div>
          <SectionHeader
            title="사업자등록증"
            isComplete={hasBizReg}
            docName="사업자등록증"
            uploadOpen={showBizRegUpload}
            onUploadToggle={() => setShowBizRegUpload((v) => !v)}
          />
          {hasBizReg && ci ? (
            <div className="mt-3">
              <BizRegInfoSection ci={ci} />
            </div>
          ) : (
            showBizRegUpload && (
              <div className="mt-3">
                <EngagementDocUpload
                  txnId={txn.id}
                  docCategoryHint="CORPORATE_DOCS"
                />
              </div>
            )
          )}
        </div>
      </div>
    </Card>
  );
}

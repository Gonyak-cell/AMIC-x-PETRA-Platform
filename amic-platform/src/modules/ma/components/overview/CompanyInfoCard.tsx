import { useState, Fragment } from "react";
import { UploadCloud, CheckCircle2 } from "lucide-react";
import { Card } from "@/components/ui/Card";
import VdrUploadShortcutCard from "@/modules/ma/components/vdr/VdrUploadShortcutCard";
import { useOpenVdrUpload } from "@/modules/ma/hooks/useVdrUploadNavigation";
import type { Transaction } from "@/modules/ma/types/transaction";
import type {
  CorporateDocsExtractedData,
  CorporateDirector,
} from "@/modules/ma/types/document_extraction";
import { sortDirectorsByPosition } from "@/modules/ma/types/document_extraction";

interface Props {
  txn: Transaction;
  canWrite?: boolean;
}

// ── 유틸 ──────────────────────────────────────────────────

/** 하위 호환: 기존 string 데이터도 배열로 변환 */
function normalizePurposes(value: unknown): string[] {
  if (Array.isArray(value)) return value;
  if (typeof value === "string")
    return value
      .split(/\n/)
      .map((s) => s.trim())
      .filter(Boolean);
  return [];
}

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
      <dt className="text-text-secondary text-sm">{label}</dt>
      <dd className="text-sm font-medium text-text-body">{value ?? "-"}</dd>
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
  canWrite?: boolean;
}

function SectionHeader({
  title,
  isComplete,
  docName,
  uploadOpen,
  onUploadToggle,
  canWrite = true,
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
      ) : canWrite ? (
        <button
          type="button"
          onClick={onUploadToggle}
          className="flex items-center gap-1 text-xs text-text-tertiary hover:text-text-secondary transition-colors"
        >
          <UploadCloud className="h-3 w-3" />
          {uploadOpen ? "닫기" : `${docName}를 업로드하세요`}
        </button>
      ) : null}
    </div>
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
    </dl>
  );
}

function CapitalSection({ ci }: { ci: CorporateDocsExtractedData }) {
  return (
    <div className="border-t border-gray-border pt-4 md:border-t-0 md:pt-2">
      <h4 className="text-xs font-semibold text-text-secondary uppercase mb-3">
        자본 및 주식
      </h4>
      <dl className="grid grid-cols-[140px_1fr] gap-x-4 gap-y-2.5 [&>dd]:text-right">
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
  if (sorted.length === 0) return <div />;

  return (
    <div className="border-t border-gray-border pt-4 md:border-t-0 md:pt-0 md:pb-2">
      <h4 className="text-xs font-semibold text-text-secondary uppercase mb-3">
        임원 정보
      </h4>
      <div className="grid grid-cols-[auto_1fr_auto_auto] gap-x-4 gap-y-2 items-center">
        <span className="text-[11px] text-text-muted">직책</span>
        <span className="text-[11px] text-text-muted">성명</span>
        <span className="text-[11px] text-text-muted">생년월일</span>
        <span className="text-[11px] text-text-muted">취임일</span>
        {sorted.map((d, i) => (
          <Fragment key={i}>
            <DirectorBadge position={d.position} />
            <span className="text-sm font-medium text-text-body">{d.name}</span>
            <span className="text-xs text-text-secondary font-mono">
              {d.birth_date ?? "-"}
            </span>
            <span className="text-xs text-text-secondary font-mono">
              {d.appointment_date ?? "-"}
            </span>
          </Fragment>
        ))}
      </div>
    </div>
  );
}

function BusinessPurposeSection({ purposes }: { purposes: string[] }) {
  const [expanded, setExpanded] = useState(false);
  const VISIBLE_COUNT = 10;
  const hasMore = purposes.length > VISIBLE_COUNT;
  const visibleItems = expanded ? purposes : purposes.slice(0, VISIBLE_COUNT);

  const half = Math.ceil(visibleItems.length / 2);
  const leftCol = visibleItems.slice(0, half);
  const rightCol = visibleItems.slice(half);

  return (
    <div className="border-t border-gray-border pt-4 md:border-t-0 md:pt-2">
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-xs font-semibold text-text-secondary uppercase">
          사업목적
          <span className="ml-1 text-text-muted font-normal">
            ({purposes.length}건)
          </span>
        </h4>
        {hasMore && (
          <button
            type="button"
            onClick={() => setExpanded((v) => !v)}
            className="text-xs text-accent hover:text-accent/80 transition-colors"
          >
            {expanded ? "접기" : `+${purposes.length - VISIBLE_COUNT}건 더보기`}
          </button>
        )}
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6">
        <ul className="space-y-1">
          {leftCol.map((item, i) => (
            <li
              key={i}
              className="text-xs text-text-secondary leading-relaxed break-words"
              title={item}
            >
              · {item}
            </li>
          ))}
        </ul>
        <ul className="space-y-1">
          {rightCol.map((item, i) => (
            <li
              key={i}
              className="text-xs text-text-secondary leading-relaxed break-words"
              title={item}
            >
              · {item}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

// ── 사업자등록증 섹션 ──────────────────────────────────────

function BizRegInfoSection({ ci }: { ci: CorporateDocsExtractedData }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-4">
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
      </dl>
      <dl className="grid grid-cols-[140px_1fr] gap-x-4 gap-y-2.5">
        <FieldRow label="업태" value={ci.business_type} />
        <FieldRow label="종목" value={ci.business_item} />
      </dl>
    </div>
  );
}

// ── 메인 컴포넌트 ─────────────────────────────────────────

function MissingDocumentState({
  docName,
  canWrite = true,
}: {
  docName: string;
  canWrite?: boolean;
}) {
  return (
    <div className="mt-3 rounded-lg border border-slate-200 bg-slate-50 px-4 py-3">
      <p className="text-sm font-medium text-slate-800">{docName} 문서가 아직 없습니다.</p>
      <p className="mt-1 text-xs text-slate-600">
        {canWrite
          ? "VDR에 업로드하면 이 카드가 자동으로 업데이트됩니다."
          : "업로드가 완료되면 이 카드가 자동으로 업데이트됩니다."}
      </p>
    </div>
  );
}

export default function CompanyInfoCard({ txn, canWrite = true }: Props) {
  const ci = txn.corporate_info as unknown as CorporateDocsExtractedData | null;
  const openVdrUpload = useOpenVdrUpload(txn.id);

  const hasRegistry = !!(ci?.corporate_registration_number || ci?.company_name);
  const hasBizReg = !!ci?.business_registration_number;
  const bothComplete = hasRegistry && hasBizReg;
  const missingDocNames = [
    !hasRegistry ? "법인등기부" : null,
    !hasBizReg ? "사업자등록증" : null,
  ].filter((value): value is string => value !== null);

  return (
    <Card
      title="회사 정보"
      headerBar
      variant="accent-left"
      actions={bothComplete ? <BothCompleteActions /> : undefined}
    >
      <div className="space-y-4 p-1">
        {!bothComplete && canWrite && (
          <VdrUploadShortcutCard
            title="필요 문서를 VDR에서 업로드하세요"
            description={`${missingDocNames.join(", ")}을(를) 업로드하면 회사 정보가 자동으로 채워집니다.`}
            onOpen={() => openVdrUpload({ returnLabel: "Overview" })}
          />
        )}
        {/* ── 법인등기부 섹션 ── */}
        <div>
          <SectionHeader
            title="법인등기부"
            isComplete={hasRegistry}
            docName="법인등기부"
            uploadOpen={false}
            onUploadToggle={() => {}}
            canWrite={false}
          />
          {hasRegistry && ci ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-4 md:gap-y-0">
              {/* 좌측: subgrid로 행 정렬 */}
              <div className="space-y-4 md:space-y-0 md:row-span-3 md:grid md:grid-rows-[subgrid]">
                <RegistryBasicInfoSection ci={ci} />
                <div className="hidden md:block border-t border-gray-border my-4" />
                <CapitalSection ci={ci} />
              </div>
              {/* 우측: subgrid로 행 정렬 */}
              <div className="space-y-4 md:space-y-0 md:row-span-3 md:grid md:grid-rows-[subgrid]">
                <DirectorsSection directors={ci.directors ?? []} />
                <div className="hidden md:block border-t border-gray-border my-4" />
                {ci.corporate_purpose ? (
                  <BusinessPurposeSection
                    purposes={normalizePurposes(ci.corporate_purpose)}
                  />
                ) : (
                  <div />
                )}
              </div>
            </div>
          ) : (
            <MissingDocumentState docName="법인등기부" canWrite={canWrite} />
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
            uploadOpen={false}
            onUploadToggle={() => {}}
            canWrite={false}
          />
          {hasBizReg && ci ? (
            <div className="mt-3">
              <BizRegInfoSection ci={ci} />
            </div>
          ) : (
            <MissingDocumentState docName="사업자등록증" canWrite={canWrite} />
          )}
        </div>
      </div>
    </Card>
  );
}

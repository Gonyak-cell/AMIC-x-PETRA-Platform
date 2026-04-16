import { Fragment, useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import {
  ArrowRight,
  CheckCircle2,
  FileSearch,
  Loader2,
  PencilLine,
  UploadCloud,
} from "lucide-react";

import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { PHASE_TAB_MAP } from "@/modules/ma/constants";
import { useExtractions } from "@/modules/ma/hooks/useDocumentExtraction";
import { useUpdateTransaction } from "@/modules/ma/hooks/useTransactions";
import { useOpenVdrUpload } from "@/modules/ma/hooks/useVdrUploadNavigation";
import type {
  CorporateInfoUpdate,
  Transaction,
  TransactionPhase,
} from "@/modules/ma/types/transaction";
import type {
  CorporateDocsExtractedData,
  CorporateDirector,
  DocExtractionCategory,
  DocumentExtraction,
} from "@/modules/ma/types/document_extraction";
import {
  hasMeaningfulExtractionData,
  IN_PROGRESS_STATUSES,
  sortDirectorsByPosition,
} from "@/modules/ma/types/document_extraction";

interface Props {
  txn: Transaction;
  canWrite?: boolean;
}

interface ManualCompanyInfoForm {
  representative_name: string;
  business_registration_number: string;
  corporate_registration_number: string;
  head_office_address: string;
  business_type: string;
  business_item: string;
}

type SectionStatusKind =
  | "missing"
  | "processing"
  | "review"
  | "confirmed"
  | "manual";

interface SectionStatus {
  kind: SectionStatusKind;
  label: string;
  description: string;
}

const REGISTRY_CATEGORIES: DocExtractionCategory[] = [
  "REGISTRY_DOCS",
  "CORPORATE_DOCS",
];
const BIZ_REG_CATEGORIES: DocExtractionCategory[] = [
  "BIZ_REG_DOCS",
  "CORPORATE_DOCS",
];

function trimToNull(value: unknown): string | null {
  if (typeof value !== "string") {
    return null;
  }
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : null;
}

function normalizePurposes(value: unknown): string[] {
  if (Array.isArray(value)) {
    return value.filter((item): item is string => typeof item === "string");
  }
  if (typeof value === "string") {
    return value
      .split(/\n/)
      .map((item) => item.trim())
      .filter(Boolean);
  }
  return [];
}

function formatKRW(amount: number): string {
  if (amount >= 1_0000_0000) {
    const eok = amount / 1_0000_0000;
    return `${eok.toLocaleString(undefined, { maximumFractionDigits: 1 })}억원`;
  }
  if (amount >= 1_0000) {
    const man = amount / 1_0000;
    return `${man.toLocaleString(undefined, { maximumFractionDigits: 1 })}만원`;
  }
  return `${amount.toLocaleString()}원`;
}

function buildManualForm(
  ci: CorporateDocsExtractedData | null | undefined,
): ManualCompanyInfoForm {
  return {
    representative_name: ci?.representative_name ?? "",
    business_registration_number: ci?.business_registration_number ?? "",
    corporate_registration_number: ci?.corporate_registration_number ?? "",
    head_office_address: ci?.head_office_address ?? "",
    business_type: ci?.business_type ?? "",
    business_item: ci?.business_item ?? "",
  };
}

function pickLatestExtraction(
  extractions: DocumentExtraction[],
  categories: DocExtractionCategory[],
) {
  return extractions
    .filter(
      (extraction): extraction is DocumentExtraction & {
        doc_category: DocExtractionCategory;
      } =>
        extraction.doc_category !== null &&
        categories.includes(extraction.doc_category),
    )
    .sort((left, right) => right.created_at.localeCompare(left.created_at))[0];
}

function hasRegistryData(ci: CorporateDocsExtractedData | null | undefined) {
  return Boolean(
    trimToNull(ci?.company_name) ||
      trimToNull(ci?.representative_name) ||
      trimToNull(ci?.corporate_registration_number) ||
      trimToNull(ci?.head_office_address) ||
      (ci?.capital_amount ?? null) !== null ||
      (ci?.total_shares_issued ?? null) !== null ||
      (ci?.par_value_per_share ?? null) !== null ||
      (ci?.common_shares ?? null) !== null ||
      (ci?.preferred_shares ?? null) !== null ||
      (ci?.directors?.length ?? 0) > 0 ||
      normalizePurposes(ci?.corporate_purpose).length > 0,
  );
}

function hasBizRegData(ci: CorporateDocsExtractedData | null | undefined) {
  return Boolean(
    trimToNull(ci?.business_registration_number) ||
      trimToNull(ci?.business_type) ||
      trimToNull(ci?.business_item),
  );
}

function getSectionStatus({
  extraction,
  manualComplete,
  hasVisibleData,
}: {
  extraction?: DocumentExtraction;
  manualComplete: boolean;
  hasVisibleData: boolean;
}): SectionStatus {
  if (extraction) {
    if (IN_PROGRESS_STATUSES.includes(extraction.status)) {
      return {
        kind: "processing",
        label: "처리중",
        description: "OCR 추출을 진행하고 있습니다.",
      };
    }
    if (extraction.status === "COMPLETED") {
      return {
        kind: "review",
        label: "검토 필요",
        description: hasMeaningfulExtractionData(extraction.extracted_data)
          ? "OCR 결과를 검토하고 확정해주세요."
          : "OCR 결과가 비어 있어 직접 입력으로 보완이 필요합니다.",
      };
    }
    if (extraction.status === "CONFIRMED") {
      return {
        kind: "confirmed",
        label: "확정 완료",
        description: hasVisibleData
          ? "확정된 값이 회사 정보에 반영되었습니다."
          : "확정은 완료되었고, 비어 있는 항목은 직접 입력으로 보완할 수 있습니다.",
      };
    }
    if (extraction.status === "FAILED") {
      return {
        kind: "review",
        label: "재확인 필요",
        description:
          "OCR 처리에 실패했습니다. 문서를 다시 업로드하거나 직접 입력할 수 있습니다.",
      };
    }
  }

  if (manualComplete) {
    return {
      kind: "manual",
      label: "직접 입력 완료",
      description: "수동 입력 값이 저장되었습니다.",
    };
  }

  return {
    kind: "missing",
    label: "미업로드",
    description: "아직 문서를 업로드하지 않았습니다. 업로드하거나 직접 입력할 수 있습니다.",
  };
}

function getStatusClasses(kind: SectionStatusKind) {
  switch (kind) {
    case "processing":
      return "bg-sky-50 text-sky-700 border-sky-200";
    case "review":
      return "bg-amber-50 text-amber-700 border-amber-200";
    case "confirmed":
      return "bg-emerald-50 text-emerald-700 border-emerald-200";
    case "manual":
      return "bg-violet-50 text-violet-700 border-violet-200";
    default:
      return "bg-slate-50 text-slate-600 border-slate-200";
  }
}

function FieldRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <>
      <dt className="text-sm text-text-secondary">{label}</dt>
      <dd className="text-sm font-medium text-text-body">{value ?? "-"}</dd>
    </>
  );
}

function StatusBadge({ status }: { status: SectionStatus }) {
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-medium ${getStatusClasses(
        status.kind,
      )}`}
    >
      {status.label}
    </span>
  );
}

function SectionHeader({
  title,
  status,
  uploadLabel,
  canWrite,
  onUpload,
}: {
  title: string;
  status: SectionStatus;
  uploadLabel: string;
  canWrite: boolean;
  onUpload: () => void;
}) {
  return (
    <div className="mb-3 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
      <div className="space-y-1">
        <div className="flex items-center gap-2">
          <h4 className="text-xs font-semibold uppercase text-text-secondary">
            {title}
          </h4>
          <StatusBadge status={status} />
        </div>
        <p className="text-xs text-text-muted">{status.description}</p>
      </div>
      {canWrite ? (
        <button
          type="button"
          onClick={onUpload}
          className="inline-flex items-center gap-1 text-xs font-medium text-accent transition-colors hover:text-accent/80"
        >
          <UploadCloud className="h-3.5 w-3.5" />
          {uploadLabel}
        </button>
      ) : null}
    </div>
  );
}

function RegistryBasicInfoSection({ ci }: { ci: CorporateDocsExtractedData }) {
  return (
    <dl className="grid grid-cols-[140px_1fr] gap-x-4 gap-y-2.5">
      <FieldRow label="상호" value={ci.company_name} />
      <FieldRow label="대표이사" value={ci.representative_name} />
      <FieldRow label="설립일" value={ci.establishment_date} />
      <FieldRow
        label="법인등록번호"
        value={
          ci.corporate_registration_number ? (
            <span className="font-mono text-xs">
              {ci.corporate_registration_number}
            </span>
          ) : null
        }
      />
      <FieldRow label="본점 소재지" value={ci.head_office_address} />
    </dl>
  );
}

function CapitalSection({ ci }: { ci: CorporateDocsExtractedData }) {
  return (
    <div className="border-t border-gray-border pt-4 md:border-t-0 md:pt-2">
      <h4 className="mb-3 text-xs font-semibold uppercase text-text-secondary">
        자본 및 주식
      </h4>
      <dl className="grid grid-cols-[140px_1fr] gap-x-4 gap-y-2.5 [&>dd]:text-right">
        <FieldRow
          label="자본금"
          value={
            ci.capital_amount != null ? (
              <span className="font-mono">{formatKRW(ci.capital_amount)}</span>
            ) : null
          }
        />
        <FieldRow
          label="발행주식총수"
          value={
            ci.total_shares_issued != null ? (
              <span className="font-mono">
                {ci.total_shares_issued.toLocaleString()}주
              </span>
            ) : null
          }
        />
        <FieldRow
          label="1주 금액"
          value={
            ci.par_value_per_share != null ? (
              <span className="font-mono">
                {ci.par_value_per_share.toLocaleString()}원
              </span>
            ) : null
          }
        />
        <FieldRow
          label="보통주"
          value={
            ci.common_shares != null ? (
              <span className="font-mono">
                {ci.common_shares.toLocaleString()}주
              </span>
            ) : null
          }
        />
        <FieldRow
          label="종류주"
          value={
            ci.preferred_shares != null ? (
              <span className="font-mono">
                {ci.preferred_shares.toLocaleString()}주
              </span>
            ) : null
          }
        />
      </dl>
    </div>
  );
}

function DirectorBadge({ position }: { position: string }) {
  return (
    <span className="inline-flex shrink-0 items-center rounded bg-amic-50 px-2 py-0.5 text-xs font-medium text-amic-600">
      {position}
    </span>
  );
}

function DirectorsSection({ directors }: { directors: CorporateDirector[] }) {
  const sorted = sortDirectorsByPosition(directors);
  if (sorted.length === 0) {
    return <div />;
  }

  return (
    <div className="border-t border-gray-border pt-4 md:border-t-0 md:pt-0 md:pb-2">
      <h4 className="mb-3 text-xs font-semibold uppercase text-text-secondary">
        임원 정보
      </h4>
      <div className="grid grid-cols-[auto_1fr_auto_auto] items-center gap-x-4 gap-y-2">
        <span className="text-[11px] text-text-muted">직위</span>
        <span className="text-[11px] text-text-muted">성명</span>
        <span className="text-[11px] text-text-muted">생년월일</span>
        <span className="text-[11px] text-text-muted">취임일</span>
        {sorted.map((director, index) => (
          <Fragment key={`${director.name}-${index}`}>
            <DirectorBadge position={director.position} />
            <span className="text-sm font-medium text-text-body">
              {director.name}
            </span>
            <span className="font-mono text-xs text-text-secondary">
              {director.birth_date ?? "-"}
            </span>
            <span className="font-mono text-xs text-text-secondary">
              {director.appointment_date ?? "-"}
            </span>
          </Fragment>
        ))}
      </div>
    </div>
  );
}

function BusinessPurposeSection({ purposes }: { purposes: string[] }) {
  const [expanded, setExpanded] = useState(false);
  const visibleCount = 10;
  const hasMore = purposes.length > visibleCount;
  const visibleItems = expanded ? purposes : purposes.slice(0, visibleCount);
  const half = Math.ceil(visibleItems.length / 2);
  const leftColumn = visibleItems.slice(0, half);
  const rightColumn = visibleItems.slice(half);

  return (
    <div className="border-t border-gray-border pt-4 md:border-t-0 md:pt-2">
      <div className="mb-3 flex items-center justify-between">
        <h4 className="text-xs font-semibold uppercase text-text-secondary">
          사업목적
          <span className="ml-1 font-normal text-text-muted">
            ({purposes.length}건)
          </span>
        </h4>
        {hasMore ? (
          <button
            type="button"
            onClick={() => setExpanded((current) => !current)}
            className="text-xs text-accent transition-colors hover:text-accent/80"
          >
            {expanded ? "접기" : `+${purposes.length - visibleCount}건 더보기`}
          </button>
        ) : null}
      </div>
      <div className="grid grid-cols-1 gap-x-6 md:grid-cols-2">
        {[leftColumn, rightColumn].map((items, columnIndex) => (
          <ul key={columnIndex} className="space-y-1">
            {items.map((item, itemIndex) => (
              <li
                key={`${item}-${itemIndex}`}
                className="break-words text-xs leading-relaxed text-text-secondary"
                title={item}
              >
                - {item}
              </li>
            ))}
          </ul>
        ))}
      </div>
    </div>
  );
}

function BizRegInfoSection({ ci }: { ci: CorporateDocsExtractedData }) {
  return (
    <div className="grid grid-cols-1 gap-x-8 gap-y-4 md:grid-cols-2">
      <dl className="grid grid-cols-[140px_1fr] gap-x-4 gap-y-2.5">
        <FieldRow
          label="사업자등록번호"
          value={
            ci.business_registration_number ? (
              <span className="font-mono text-xs">
                {ci.business_registration_number}
              </span>
            ) : null
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

function SectionStateCard({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return (
    <div className="mt-3 rounded-lg border border-slate-200 bg-slate-50 px-4 py-3">
      <p className="text-sm font-medium text-slate-800">{title}</p>
      <p className="mt-1 text-xs text-slate-600">{description}</p>
    </div>
  );
}

export default function CompanyInfoCard({ txn, canWrite = true }: Props) {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const setupMode = searchParams.get("setup") === "company-info";
  const openVdrUpload = useOpenVdrUpload(txn.id);
  const updateTxn = useUpdateTransaction(txn.id);
  const extractionQuery = useExtractions(txn.id);

  const sourceCorporateInfo =
    (txn.corporate_info as CorporateDocsExtractedData | null) ?? null;
  const [localCorporateInfo, setLocalCorporateInfo] = useState<
    CorporateDocsExtractedData | null
  >(sourceCorporateInfo);
  const effectiveCorporateInfo = localCorporateInfo ?? sourceCorporateInfo;

  const [showManualForm, setShowManualForm] = useState(setupMode && canWrite);
  const [manualForm, setManualForm] = useState<ManualCompanyInfoForm>(() =>
    buildManualForm(sourceCorporateInfo),
  );

  useEffect(() => {
    setLocalCorporateInfo(sourceCorporateInfo);
  }, [sourceCorporateInfo, txn.updated_at]);

  useEffect(() => {
    setManualForm(buildManualForm(effectiveCorporateInfo));
  }, [effectiveCorporateInfo]);

  useEffect(() => {
    if (setupMode && canWrite) {
      setShowManualForm(true);
    }
  }, [canWrite, setupMode]);

  const extractions = extractionQuery.data?.items ?? [];
  const latestRegistryExtraction = useMemo(
    () => pickLatestExtraction(extractions, REGISTRY_CATEGORIES),
    [extractions],
  );
  const latestBizExtraction = useMemo(
    () => pickLatestExtraction(extractions, BIZ_REG_CATEGORIES),
    [extractions],
  );

  const registryStatus = getSectionStatus({
    extraction: latestRegistryExtraction,
    manualComplete: Boolean(
      trimToNull(effectiveCorporateInfo?.representative_name) &&
        trimToNull(effectiveCorporateInfo?.corporate_registration_number),
    ),
    hasVisibleData: hasRegistryData(effectiveCorporateInfo),
  });
  const bizStatus = getSectionStatus({
    extraction: latestBizExtraction,
    manualComplete: Boolean(
      trimToNull(effectiveCorporateInfo?.business_registration_number),
    ),
    hasVisibleData: hasBizRegData(effectiveCorporateInfo),
  });

  const companyName =
    trimToNull(effectiveCorporateInfo?.company_name) ??
    trimToNull(txn.target_company_name);
  const requiredInfoComplete = Boolean(
    companyName &&
      trimToNull(effectiveCorporateInfo?.representative_name) &&
      trimToNull(effectiveCorporateInfo?.business_registration_number) &&
      trimToNull(effectiveCorporateInfo?.corporate_registration_number),
  );

  const managedCorporateInfo = useMemo<CorporateInfoUpdate>(
    () => ({
      company_name:
        trimToNull(effectiveCorporateInfo?.company_name) ??
        trimToNull(txn.target_company_name),
      representative_name: trimToNull(manualForm.representative_name),
      business_registration_number: trimToNull(
        manualForm.business_registration_number,
      ),
      corporate_registration_number: trimToNull(
        manualForm.corporate_registration_number,
      ),
      head_office_address: trimToNull(manualForm.head_office_address),
      business_type: trimToNull(manualForm.business_type),
      business_item: trimToNull(manualForm.business_item),
    }),
    [effectiveCorporateInfo?.company_name, manualForm, txn.target_company_name],
  );

  const currentManagedInfo = useMemo<CorporateInfoUpdate>(
    () => ({
      company_name:
        trimToNull(effectiveCorporateInfo?.company_name) ??
        trimToNull(txn.target_company_name),
      representative_name: trimToNull(effectiveCorporateInfo?.representative_name),
      business_registration_number: trimToNull(
        effectiveCorporateInfo?.business_registration_number,
      ),
      corporate_registration_number: trimToNull(
        effectiveCorporateInfo?.corporate_registration_number,
      ),
      head_office_address: trimToNull(effectiveCorporateInfo?.head_office_address),
      business_type: trimToNull(effectiveCorporateInfo?.business_type),
      business_item: trimToNull(effectiveCorporateInfo?.business_item),
    }),
    [effectiveCorporateInfo, txn.target_company_name],
  );

  const hasManualChanges =
    JSON.stringify(currentManagedInfo) !== JSON.stringify(managedCorporateInfo);

  const handleManualFieldChange =
    (key: keyof ManualCompanyInfoForm) =>
    (event: React.ChangeEvent<HTMLInputElement>) => {
      const nextValue = event.target.value;
      setManualForm((current) => ({ ...current, [key]: nextValue }));
    };

  const handleManualSave = () => {
    updateTxn.mutate(
      { corporate_info: managedCorporateInfo },
      {
        onSuccess: (nextTxn) => {
          setLocalCorporateInfo(
            (nextTxn.corporate_info as CorporateDocsExtractedData | null) ?? null,
          );
        },
      },
    );
  };

  const handleNextStep = () => {
    const nextParams = new URLSearchParams(searchParams);
    nextParams.delete("setup");
    const nextSearch = nextParams.toString();
    const defaultTab =
      PHASE_TAB_MAP[txn.phase as TransactionPhase] ?? "overview";
    const nextPath =
      defaultTab === "overview"
        ? `/ma/transactions/${txn.id}`
        : `/ma/transactions/${txn.id}/${defaultTab}`;
    navigate(`${nextPath}${nextSearch ? `?${nextSearch}` : ""}`, {
      replace: true,
    });
  };

  const hasRegistryVisibleData = hasRegistryData(effectiveCorporateInfo);
  const hasBizVisibleData = hasBizRegData(effectiveCorporateInfo);
  const setupStatusLabel = requiredInfoComplete
    ? "회사 정보 설정 완료"
    : "회사 정보 설정 필요";

  return (
    <Card
      title="회사 정보"
      headerBar
      variant="accent-left"
      actions={
        <span
          className={`inline-flex items-center gap-1 text-xs font-medium ${
            requiredInfoComplete ? "text-emerald-600" : "text-amber-600"
          }`}
        >
          <CheckCircle2 className="h-3.5 w-3.5" />
          {setupStatusLabel}
        </span>
      }
    >
      <div className="space-y-5 p-1">
        {canWrite ? (
          <div
            className={`rounded-xl border px-4 py-4 ${
              setupMode
                ? "border-amber-200 bg-amber-50/70"
                : "border-slate-200 bg-slate-50"
            }`}
          >
            <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
              <div className="space-y-1">
                <h3 className="text-sm font-semibold text-text-body">
                  {setupMode
                    ? "프로젝트 시작 전 회사 정보를 먼저 준비해주세요"
                    : "문서 업로드 또는 직접 입력으로 회사 정보를 보완할 수 있습니다"}
                </h3>
                <p className="text-sm text-text-secondary">
                  사업자등록증과 법인등기부를 올리면 OCR로 값을 채워주고, 문서가 없어도
                  핵심 항목을 직접 입력해 다음 단계로 이동할 수 있습니다.
                </p>
              </div>
              {setupMode ? (
                <div className="inline-flex items-center gap-2 rounded-full bg-white px-3 py-1 text-xs font-medium text-amber-700">
                  <FileSearch className="h-3.5 w-3.5" />
                  초기 설정 단계
                </div>
              ) : null}
            </div>

            <div className="mt-4 grid gap-2 md:grid-cols-3">
              <button
                type="button"
                onClick={() =>
                  openVdrUpload({
                    returnLabel: "회사 정보",
                    docHint: "REGISTRY_DOCS",
                  })
                }
                className="flex items-center justify-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm font-medium text-text-body transition-colors hover:border-accent/40 hover:text-accent"
              >
                <UploadCloud className="h-4 w-4" />
                법인등기부 업로드
              </button>
              <button
                type="button"
                onClick={() =>
                  openVdrUpload({
                    returnLabel: "회사 정보",
                    docHint: "BIZ_REG_DOCS",
                  })
                }
                className="flex items-center justify-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm font-medium text-text-body transition-colors hover:border-accent/40 hover:text-accent"
              >
                <UploadCloud className="h-4 w-4" />
                사업자등록증 업로드
              </button>
              <button
                type="button"
                onClick={() => setShowManualForm((current) => !current)}
                className="flex items-center justify-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm font-medium text-text-body transition-colors hover:border-accent/40 hover:text-accent"
              >
                <PencilLine className="h-4 w-4" />
                직접 입력
              </button>
            </div>
          </div>
        ) : null}

        {showManualForm && canWrite ? (
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <div className="mb-4 flex items-center justify-between gap-3">
              <div>
                <h3 className="text-sm font-semibold text-text-body">
                  직접 입력
                </h3>
                <p className="mt-1 text-xs text-text-muted">
                  필수값은 대표이사, 사업자등록번호, 법인등록번호입니다. 회사명은
                  현재 대상기업명을 기본값으로 사용합니다.
                </p>
              </div>
              {!setupMode ? (
                <button
                  type="button"
                  onClick={() => setShowManualForm(false)}
                  className="text-xs font-medium text-text-muted transition-colors hover:text-text-body"
                >
                  닫기
                </button>
              ) : null}
            </div>

            <div className="grid gap-4 lg:grid-cols-2">
              <div className="space-y-4">
                <div className="grid gap-1.5">
                  <label
                    htmlFor="company-info-representative"
                    className="text-sm font-medium text-text-body"
                  >
                    대표이사
                  </label>
                  <input
                    id="company-info-representative"
                    type="text"
                    value={manualForm.representative_name}
                    onChange={handleManualFieldChange("representative_name")}
                    className="rounded-md border border-gray-border px-3 py-2 text-sm outline-none transition focus:border-accent focus:ring-2 focus:ring-accent/10"
                  />
                </div>
                <div className="grid gap-1.5">
                  <label
                    htmlFor="company-info-biz-reg-number"
                    className="text-sm font-medium text-text-body"
                  >
                    사업자등록번호
                  </label>
                  <input
                    id="company-info-biz-reg-number"
                    type="text"
                    value={manualForm.business_registration_number}
                    onChange={handleManualFieldChange(
                      "business_registration_number",
                    )}
                    className="rounded-md border border-gray-border px-3 py-2 font-mono text-sm outline-none transition focus:border-accent focus:ring-2 focus:ring-accent/10"
                  />
                </div>
                <div className="grid gap-1.5">
                  <label
                    htmlFor="company-info-corp-reg-number"
                    className="text-sm font-medium text-text-body"
                  >
                    법인등록번호
                  </label>
                  <input
                    id="company-info-corp-reg-number"
                    type="text"
                    value={manualForm.corporate_registration_number}
                    onChange={handleManualFieldChange(
                      "corporate_registration_number",
                    )}
                    className="rounded-md border border-gray-border px-3 py-2 font-mono text-sm outline-none transition focus:border-accent focus:ring-2 focus:ring-accent/10"
                  />
                </div>
              </div>

              <div className="space-y-4">
                <div className="grid gap-1.5">
                  <label
                    htmlFor="company-info-address"
                    className="text-sm font-medium text-text-body"
                  >
                    본점 소재지
                  </label>
                  <input
                    id="company-info-address"
                    type="text"
                    value={manualForm.head_office_address}
                    onChange={handleManualFieldChange("head_office_address")}
                    className="rounded-md border border-gray-border px-3 py-2 text-sm outline-none transition focus:border-accent focus:ring-2 focus:ring-accent/10"
                  />
                </div>
                <div className="grid gap-1.5">
                  <label
                    htmlFor="company-info-business-type"
                    className="text-sm font-medium text-text-body"
                  >
                    업태
                  </label>
                  <input
                    id="company-info-business-type"
                    type="text"
                    value={manualForm.business_type}
                    onChange={handleManualFieldChange("business_type")}
                    className="rounded-md border border-gray-border px-3 py-2 text-sm outline-none transition focus:border-accent focus:ring-2 focus:ring-accent/10"
                  />
                </div>
                <div className="grid gap-1.5">
                  <label
                    htmlFor="company-info-business-item"
                    className="text-sm font-medium text-text-body"
                  >
                    종목
                  </label>
                  <input
                    id="company-info-business-item"
                    type="text"
                    value={manualForm.business_item}
                    onChange={handleManualFieldChange("business_item")}
                    className="rounded-md border border-gray-border px-3 py-2 text-sm outline-none transition focus:border-accent focus:ring-2 focus:ring-accent/10"
                  />
                </div>
              </div>
            </div>

            <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 pt-4">
              <p className="text-xs text-text-muted">
                {requiredInfoComplete
                  ? "필수 회사 정보가 준비되었습니다."
                  : "필수값을 저장하면 다음 단계 버튼이 활성화됩니다."}
              </p>
              <Button
                type="button"
                variant="secondary"
                onClick={handleManualSave}
                disabled={!hasManualChanges || updateTxn.isPending}
              >
                {updateTxn.isPending ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    저장중...
                  </>
                ) : (
                  "회사 정보 저장"
                )}
              </Button>
            </div>
          </div>
        ) : null}

        <div>
          <SectionHeader
            title="법인등기부"
            status={registryStatus}
            uploadLabel="법인등기부 업로드"
            canWrite={canWrite}
            onUpload={() =>
              openVdrUpload({
                returnLabel: "회사 정보",
                docHint: "REGISTRY_DOCS",
              })
            }
          />
          {hasRegistryVisibleData && effectiveCorporateInfo ? (
            <div className="grid grid-cols-1 gap-x-8 gap-y-4 md:grid-cols-2 md:gap-y-0">
              <div className="space-y-4 md:row-span-3 md:grid md:grid-rows-[subgrid] md:space-y-0">
                <RegistryBasicInfoSection ci={effectiveCorporateInfo} />
                <div className="my-4 hidden border-t border-gray-border md:block" />
                <CapitalSection ci={effectiveCorporateInfo} />
              </div>
              <div className="space-y-4 md:row-span-3 md:grid md:grid-rows-[subgrid] md:space-y-0">
                <DirectorsSection
                  directors={effectiveCorporateInfo.directors ?? []}
                />
                <div className="my-4 hidden border-t border-gray-border md:block" />
                {normalizePurposes(effectiveCorporateInfo.corporate_purpose)
                  .length > 0 ? (
                  <BusinessPurposeSection
                    purposes={normalizePurposes(
                      effectiveCorporateInfo.corporate_purpose,
                    )}
                  />
                ) : (
                  <div />
                )}
              </div>
            </div>
          ) : (
            <SectionStateCard
              title="법인등기부 정보가 아직 카드에 반영되지 않았습니다."
              description={registryStatus.description}
            />
          )}
        </div>

        <hr className="border-gray-border" />

        <div>
          <SectionHeader
            title="사업자등록증"
            status={bizStatus}
            uploadLabel="사업자등록증 업로드"
            canWrite={canWrite}
            onUpload={() =>
              openVdrUpload({
                returnLabel: "회사 정보",
                docHint: "BIZ_REG_DOCS",
              })
            }
          />
          {hasBizVisibleData && effectiveCorporateInfo ? (
            <div className="mt-3">
              <BizRegInfoSection ci={effectiveCorporateInfo} />
            </div>
          ) : (
            <SectionStateCard
              title="사업자등록증 정보가 아직 카드에 반영되지 않았습니다."
              description={bizStatus.description}
            />
          )}
        </div>

        {setupMode ? (
          <div className="flex flex-col gap-3 rounded-xl border border-slate-200 bg-slate-50 px-4 py-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="space-y-1">
              <p className="text-sm font-semibold text-text-body">
                회사 정보 준비를 마치면 다음 단계로 이동합니다
              </p>
              <p className="text-xs text-text-muted">
                필수값: 대표이사, 사업자등록번호, 법인등록번호
              </p>
            </div>
            <Button
              type="button"
              onClick={handleNextStep}
              disabled={!requiredInfoComplete}
            >
              다음 단계
              <ArrowRight className="h-4 w-4" />
            </Button>
          </div>
        ) : null}
      </div>
    </Card>
  );
}

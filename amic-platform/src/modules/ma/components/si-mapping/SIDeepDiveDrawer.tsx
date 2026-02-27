import { useEffect, useRef } from "react";

import { cn } from "@/lib/cn";
import { useSIDeepDive } from "@/modules/ma/hooks/useSIMapping";
import type {
  FinancialSummary,
  SanctionItem,
} from "@/modules/ma/types/si_mapping";
import { formatDate, formatKRW } from "@/modules/ma/utils/format";

interface SIDeepDiveDrawerProps {
  companyId: string | null;
  onClose: () => void;
}

export default function SIDeepDiveDrawer({
  companyId,
  onClose,
}: SIDeepDiveDrawerProps) {
  const { data, isLoading, isError } = useSIDeepDive(companyId);
  const drawerRef = useRef<HTMLDivElement>(null);

  // ESC 키로 닫기
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    if (companyId) document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [companyId, onClose]);

  if (!companyId) return null;

  return (
    <>
      {/* 오버레이 */}
      <div className="fixed inset-0 z-[60] bg-black/20" onClick={onClose} />

      {/* 드로어 패널 */}
      <div
        ref={drawerRef}
        className={cn(
          "fixed right-0 top-0 z-[61] flex h-full w-full max-w-lg flex-col",
          "bg-white shadow-2xl transition-transform duration-300",
          companyId ? "translate-x-0" : "translate-x-full",
        )}
      >
        {/* 헤더 */}
        <div className="flex items-center justify-between border-b border-slate-200 px-5 py-4">
          <div className="min-w-0 flex-1">
            <h3 className="truncate text-base font-bold text-slate-800">
              {data?.company.company_name ?? "로딩 중..."}
            </h3>
            {data?.dart_available && data.overview && (
              <p className="mt-0.5 text-xs text-slate-500">
                DART {data.overview.corp_code}
              </p>
            )}
          </div>
          <button
            type="button"
            onClick={onClose}
            className="ml-3 rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
          >
            <svg
              className="h-5 w-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        {/* 본문 */}
        <div className="flex-1 overflow-y-auto px-5 py-4 space-y-5">
          {isLoading && (
            <div className="flex items-center justify-center py-12">
              <div className="h-6 w-6 animate-spin rounded-full border-2 border-emerald-500 border-t-transparent" />
              <span className="ml-2 text-sm text-slate-500">
                DART 데이터 조회 중...
              </span>
            </div>
          )}

          {isError && (
            <div className="rounded-lg bg-red-50 p-4 text-sm text-red-600">
              딥다이브 데이터를 불러오는 데 실패했습니다.
            </div>
          )}

          {data && (
            <>
              {/* 기업 기본 정보 */}
              <Section title="기업 정보">
                <InfoGrid>
                  <InfoItem
                    label="KSIC"
                    value={data.company.ksic_codes?.join(", ") ?? "-"}
                  />
                  <InfoItem
                    label="매출액"
                    value={formatKRW(data.company.revenue)}
                  />
                  <InfoItem
                    label="투자이력"
                    value={
                      data.company.has_investment_history ? "있음" : "없음"
                    }
                  />
                </InfoGrid>
              </Section>

              {/* DART 기업개황 */}
              {data.dart_available && data.overview ? (
                <>
                  <Section title="DART 기업개황">
                    <InfoGrid>
                      <InfoItem label="대표자" value={data.overview.ceo_nm} />
                      <InfoItem
                        label="설립일"
                        value={formatDate(data.overview.est_dt)}
                      />
                      <InfoItem
                        label="업종코드"
                        value={data.overview.induty_code}
                      />
                      <InfoItem label="주소" value={data.overview.adres} wide />
                      {data.overview.hm_url && (
                        <InfoItem label="홈페이지">
                          <a
                            href={
                              data.overview.hm_url.startsWith("http")
                                ? data.overview.hm_url
                                : `https://${data.overview.hm_url}`
                            }
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-emerald-600 hover:underline"
                          >
                            {data.overview.hm_url}
                          </a>
                        </InfoItem>
                      )}
                    </InfoGrid>
                  </Section>

                  {/* 재무 요약 */}
                  {data.financials.length > 0 && (
                    <Section title="재무 요약 (연결)">
                      <FinancialTable financials={data.financials} />
                    </Section>
                  )}

                  {/* M&A 관련 공시 */}
                  {data.disclosures.length > 0 && (
                    <Section title="M&A 관련 공시">
                      <ul className="space-y-2">
                        {data.disclosures.map((d) => (
                          <li
                            key={d.rcept_no}
                            className="flex items-start gap-2 text-sm"
                          >
                            <span className="flex-shrink-0 text-slate-400">
                              {formatDate(d.rcept_dt)}
                            </span>
                            <a
                              href={`https://dart.fss.or.kr/dsaf001/main.do?rcpNo=${d.rcept_no}`}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-slate-700 hover:text-emerald-600 hover:underline"
                            >
                              {d.report_nm}
                            </a>
                          </li>
                        ))}
                      </ul>
                    </Section>
                  )}

                  {/* 제재 내역 */}
                  {data.sanctions.length > 0 && (
                    <Section title="제재 내역">
                      <SanctionsTable sanctions={data.sanctions} />
                    </Section>
                  )}
                </>
              ) : (
                !isLoading && (
                  <div className="rounded-lg border border-slate-200 bg-slate-50 p-4 text-center text-sm text-slate-500">
                    DART 데이터를 조회할 수 없습니다.
                    <br />
                    <span className="text-xs text-slate-400">
                      KIIS DART API 연결을 확인하세요.
                    </span>
                  </div>
                )
              )}
            </>
          )}
        </div>
      </div>
    </>
  );
}

// ── 내부 UI 컴포넌트 ──────────────────────────────────────

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <h4 className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-500">
        {title}
      </h4>
      {children}
    </div>
  );
}

function InfoGrid({ children }: { children: React.ReactNode }) {
  return (
    <div className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">{children}</div>
  );
}

function InfoItem({
  label,
  value,
  wide,
  children,
}: {
  label: string;
  value?: string;
  wide?: boolean;
  children?: React.ReactNode;
}) {
  return (
    <div className={wide ? "col-span-2" : ""}>
      <span className="text-xs text-slate-400">{label}</span>
      <div className="text-slate-700">{children ?? (value || "-")}</div>
    </div>
  );
}

function SanctionsTable({ sanctions }: { sanctions: SanctionItem[] }) {
  return (
    <div className="overflow-x-auto rounded-lg border border-red-200">
      <table className="w-full text-left text-sm">
        <thead className="border-b border-red-200 bg-red-50">
          <tr>
            <th className="px-3 py-2 font-medium text-red-700">일자</th>
            <th className="px-3 py-2 font-medium text-red-700">유형</th>
            <th className="px-3 py-2 font-medium text-red-700">내용</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-red-100">
          {sanctions.map((s, i) => (
            <tr key={`${s.date}-${i}`} className="hover:bg-red-50/50">
              <td className="whitespace-nowrap px-3 py-2 text-slate-600">
                {formatDate(s.date)}
              </td>
              <td className="px-3 py-2 text-slate-700">{s.type || "-"}</td>
              <td className="px-3 py-2 text-slate-700">{s.content || "-"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function FinancialTable({ financials }: { financials: FinancialSummary[] }) {
  return (
    <div className="overflow-x-auto rounded-lg border border-slate-200">
      <table className="w-full text-right text-sm">
        <thead className="border-b border-slate-200 bg-slate-50">
          <tr>
            <th className="px-3 py-2 text-left font-medium text-slate-600">
              연도
            </th>
            <th className="px-3 py-2 font-medium text-slate-600">매출액</th>
            <th className="px-3 py-2 font-medium text-slate-600">영업이익</th>
            <th className="px-3 py-2 font-medium text-slate-600">순이익</th>
            <th className="px-3 py-2 font-medium text-slate-600">총자산</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {financials.map((f) => (
            <tr key={f.bsns_year} className="hover:bg-slate-50">
              <td className="px-3 py-2 text-left font-medium text-slate-800">
                {f.bsns_year}
              </td>
              <td className="px-3 py-2 tabular-nums">{formatKRW(f.revenue)}</td>
              <td className="px-3 py-2 tabular-nums">
                {formatKRW(f.operating_income)}
              </td>
              <td className="px-3 py-2 tabular-nums">
                {formatKRW(f.net_income)}
              </td>
              <td className="px-3 py-2 tabular-nums">
                {formatKRW(f.total_assets)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

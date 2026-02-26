import { useState } from "react";
import {
  useCompanyFinancials,
  useFinancialSummary,
} from "@/modules/kiis/hooks/useCompanies";
import {
  Card,
  DataTable,
  Select,
  Spinner,
  EmptyState,
  Badge,
  KpiCard,
} from "@/components/ui";
import type { Column } from "@/components/ui";
import { FinancialBarChart } from "@/components/charts";
import type { FinancialStatement } from "@/modules/kiis/types/company";
import { formatAmount } from "@/lib/format";
import { BarChart3 } from "lucide-react";

const currentYear = new Date().getFullYear();
const YEAR_OPTIONS = Array.from({ length: 4 }, (_, i) => {
  const y = String(currentYear - i);
  return { value: y, label: y };
});

const REPORT_OPTIONS = [
  { value: "11011", label: "Annual Report" },
  { value: "11012", label: "Semi-Annual" },
  { value: "11013", label: "Q1 Report" },
  { value: "11014", label: "Q3 Report" },
];

function parseAmount(s: string): number | null {
  const n = Number(s);
  return isNaN(n) ? null : n;
}

function formatKpiAmount(value: string | null | undefined): string {
  if (!value) return "-";
  const n = Number(value);
  if (isNaN(n)) return "-";
  // 억 단위 표시
  const eok = n / 100_000_000;
  if (Math.abs(eok) >= 1) {
    return `${eok.toLocaleString("ko-KR", { maximumFractionDigits: 0 })}억`;
  }
  return formatAmount(n, "KRW");
}

const SOURCE_LABEL: Record<string, string> = {
  DART: "DART",
  DATA_GO_KR: "공공데이터",
  NONE: "-",
};

interface CompanyFinancialsProps {
  corpCode: string;
}

export default function CompanyFinancials({
  corpCode,
}: CompanyFinancialsProps) {
  const [year, setYear] = useState(String(currentYear));
  const [reportCode, setReportCode] = useState("11011");

  const { data: financialData, isLoading, isError } = useCompanyFinancials(
    corpCode,
    { bsns_year: year, reprt_code: reportCode },
  );

  const { data: summary } = useFinancialSummary(corpCode, year);

  const financials = financialData?.items;
  const source = financialData?.source ?? summary?.source ?? "NONE";

  const columns: Column<FinancialStatement>[] = [
    {
      key: "account_nm",
      header: "Account",
      render: (row) => (
        <span className="font-medium text-text-dark">{row.account_nm}</span>
      ),
    },
    {
      key: "thstrm_amount",
      header: "Current",
      align: "right",
      mono: true,
      render: (row) => formatAmount(parseAmount(row.thstrm_amount), "KRW"),
    },
    {
      key: "frmtrm_amount",
      header: "Previous",
      align: "right",
      mono: true,
      render: (row) => formatAmount(parseAmount(row.frmtrm_amount), "KRW"),
    },
    {
      key: "bfefrmtrm_amount",
      header: "2 Years Ago",
      align: "right",
      mono: true,
      render: (row) => formatAmount(parseAmount(row.bfefrmtrm_amount), "KRW"),
    },
  ];

  const chartData = (financials ?? []).slice(0, 8).map((f) => ({
    name: f.account_nm,
    value: parseAmount(f.thstrm_amount) ?? 0,
    displayValue: formatAmount(parseAmount(f.thstrm_amount), "KRW"),
  }));

  const hasSummary =
    summary && summary.source !== "NONE" && (summary.sale_amt || summary.tast_amt);

  return (
    <Card
      title="Financial Statements"
      headerBar
      actions={
        source !== "NONE" ? (
          <Badge variant={source === "DART" ? "info" : "warning"}>
            {SOURCE_LABEL[source] ?? source}
          </Badge>
        ) : undefined
      }
    >
      {/* 요약 KPI 그리드 */}
      {hasSummary && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-5">
          <KpiCard label="매출" value={formatKpiAmount(summary.sale_amt)} />
          <KpiCard label="영업이익" value={formatKpiAmount(summary.bzop_pft)} />
          <KpiCard label="순이익" value={formatKpiAmount(summary.crtm_npf)} />
          <KpiCard label="총자산" value={formatKpiAmount(summary.tast_amt)} />
          <KpiCard label="총부채" value={formatKpiAmount(summary.tdbt_amt)} />
          <KpiCard label="총자본" value={formatKpiAmount(summary.tcpt_amt)} />
          <KpiCard
            label="부채비율"
            value={
              summary.debt_rto
                ? `${Number(summary.debt_rto).toFixed(1)}%`
                : "-"
            }
          />
        </div>
      )}

      {/* 연도/보고서 선택기 */}
      <div className="flex gap-3 mb-4">
        <Select
          label="Year"
          options={YEAR_OPTIONS}
          value={year}
          onChange={(e) => setYear(e.target.value)}
        />
        <Select
          label="Report"
          options={REPORT_OPTIONS}
          value={reportCode}
          onChange={(e) => setReportCode(e.target.value)}
        />
      </div>

      {/* 상세 재무제표 */}
      {isLoading ? (
        <Spinner />
      ) : isError ? (
        <EmptyState
          icon={BarChart3}
          title="Failed to load financials"
          description="An error occurred while fetching financial data. Please try again."
        />
      ) : !financials || financials.length === 0 ? (
        <EmptyState
          icon={BarChart3}
          title="No financial data"
          description="Financial statements are not available for the selected period."
        />
      ) : (
        <>
          <div className="mb-4">
            <FinancialBarChart data={chartData} height={260} />
          </div>
          <DataTable
            columns={columns}
            data={financials}
            keyField="account_nm"
            compact
            striped
          />
        </>
      )}
    </Card>
  );
}

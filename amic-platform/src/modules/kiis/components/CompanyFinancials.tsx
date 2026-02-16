import { useState } from "react";
import { useCompanyFinancials } from "@/modules/kiis/hooks/useCompanies";
import { Card, DataTable, Select, Spinner, EmptyState } from "@/components/ui";
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

interface CompanyFinancialsProps {
  corpCode: string;
}

export default function CompanyFinancials({
  corpCode,
}: CompanyFinancialsProps) {
  const [year, setYear] = useState(String(currentYear));
  const [reportCode, setReportCode] = useState("11011");

  const { data: financials, isLoading, isError } = useCompanyFinancials(corpCode, {
    bsns_year: year,
    reprt_code: reportCode,
  });

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

  return (
    <Card title="Financial Statements" headerBar>
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

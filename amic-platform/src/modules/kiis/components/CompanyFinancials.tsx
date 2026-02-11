import { useState } from "react";
import { useCompanyFinancials } from "@/modules/kiis/hooks/useCompanies";
import { Card, DataTable, Select, Spinner, EmptyState } from "@/components/ui";
import type { Column } from "@/components/ui";
import { FinancialBarChart } from "@/components/charts";
import type { FinancialStatement } from "@/modules/kiis/types/company";
import { formatAmount } from "@/lib/format";
import { BarChart3 } from "lucide-react";

const YEAR_OPTIONS = [
  { value: "2024", label: "2024" },
  { value: "2023", label: "2023" },
  { value: "2022", label: "2022" },
  { value: "2021", label: "2021" },
];

const REPORT_OPTIONS = [
  { value: "11011", label: "Annual Report" },
  { value: "11012", label: "Semi-Annual" },
  { value: "11013", label: "Q1 Report" },
  { value: "11014", label: "Q3 Report" },
];

interface CompanyFinancialsProps {
  corpCode: string;
}

export default function CompanyFinancials({
  corpCode,
}: CompanyFinancialsProps) {
  const [year, setYear] = useState("2024");
  const [reportCode, setReportCode] = useState("11011");

  const { data: financials, isLoading } = useCompanyFinancials(corpCode, {
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
      render: (row) => formatAmount(row.thstrm_amount, "KRW"),
    },
    {
      key: "frmtrm_amount",
      header: "Previous",
      align: "right",
      mono: true,
      render: (row) => formatAmount(row.frmtrm_amount, "KRW"),
    },
    {
      key: "bfefrmtrm_amount",
      header: "2 Years Ago",
      align: "right",
      mono: true,
      render: (row) => formatAmount(row.bfefrmtrm_amount, "KRW"),
    },
  ];

  const chartData = (financials ?? []).slice(0, 8).map((f) => ({
    name: f.account_nm,
    value: f.thstrm_amount ?? 0,
    displayValue: formatAmount(f.thstrm_amount, "KRW"),
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

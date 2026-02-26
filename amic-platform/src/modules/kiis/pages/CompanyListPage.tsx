import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Building2 } from "lucide-react";
import { useCompanies } from "@/modules/kiis/hooks/useCompanies";
import { useCompanyFilters } from "@/modules/kiis/hooks/useCompanyFilters";
import { Card, DataTable, Badge, EmptyState, Pagination, PageHero } from "@/components/ui";
import type { Column } from "@/components/ui";
import type { Company, SearchType } from "@/modules/kiis/types/company";
import { CompanyFilterPanel } from "@/modules/kiis/components/CompanyFilterPanel";
import {
  CORP_CLS_BADGE_VARIANT,
  CORP_CLS_LABELS,
} from "@/modules/kiis/constants/companyFilters";
import heroImg from "@/assets/images/forest-bg.jpg";

const columns: Column<Company>[] = [
  {
    key: "corp_name",
    header: "Company",
    render: (row) => (
      <span className="font-medium text-text-dark">{row.corp_name}</span>
    ),
  },
  {
    key: "stock_code",
    header: "Stock Code",
    align: "center",
    width: "120px",
    mono: true,
    render: (row) => row.stock_code ?? "-",
  },
  {
    key: "corp_cls",
    header: "Market",
    align: "center",
    width: "100px",
    render: (row) =>
      row.corp_cls ? (
        <Badge variant={CORP_CLS_BADGE_VARIANT[row.corp_cls] ?? "neutral"}>
          {CORP_CLS_LABELS[row.corp_cls] ?? row.corp_cls}
        </Badge>
      ) : (
        "-"
      ),
  },
  {
    key: "stock_name",
    header: "Stock Name",
    render: (row) => row.stock_name ?? "-",
  },
];

export default function CompanyListPage() {
  const navigate = useNavigate();
  const {
    params,
    setFilter,
    getSelected,
    setPage,
    resetFilters,
    activeFilterCount,
    page,
  } = useCompanyFilters();

  const [searchText, setSearchText] = useState(params.search ?? "");
  const [searchType, setSearchType] = useState<SearchType>(params.search_type ?? "name");

  const { data, isLoading } = useCompanies(params);

  return (
    <div className="space-y-6">
      <PageHero
        title="Companies"
        subtitle="Search and browse listed companies"
        compact
        backgroundImage={heroImg}
        backgroundOpacity={0.18}
      />

      <CompanyFilterPanel
        searchText={searchText}
        onSearchTextChange={setSearchText}
        searchType={searchType}
        onSearchTypeChange={setSearchType}
        corpClsList={getSelected("corp_cls")}
        onSetFilter={setFilter}
        onReset={() => {
          resetFilters();
          setSearchText("");
          setSearchType("name");
        }}
        activeFilterCount={activeFilterCount}
      />

      <Card padding="none">
        {!isLoading && (!data?.items || data.items.length === 0) ? (
          <EmptyState
            icon={Building2}
            title="No companies found"
            description="Try adjusting your search or filters."
          />
        ) : (
          <DataTable
            columns={columns}
            data={data?.items ?? []}
            keyField="corp_code"
            loading={isLoading}
            onRowClick={(row) => navigate(`/kiis/companies/${row.corp_code}`)}
            striped
          />
        )}
      </Card>

      <Pagination
        page={page}
        totalPages={data ? Math.ceil(data.total / 20) : 0}
        onPageChange={setPage}
      />
    </div>
  );
}

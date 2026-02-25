import { useState, useMemo, useRef } from "react";
import { useNavigate } from "react-router-dom";
import {
  Plus,
  Briefcase,
  FileText,
  Loader2,
  Clock,
} from "lucide-react";

import { useTransactions } from "@/modules/ma/hooks/useTransactions";
import type { Transaction } from "@/modules/ma/types/transaction";
import {
  PHASE_CONFIG,
  TRANSACTION_STATUS_OPTIONS,
} from "@/modules/ma/constants";

import CategoryCard from "@/modules/docs/components/CategoryCard";
import { STUDIO_CATEGORIES } from "@/modules/docs/types/studio-categories";

import {
  Button,
  Card,
  Badge,
  DataTable,
  KpiCard,
  PageHero,
  Select,
  Input,
  Pagination,
  EmptyState,
} from "@/components/ui";
import type { Column, SelectOption } from "@/components/ui";
import { useScrollReveal } from "@/hooks/useScrollReveal";
import heroImg from "@/assets/images/heroes/hero-arch-symmetry.jpg";

const PHASE_LABELS: Record<string, string> = Object.fromEntries(
  PHASE_CONFIG.map((p) => [p.phase, p.label]),
);

const STATUS_VARIANT: Record<string, "success" | "warning" | "error" | "info" | "neutral"> = {
  DRAFT: "neutral",
  ACTIVE: "success",
  ON_HOLD: "warning",
  COMPLETED: "info",
  TERMINATED: "error",
};

const PHASE_FILTER_OPTIONS: SelectOption[] = [
  { value: "", label: "전체 단계" },
  ...PHASE_CONFIG.map((p) => ({ value: p.phase, label: p.label })),
];

export default function StudioHomePage() {
  const navigate = useNavigate();
  const [search, setSearch] = useState("");
  const [phaseFilter, setPhaseFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [page, setPage] = useState(1);
  const pageSize = 20;

  const kpiRef = useRef<HTMLDivElement>(null);
  const shortcutsRef = useRef<HTMLDivElement>(null);
  useScrollReveal(kpiRef, { stagger: 0.06, y: 20 });
  useScrollReveal(shortcutsRef, { stagger: 0.1, y: 24 });

  const { data, isLoading } = useTransactions({
    search: search || undefined,
    phase: (phaseFilter as Transaction["phase"]) || undefined,
    status: (statusFilter as Transaction["status"]) || undefined,
    limit: pageSize,
    offset: (page - 1) * pageSize,
  });

  const items = useMemo(() => data?.items ?? [], [data?.items]);
  const total = data?.total ?? 0;
  const totalPages = Math.ceil(total / pageSize);

  const kpis = useMemo(() => {
    const now = new Date();
    return {
      total,
      linked: items.filter((t) => t.im_document_id || t.fdd_deal_id).length,
      active: items.filter((t) => t.status === "ACTIVE").length,
      thisMonth: items.filter((t) => {
        const d = new Date(t.created_at);
        return d.getMonth() === now.getMonth() && d.getFullYear() === now.getFullYear();
      }).length,
    };
  }, [items, total]);

  const columns: Column<Transaction>[] = [
    {
      key: "code_name",
      header: "Code",
      width: "120px",
      render: (row) => (
        <span className="font-mono text-sm font-medium text-accent">
          {row.code_name}
        </span>
      ),
    },
    {
      key: "name",
      header: "거래명",
      render: (row) => (
        <div>
          <span className="font-medium">{row.name}</span>
          <span className="block text-xs text-text-muted">
            {row.target_company_name}
          </span>
        </div>
      ),
    },
    {
      key: "phase",
      header: "단계",
      width: "100px",
      render: (row) => (
        <span className="text-sm">{PHASE_LABELS[row.phase] ?? row.phase}</span>
      ),
    },
    {
      key: "im_document_id",
      header: "문서 현황",
      width: "200px",
      render: (row) => (
        <div className="flex gap-1.5">
          {row.im_document_id && (
            <span className="inline-block px-2 py-0.5 text-xs font-medium rounded bg-info-light text-info">
              IM
            </span>
          )}
          {row.fdd_deal_id && (
            <span className="inline-block px-2 py-0.5 text-xs font-medium rounded bg-info-light text-info">
              FDD
            </span>
          )}
          {!row.im_document_id && !row.fdd_deal_id && (
            <span className="text-xs text-text-muted">&mdash;</span>
          )}
        </div>
      ),
    },
    {
      key: "status",
      header: "상태",
      width: "100px",
      align: "center",
      render: (row) => (
        <Badge variant={STATUS_VARIANT[row.status] ?? "neutral"}>
          {row.status}
        </Badge>
      ),
    },
    {
      key: "created_at",
      header: "생성일",
      width: "120px",
      render: (row) => new Date(row.created_at).toLocaleDateString(),
    },
  ];

  return (
    <div className="space-y-6">
      {/* 1. PageHero */}
      <PageHero
        title="Deal Document Studio"
        subtitle="M&A 거래별 문서를 생성하고 관리합니다"
        backgroundImage={heroImg}
        backgroundOpacity={0.18}
        compact
        actions={
          <Button
            variant="accent"
            icon={Plus}
            onClick={() => navigate("/docs/new")}
          >
            New Document
          </Button>
        }
      />

      {/* 2. KPI Cards - 표준 4-grid */}
      <div ref={kpiRef} className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard
          label="전체 거래"
          value={String(kpis.total)}
          icon={Briefcase}
        />
        <KpiCard
          label="문서 연결됨"
          value={String(kpis.linked)}
          icon={FileText}
        />
        <KpiCard
          label="진행 중"
          value={String(kpis.active)}
          icon={Loader2}
          variant="caution"
        />
        <KpiCard
          label="이번 달"
          value={String(kpis.thisMonth)}
          icon={Clock}
        />
      </div>

      {/* 3. Filter Card */}
      <Card padding="md">
        <div className="flex flex-wrap items-end gap-4">
          <div className="flex-1 min-w-[200px]">
            <Input
              label="검색"
              placeholder="거래명, 코드네임, 대상기업..."
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setPage(1);
              }}
            />
          </div>
          <div className="w-40">
            <Select
              label="단계"
              options={PHASE_FILTER_OPTIONS}
              value={phaseFilter}
              onChange={(e) => {
                setPhaseFilter(e.target.value);
                setPage(1);
              }}
            />
          </div>
          <div className="w-40">
            <Select
              label="상태"
              options={TRANSACTION_STATUS_OPTIONS}
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value);
                setPage(1);
              }}
            />
          </div>
        </div>
      </Card>

      {/* 4. 거래별 문서 현황 테이블 */}
      <Card title="거래별 문서 현황" headerBar padding="none">
        {!isLoading && items.length === 0 ? (
          <EmptyState
            icon={Briefcase}
            title="거래가 없습니다"
            description="M&A 파이프라인에서 거래를 생성하면 문서를 관리할 수 있습니다."
            actionLabel="New Transaction"
            onAction={() => navigate("/ma/transactions/new")}
          />
        ) : (
          <DataTable
            columns={columns}
            data={items}
            keyField="id"
            loading={isLoading}
            onRowClick={(row) => navigate(`/ma/transactions/${row.id}`)}
            emptyMessage="조건에 맞는 거래가 없습니다"
            borderless
          />
        )}
      </Card>

      {/* 5. Pagination */}
      {totalPages > 1 && (
        <Pagination
          page={page}
          totalPages={totalPages}
          onPageChange={setPage}
        />
      )}

      {/* 6. 문서 유형 바로가기 */}
      <div ref={shortcutsRef}>
        <Card title="문서 유형 바로가기" headerBar>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
            {STUDIO_CATEGORIES.map((cat) => (
              <CategoryCard key={cat.id} category={cat} />
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
}

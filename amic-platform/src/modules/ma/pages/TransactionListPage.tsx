import { useState, useMemo, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";
import { Plus, Pencil, Briefcase, TrendingUp, DollarSign } from "lucide-react";

import {
  useTransactions,
  useMaStats,
} from "@/modules/ma/hooks/useTransactions";
import type { Transaction } from "@/modules/ma/types/transaction";
import {
  TRANSACTION_SIDE_OPTIONS,
  TRANSACTION_STATUS_OPTIONS,
  TRANSACTION_STATUS_VARIANT,
  PHASE_CONFIG,
} from "@/modules/ma/constants";

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
import type { Column } from "@/components/ui";
import { useScrollReveal } from "@/hooks/useScrollReveal";
import heroImg from "@/assets/images/heroes/hero-arch-teal.jpg";
import EditTransactionModal from "@/modules/ma/components/EditTransactionModal";

const PHASE_LABELS: Record<string, string> = Object.fromEntries(
  PHASE_CONFIG.map((p) => [p.phase, p.label]),
);

const SIDE_LABEL: Record<string, string> = {
  SELL: "Sell",
  BUY: "Buy",
  DUAL: "Dual",
};

function formatKrwCompact(val: string | number | null): string {
  if (val == null) return "-";
  const num = typeof val === "string" ? parseFloat(val) : val;
  if (isNaN(num) || num === 0) return "-";
  const abs = Math.abs(num);
  const sign = num < 0 ? "-" : "";
  if (abs >= 1_0000_0000) {
    const eok = Math.round(abs / 1_0000_0000);
    return `${sign}${eok.toLocaleString("ko-KR")}억원`;
  }
  if (abs >= 1_0000) {
    const man = Math.round(abs / 1_0000);
    return `${sign}${man.toLocaleString("ko-KR")}만원`;
  }
  return `${sign}${abs.toLocaleString("ko-KR")}원`;
}

function formatValue(val: string | number | null, currency: string): string {
  if (val == null) return "-";
  if (currency === "KRW") return formatKrwCompact(val);
  const num = typeof val === "string" ? parseFloat(val) : val;
  if (isNaN(num)) return "-";
  return new Intl.NumberFormat("ko-KR", {
    style: "currency",
    currency,
    maximumFractionDigits: 0,
  }).format(num);
}

export default function TransactionListPage() {
  const navigate = useNavigate();
  const { canWrite, isClient } = useAuth();
  const [search, setSearch] = useState("");
  const [sideFilter, setSideFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [page, setPage] = useState(1);
  const [editTarget, setEditTarget] = useState<Transaction | null>(null);
  const pageSize = 20;

  const kpiRef = useRef<HTMLDivElement>(null);
  useScrollReveal(kpiRef, { stagger: 0.06, y: 20 });

  const { data, isLoading } = useTransactions({
    search: search || undefined,
    side: (sideFilter as Transaction["side"]) || undefined,
    status: (statusFilter as Transaction["status"]) || undefined,
    limit: pageSize,
    offset: (page - 1) * pageSize,
  });

  // KPI 통계 (DB 집계 기반)
  const { data: stats } = useMaStats();

  const items = useMemo(() => data?.items ?? [], [data?.items]);
  const total = data?.total ?? 0;
  const totalPages = Math.ceil(total / pageSize);

  // KPI 계산 — DB 집계 기반
  const kpis = useMemo(
    () => ({
      total: stats?.total_transactions ?? total,
      active: stats?.active_transactions ?? 0,
      totalValue: Number(stats?.total_deal_value ?? 0),
    }),
    [stats, total],
  );

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
      width: "280px",
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
      key: "side",
      header: "유형",
      width: "80px",
      align: "center",
      render: (row) => (
        <Badge variant={row.side === "SELL" ? "info" : "neutral"} pill>
          {SIDE_LABEL[row.side] ?? row.side}
        </Badge>
      ),
    },
    {
      key: "phase",
      header: "단계",
      width: "110px",
      render: (row) => (
        <span className="text-sm">{PHASE_LABELS[row.phase] ?? row.phase}</span>
      ),
    },
    {
      key: "status",
      header: "상태",
      width: "100px",
      align: "center",
      render: (row) => (
        <Badge variant={TRANSACTION_STATUS_VARIANT[row.status] ?? "neutral"}>
          {row.status}
        </Badge>
      ),
    },
    {
      key: "estimated_deal_value",
      header: "예상 금액",
      width: "150px",
      align: "right",
      mono: true,
      render: (row) => formatValue(row.estimated_deal_value, row.currency),
    },
    {
      key: "client_name",
      header: "클라이언트",
      width: "160px",
      render: (row) => (
        <span className="text-sm text-text-secondary">{row.client_name}</span>
      ),
    },
    ...(canWrite()
      ? [
          {
            key: "actions" as keyof Transaction,
            header: "",
            width: "48px",
            align: "center" as const,
            render: (row: Transaction) => (
              <button
                type="button"
                className="p-1.5 rounded-md text-text-muted hover:text-accent hover:bg-accent/10 transition-colors"
                title="기본정보 수정"
                onClick={(e) => {
                  e.stopPropagation();
                  setEditTarget(row);
                }}
              >
                <Pencil size={15} />
              </button>
            ),
          },
        ]
      : []),
  ];

  return (
    <div className="space-y-6">
      <PageHero
        title="M&A Pipeline"
        subtitle={
          isClient ? "배정된 거래 목록" : "7단계 워크플로우 기반 거래 관리"
        }
        backgroundImage={heroImg}
        backgroundOpacity={0.18}
        compact
        actions={
          canWrite() ? (
            <Button
              icon={Plus}
              onClick={() => navigate("/ma/transactions/new")}
            >
              New Transaction
            </Button>
          ) : undefined
        }
      />

      {/* KPI 카드 */}
      <div ref={kpiRef} className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <KpiCard
          label="전체 거래"
          value={String(kpis.total)}
          icon={Briefcase}
        />
        <KpiCard
          label="진행 중"
          value={String(kpis.active)}
          icon={TrendingUp}
        />
        <KpiCard
          label="예상 총액"
          value={formatKrwCompact(kpis.totalValue || null)}
          icon={DollarSign}
        />
      </div>

      {/* 필터 바 */}
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
              label="유형"
              options={TRANSACTION_SIDE_OPTIONS}
              value={sideFilter}
              onChange={(e) => {
                setSideFilter(e.target.value);
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

      {/* 거래 목록 테이블 */}
      <Card title="Transactions" headerBar padding="none">
        {!isLoading && items.length === 0 ? (
          <EmptyState
            icon={Briefcase}
            title="거래가 없습니다"
            description={
              canWrite()
                ? "새 거래를 생성하여 M&A 파이프라인을 시작하세요."
                : "배정된 거래가 없습니다."
            }
            actionLabel={canWrite() ? "New Transaction" : undefined}
            onAction={
              canWrite() ? () => navigate("/ma/transactions/new") : undefined
            }
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

      {totalPages > 1 && (
        <Pagination
          page={page}
          totalPages={totalPages}
          onPageChange={setPage}
        />
      )}

      {/* 편집 모달 */}
      {editTarget && (
        <EditTransactionModal
          open={!!editTarget}
          onClose={() => setEditTarget(null)}
          transaction={editTarget}
        />
      )}
    </div>
  );
}

import { useMemo, useRef } from "react";
import { useNavigate } from "react-router-dom";
import {
  Plus,
  BarChart2,
  Gavel,
  FileText,
  Loader2,
  CheckCircle,
  XCircle,
} from "lucide-react";
import {
  Button,
  Card,
  DataTable,
  KpiCard,
  EmptyState,
  PageHero,
} from "@/components/ui";
import type { Column } from "@/components/ui";
import { useScrollReveal } from "@/hooks/useScrollReveal";
import { useFDDDeals } from "@/modules/docs/hooks/useFDDDocuments";
import { useLDDReportsList } from "@/modules/docs/hooks/useLDDReports";
import type { Deal, DealStatus } from "@/modules/fdd/types/deal";
import type { LDDReport } from "@/modules/docs/types/ldd_report";
import {
  LDD_STATUS_LABELS,
  LDD_STATUS_COLORS,
  LDD_REPORT_TYPE_LABELS,
} from "@/modules/docs/types/ldd_report";
import heroImg from "@/assets/images/heroes/hero-arch-dome.jpg";

type DDType = "fdd" | "ldd";

interface Props {
  type: DDType;
}

const DD_CONFIG = {
  fdd: {
    title: "FDD (재무실사)",
    subtitle: "재무 실사 보고서를 생성하고 관리합니다.",
    icon: BarChart2,
    createLabel: "새 FDD 생성",
    createPath: "/docs/new?type=fdd",
    emptyTitle: "FDD 보고서가 없습니다",
    emptyDesc: "재무실사 보고서를 생성하여 분석을 시작하세요.",
  },
  ldd: {
    title: "LDD (법률실사)",
    subtitle: "법률 실사 보고서를 생성하고 관리합니다.",
    icon: Gavel,
    createLabel: "새 LDD 생성",
    createPath: "/docs/ldd/new",
    emptyTitle: "LDD 보고서가 없습니다",
    emptyDesc: "DDRL 체크리스트 기반 법률실사 보고서를 생성하세요.",
  },
} as const;

// ── Status badge helpers ──

const FDD_STATUS_LABELS: Record<DealStatus, string> = {
  DRAFT: "초안",
  ACTIVE: "진행중",
  ARCHIVED: "완료",
};

const FDD_STATUS_COLORS: Record<DealStatus, string> = {
  DRAFT: "bg-slate-100 text-slate-600",
  ACTIVE: "bg-blue-100 text-blue-700",
  ARCHIVED: "bg-green-100 text-green-700",
};

function StatusBadge({ label, className }: { label: string; className: string }) {
  return (
    <span className={`inline-flex px-2 py-0.5 rounded-full text-[11px] font-medium ${className}`}>
      {label}
    </span>
  );
}

// ── FDD columns ──

const fddColumns: Column<Deal>[] = [
  {
    key: "name",
    header: "보고서명",
    render: (row) => <span className="font-medium text-text-primary">{row.name}</span>,
  },
  {
    key: "target_company_name",
    header: "대상회사",
    render: (row) => row.target_company_name ?? "—",
  },
  {
    key: "status",
    header: "상태",
    render: (row) => (
      <StatusBadge label={FDD_STATUS_LABELS[row.status]} className={FDD_STATUS_COLORS[row.status]} />
    ),
  },
  {
    key: "created_at",
    header: "생성일",
    render: (row) => new Date(row.created_at).toLocaleDateString("ko-KR"),
  },
];

// ── LDD columns ──

const lddColumns: Column<LDDReport>[] = [
  {
    key: "title",
    header: "보고서명",
    render: (row) => <span className="font-medium text-text-primary">{row.title}</span>,
  },
  {
    key: "report_type",
    header: "유형",
    render: (row) => (
      <span className="text-xs text-text-secondary">
        {LDD_REPORT_TYPE_LABELS[row.report_type]}
      </span>
    ),
  },
  {
    key: "status",
    header: "상태",
    render: (row) => (
      <StatusBadge
        label={LDD_STATUS_LABELS[row.status]}
        className={LDD_STATUS_COLORS[row.status]}
      />
    ),
  },
  {
    key: "created_at",
    header: "생성일",
    render: (row) => new Date(row.created_at).toLocaleDateString("ko-KR"),
  },
];

// ── FDD Section ──

function FDDContent() {
  const navigate = useNavigate();
  const { data: fddDeals, isLoading } = useFDDDeals({ limit: 50 });
  const items = useMemo(() => fddDeals?.items ?? [], [fddDeals]);
  const config = DD_CONFIG.fdd;

  const kpis = useMemo(() => {
    const active = items.filter((d) => d.status === "ACTIVE").length;
    const draft = items.filter((d) => d.status === "DRAFT").length;
    const archived = items.filter((d) => d.status === "ARCHIVED").length;
    return { total: items.length, active, draft, archived };
  }, [items]);

  return (
    <>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <KpiCard label="전체" value={String(kpis.total)} icon={FileText} />
        <KpiCard label="진행중" value={String(kpis.active)} icon={Loader2} variant="positive" />
        <KpiCard label="초안" value={String(kpis.draft)} icon={FileText} variant="caution" />
        <KpiCard label="완료" value={String(kpis.archived)} icon={CheckCircle} />
      </div>

      <Card padding="none">
        {!isLoading && items.length === 0 ? (
          <EmptyState
            icon={config.icon}
            title={config.emptyTitle}
            description={config.emptyDesc}
            actionLabel={config.createLabel}
            onAction={() => navigate(config.createPath)}
          />
        ) : (
          <DataTable
            columns={fddColumns}
            data={items}
            keyField="id"
            loading={isLoading}
            onRowClick={(row) => navigate(`/fdd/deals/${row.id}`)}
            striped
          />
        )}
      </Card>
    </>
  );
}

// ── LDD Section ──

function LDDContent() {
  const navigate = useNavigate();
  const { data: reports, isLoading } = useLDDReportsList();
  const items = useMemo(() => reports ?? [], [reports]);
  const config = DD_CONFIG.ldd;

  const kpis = useMemo(() => {
    const generating = items.filter((r) => r.status === "GENERATING").length;
    const ready = items.filter((r) => r.status === "READY").length;
    const failed = items.filter((r) => r.status === "FAILED").length;
    return { total: items.length, generating, ready, failed };
  }, [items]);

  return (
    <>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <KpiCard label="전체" value={String(kpis.total)} icon={FileText} />
        <KpiCard label="생성중" value={String(kpis.generating)} icon={Loader2} variant="caution" />
        <KpiCard label="완료" value={String(kpis.ready)} icon={CheckCircle} variant="positive" />
        <KpiCard label="실패" value={String(kpis.failed)} icon={XCircle} variant="negative" />
      </div>

      <Card padding="none">
        {!isLoading && items.length === 0 ? (
          <EmptyState
            icon={config.icon}
            title={config.emptyTitle}
            description={config.emptyDesc}
            actionLabel={config.createLabel}
            onAction={() => navigate(config.createPath)}
          />
        ) : (
          <DataTable
            columns={lddColumns}
            data={items}
            keyField="id"
            loading={isLoading}
            striped
          />
        )}
      </Card>
    </>
  );
}

// ── Main Page ──

export default function DDReportListPage({ type }: Props) {
  const navigate = useNavigate();
  const config = DD_CONFIG[type];
  const cardsRef = useRef<HTMLDivElement>(null);
  useScrollReveal(cardsRef, { stagger: 0.08, y: 20 });

  return (
    <div className="space-y-6">
      <PageHero
        title={config.title}
        subtitle={config.subtitle}
        backgroundImage={heroImg}
        backgroundOpacity={0.18}
        compact
        actions={
          <Button
            variant="accent"
            icon={Plus}
            onClick={() => navigate(config.createPath)}
          >
            {config.createLabel}
          </Button>
        }
      />

      <div ref={cardsRef} className="space-y-6">
        {type === "fdd" && <FDDContent />}
        {type === "ldd" && <LDDContent />}
      </div>
    </div>
  );
}

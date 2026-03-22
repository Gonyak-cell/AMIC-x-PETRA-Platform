import { useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Plus,
  ChevronLeft,
  ChevronRight,
  FileText,
  Loader2,
  CheckCircle,
  AlertTriangle,
  BarChart2,
  ArrowRight,
  Gavel,
  Calculator,
} from "lucide-react";
import {
  STUDIO_CATEGORIES,
  type DocumentCategory,
} from "@/modules/docs/types/studio-categories";
import CategoryCard from "@/modules/docs/components/CategoryCard";
import { DocumentStatusBadge } from "@/modules/docs/components/DocumentStatusBadge";
import { useDocuments } from "@/modules/docs/hooks/useDocuments";
import { useFDDDeals } from "@/modules/docs/hooks/useFDDDocuments";
import { IN_PROGRESS_STATUSES, getDocumentType } from "@/modules/docs/types/document";
import type { Document, DocumentStatus, DataSource } from "@/modules/docs/types/document";
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
import heroImg from "@/assets/images/heroes/hero-arch-dome.jpg";

type StudioCategoryId = "marketing" | "legal" | "due_diligence" | "checklists";

interface Props {
  category: StudioCategoryId;
}

// ── Marketing columns (reused from StudioHomePage) ──

const marketingColumns: Column<Document>[] = [
  {
    key: "im_style",
    header: "Type",
    align: "center",
    width: "80px",
    render: (row) => {
      const type = getDocumentType(row.im_style);
      return (
        <span
          className={`inline-block px-2 py-0.5 text-xs font-medium rounded ${
            type === "teaser"
              ? "bg-violet-100 text-violet-700"
              : "bg-info-light text-info"
          }`}
        >
          {type === "teaser" ? "TM" : "IM"}
        </span>
      );
    },
  },
  {
    key: "project_name",
    header: "Project",
    render: (row) => (
      <span className="font-medium text-text-dark">
        {row.project_name || row.company_name}
      </span>
    ),
  },
  {
    key: "company_name",
    header: "Company",
    render: (row) => row.company_name,
  },
  {
    key: "data_source",
    header: "Source",
    align: "center",
    width: "100px",
    render: (row) => {
      const badge: Record<DataSource, { label: string; cls: string }> = {
        DART: { label: "DART", cls: "bg-info-light text-info" },
        MANUAL: { label: "Manual", cls: "bg-gray-100 text-gray-600" },
        EXCEL: { label: "Excel", cls: "bg-emerald-100 text-emerald-700" },
      };
      const b = badge[row.data_source] ?? badge.MANUAL;
      return (
        <span className={`inline-block px-2 py-0.5 text-xs font-medium rounded ${b.cls}`}>
          {b.label}
        </span>
      );
    },
  },
  {
    key: "status",
    header: "Status",
    align: "center",
    width: "120px",
    render: (row) => <DocumentStatusBadge status={row.status} />,
  },
  {
    key: "created_at",
    header: "Created",
    width: "140px",
    render: (row) => new Date(row.created_at).toLocaleDateString(),
  },
];

const PAGE_SIZE = 20;

// ── Marketing Section ──

function MarketingSection() {
  const navigate = useNavigate();
  const [page, setPage] = useState(0);
  const [statusFilter, setStatusFilter] = useState<"ALL" | "IN_PROGRESS" | DocumentStatus>("ALL");
  const { data, isLoading, isError } = useDocuments({ offset: page * PAGE_SIZE, limit: PAGE_SIZE });

  const total = data?.total ?? 0;
  const totalPages = Math.ceil(total / PAGE_SIZE);
  const items = useMemo(() => data?.items ?? [], [data?.items]);
  const filteredItems = useMemo(() => {
    if (statusFilter === "ALL") return items;
    if (statusFilter === "IN_PROGRESS")
      return items.filter((d) => IN_PROGRESS_STATUSES.includes(d.status));
    return items.filter((d) => d.status === statusFilter);
  }, [items, statusFilter]);

  const kpis = useMemo(
    () => ({
      total: data?.total ?? 0,
      inProgress: items.filter((d) => IN_PROGRESS_STATUSES.includes(d.status)).length,
      completed: items.filter((d) => d.status === "COMPLETED").length,
      failed: items.filter((d) => d.status === "FAILED").length,
    }),
    [data?.total, items],
  );

  return (
    <>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <KpiCard label="Total" value={String(kpis.total)} icon={FileText} />
        <KpiCard label="In Progress" value={String(kpis.inProgress)} icon={Loader2} variant="caution" />
        <KpiCard label="Completed" value={String(kpis.completed)} icon={CheckCircle} variant="positive" />
        <KpiCard label="Failed" value={String(kpis.failed)} icon={AlertTriangle} variant="negative" />
      </div>

      <div className="flex gap-2">
        {(["ALL", "IN_PROGRESS", "COMPLETED", "FAILED"] as const).map((s) => (
          <Button
            key={s}
            variant={statusFilter === s ? "accent" : "ghost"}
            size="sm"
            onClick={() => { setStatusFilter(s); setPage(0); }}
          >
            {s === "ALL" ? "All" : s === "IN_PROGRESS" ? "In Progress" : s.charAt(0) + s.slice(1).toLowerCase()}
          </Button>
        ))}
      </div>

      <Card title="Documents" headerBar padding="none">
        {isError ? (
          <EmptyState icon={AlertTriangle} title="Failed to load" description="Could not fetch documents." />
        ) : !isLoading && filteredItems.length === 0 ? (
          <EmptyState
            icon={FileText}
            title="No documents yet"
            description="Create your first marketing document."
          />
        ) : (
          <>
            <DataTable
              columns={marketingColumns}
              data={filteredItems}
              keyField="id"
              loading={isLoading}
              onRowClick={(row) => navigate(`/docs/documents/${row.id}`)}
              striped
            />
            {totalPages > 1 && (
              <div className="flex items-center justify-between px-4 py-3 border-t border-gray-border">
                <span className="text-sm text-text-secondary">
                  Showing {page * PAGE_SIZE + 1}&ndash;{Math.min((page + 1) * PAGE_SIZE, total)} of {total}
                </span>
                <div className="flex gap-2">
                  <Button variant="ghost" size="sm" icon={ChevronLeft} onClick={() => setPage((p) => p - 1)} disabled={page === 0}>
                    Previous
                  </Button>
                  <Button variant="ghost" size="sm" icon={ChevronRight} onClick={() => setPage((p) => p + 1)} disabled={page + 1 >= totalPages}>
                    Next
                  </Button>
                </div>
              </div>
            )}
          </>
        )}
      </Card>
    </>
  );
}

// ── Legal Section ──

function LegalSection() {
  return (
    <Card padding="lg">
      <EmptyState
        icon={ArrowRight}
        title="거래 컨텍스트에서 생성"
        description="법률 문서는 M&A 거래 워크스페이스에서 생성됩니다. 새 문서를 생성하려면 아래 버튼을 클릭하세요."
      />
    </Card>
  );
}

// ── Due Diligence Section ──

function DDSection() {
  const navigate = useNavigate();
  const { data: fddDeals, isLoading } = useFDDDeals({ limit: 50 });
  const fddItems = useMemo(() => fddDeals?.items ?? [], [fddDeals]);

  const ddKpis = useMemo(() => {
    const active = fddItems.filter((d) => d.status === "ACTIVE").length;
    const draft = fddItems.filter((d) => d.status === "DRAFT").length;
    const archived = fddItems.filter((d) => d.status === "ARCHIVED").length;
    return { total: fddItems.length, active, draft, archived };
  }, [fddItems]);

  return (
    <>
      {/* DD 현황 KPI */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <KpiCard label="전체 DD" value={String(ddKpis.total)} icon={BarChart2} />
        <KpiCard label="진행중" value={String(ddKpis.active)} icon={Loader2} variant="positive" />
        <KpiCard label="준비중" value={String(ddKpis.draft)} icon={FileText} variant="caution" />
        <KpiCard label="완료" value={String(ddKpis.archived)} icon={CheckCircle} />
      </div>

      {/* DD 유형 카드 그리드 */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* FDD */}
        <div
          className="rounded-xl border border-border p-5 flex flex-col gap-3 transition-all hover:border-accent-primary hover:shadow-md cursor-pointer"
          role="button"
          tabIndex={0}
          onClick={() => navigate("/docs/new?type=fdd")}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") {
              e.preventDefault();
              navigate("/docs/new?type=fdd");
            }
          }}
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <BarChart2 className="h-5 w-5 text-accent-primary" />
              <h4 className="text-sm font-semibold text-text-primary">FDD (재무실사)</h4>
            </div>
            <ArrowRight className="h-4 w-4 text-text-tertiary" />
          </div>
          <p className="text-xs text-text-secondary leading-relaxed">
            재무 실사 보고서를 생성하여 분석을 시작하세요.
          </p>
          {!isLoading && fddItems.length > 0 && (
            <span className="text-xs text-text-tertiary">{fddItems.length}건</span>
          )}
        </div>

        {/* LDD */}
        <div
          className="rounded-xl border border-border p-5 flex flex-col gap-3 transition-all hover:border-accent-primary hover:shadow-md cursor-pointer"
          role="button"
          tabIndex={0}
          onClick={() => navigate("/docs/ldd/new")}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") {
              e.preventDefault();
              navigate("/docs/ldd/new");
            }
          }}
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Gavel className="h-5 w-5 text-accent-primary" />
              <h4 className="text-sm font-semibold text-text-primary">LDD (법률실사)</h4>
            </div>
            <ArrowRight className="h-4 w-4 text-text-tertiary" />
          </div>
          <p className="text-xs text-text-secondary leading-relaxed">
            DDRL 체크리스트 기반 법률실사 보고서를 생성합니다.
          </p>
        </div>

        {/* TDD — Coming Soon */}
        <div className="rounded-xl border border-border/60 p-5 flex flex-col gap-3 opacity-60">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Calculator className="h-5 w-5 text-accent-primary" />
              <h4 className="text-sm font-semibold text-text-primary">TDD (세무실사)</h4>
            </div>
            <span className="text-[10px] font-medium uppercase tracking-wider text-text-tertiary bg-white-alt px-2 py-0.5 rounded-full">
              Coming Soon
            </span>
          </div>
          <p className="text-xs text-text-secondary leading-relaxed">
            세무 실사 보고서 생성 및 관리
          </p>
        </div>
      </div>
    </>
  );
}

// ── Checklist Section ──

function ChecklistSection() {
  return (
    <Card padding="lg">
      <EmptyState
        icon={ArrowRight}
        title="거래 워크스페이스에서 관리"
        description="체크리스트와 타임라인은 M&A 거래 워크스페이스에서 관리됩니다. 거래를 선택하여 체크리스트를 확인하세요."
      />
    </Card>
  );
}

// ── Main Page ──

export default function CategoryDocumentsPage({ category }: Props) {
  const navigate = useNavigate();
  const cat = STUDIO_CATEGORIES.find((c) => c.id === category) as DocumentCategory;
  const cardsRef = useRef<HTMLDivElement>(null);
  useScrollReveal(cardsRef, { stagger: 0.08, y: 20 });

  const createPaths: Record<StudioCategoryId, string> = {
    marketing: "/docs/new",
    legal: "/docs/legal/new",
    due_diligence: "/docs/new?type=fdd",
    checklists: "/ma/transactions",
  };

  return (
    <div className="space-y-6">
      <PageHero
        title={cat.label}
        subtitle={cat.description}
        backgroundImage={heroImg}
        backgroundOpacity={0.18}
        compact
        actions={
          <Button
            variant="accent"
            icon={Plus}
            onClick={() => navigate(createPaths[category])}
          >
            {category === "checklists" ? "거래 선택" : "New Document"}
          </Button>
        }
      />

      {/* Sub-type cards */}
      <div ref={cardsRef} className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <CategoryCard category={cat} />
      </div>

      {/* Category-specific content */}
      {category === "marketing" && <MarketingSection />}
      {category === "legal" && <LegalSection />}
      {category === "due_diligence" && <DDSection />}
      {category === "checklists" && <ChecklistSection />}
    </div>
  );
}

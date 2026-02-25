import { useRef } from "react";
import { useNavigate } from "react-router-dom";
import {
  FolderLock,
  FileText,
  HardDrive,
  CheckCircle2,
} from "lucide-react";

import {
  Badge,
  Card,
  DataTable,
  KpiCard,
  PageHero,
  EmptyState,
} from "@/components/ui";
import type { Column } from "@/components/ui";
import { useScrollReveal } from "@/hooks/useScrollReveal";
import { PHASE_CONFIG } from "@/modules/ma/constants";
import { useVdrOverview } from "@/modules/vdr/hooks/useVdrOverview";
import type { VdrOverviewItem } from "@/modules/vdr/types/overview";
import heroImg from "@/assets/images/heroes/forestgp-nature.jpg";

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

function formatFileSize(bytes: number): string {
  if (bytes === 0) return "-";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
}

function formatDate(iso: string | null): string {
  if (!iso) return "-";
  return new Date(iso).toLocaleDateString("ko-KR", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  });
}

export default function VdrOverviewPage() {
  const navigate = useNavigate();
  const { data: items, isLoading } = useVdrOverview();

  const kpiRef = useRef<HTMLDivElement>(null);
  useScrollReveal(kpiRef, { stagger: 0.06, y: 20 });

  const initialized = items?.filter((i) => i.vdr_initialized) ?? [];
  const totalDocs = items?.reduce((s, i) => s + i.total_documents, 0) ?? 0;
  const totalSize = items?.reduce((s, i) => s + i.total_size_bytes, 0) ?? 0;

  const columns: Column<VdrOverviewItem>[] = [
    {
      key: "transaction_name",
      header: "거래명",
      render: (item) => (
        <div>
          <div className="font-medium text-slate-900">{item.transaction_name}</div>
          <div className="text-xs text-slate-400">{item.code_name}</div>
        </div>
      ),
    },
    {
      key: "phase",
      header: "단계",
      render: (item) => (
        <span className="text-xs text-slate-600">
          {PHASE_LABELS[item.phase] ?? item.phase}
        </span>
      ),
    },
    {
      key: "status",
      header: "상태",
      render: (item) => (
        <Badge variant={STATUS_VARIANT[item.status] ?? "neutral"}>
          {item.status}
        </Badge>
      ),
    },
    {
      key: "vdr_initialized",
      header: "VDR",
      render: (item) =>
        item.vdr_initialized ? (
          <Badge variant="success">초기화됨</Badge>
        ) : (
          <Badge variant="neutral">미초기화</Badge>
        ),
    },
    {
      key: "total_folders",
      header: "폴더",
      render: (item) => <span className="tabular-nums">{item.total_folders}</span>,
    },
    {
      key: "total_documents",
      header: "문서",
      render: (item) => <span className="tabular-nums">{item.total_documents}</span>,
    },
    {
      key: "total_size_bytes",
      header: "용량",
      render: (item) => (
        <span className="tabular-nums text-slate-500">
          {formatFileSize(item.total_size_bytes)}
        </span>
      ),
    },
    {
      key: "last_upload_at",
      header: "최근 업로드",
      render: (item) => (
        <span className="text-xs text-slate-500">
          {formatDate(item.last_upload_at)}
        </span>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <PageHero
        title="Virtual Data Room"
        subtitle="모든 거래의 VDR 현황을 한눈에 확인합니다."
        backgroundImage={heroImg}
        backgroundOpacity={0.18}
      />

      <div ref={kpiRef} className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <KpiCard
          title="초기화된 VDR"
          value={String(initialized.length)}
          subtitle={`전체 ${items?.length ?? 0}개 거래 중`}
          icon={CheckCircle2}
        />
        <KpiCard
          title="전체 문서"
          value={String(totalDocs)}
          subtitle="활성 문서 수"
          icon={FileText}
        />
        <KpiCard
          title="전체 용량"
          value={formatFileSize(totalSize)}
          subtitle="모든 VDR 합산"
          icon={HardDrive}
        />
      </div>

      <Card>
        {!isLoading && items?.length === 0 ? (
          <EmptyState
            icon={FolderLock}
            title="등록된 거래가 없습니다"
            description="M&A 거래를 생성하면 여기에 VDR 현황이 표시됩니다."
          />
        ) : (
          <DataTable<VdrOverviewItem>
            columns={columns}
            data={items ?? []}
            keyField="transaction_id"
            loading={isLoading}
            onRowClick={(item) =>
              navigate(`/ma/transactions/${item.transaction_id}/vdr`)
            }
          />
        )}
      </Card>
    </div>
  );
}

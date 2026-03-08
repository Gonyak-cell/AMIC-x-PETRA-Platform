import { Card } from "@/components/ui/Card";
import { KpiCard } from "@/components/ui/KpiCard";
import { Spinner } from "@/components/ui/Spinner";
import { Badge } from "@/components/ui/Badge";
import {
  ClipboardList,
  AlertCircle,
  CheckCircle2,
  Lock,
  Clock,
} from "lucide-react";
import {
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import { useRFIDashboard } from "@/modules/ma/hooks/useRFI";
import {
  RFI_ITEM_STATUS_LABELS,
  RFI_CATEGORY_LABELS,
} from "@/modules/ma/constants";
import type { RFIItemStatusV2, RFICategoryV2 } from "@/modules/ma/types/rfi";

// ── Constants ───────────────────────────────────────────

const STATUS_COLORS: Record<RFIItemStatusV2, string> = {
  OPEN: "#f59e0b",
  ANSWERED: "#10b981",
  CLARIFICATION_NEEDED: "#3b82f6",
  CLOSED: "#94a3b8",
};

const AGING_THRESHOLD_DAYS = 7;

// ── Helpers ─────────────────────────────────────────────

function daysSince(dateStr: string): number {
  const created = new Date(dateStr);
  const now = new Date();
  return Math.floor(
    (now.getTime() - created.getTime()) / (1000 * 60 * 60 * 24),
  );
}

// ── Component ───────────────────────────────────────────

interface RFIDashboardProps {
  txnId: string;
}

export default function RFIDashboard({ txnId }: RFIDashboardProps) {
  const { data, isLoading, error } = useRFIDashboard(txnId);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Spinner size="md" />
      </div>
    );
  }

  if (error) {
    return (
      <Card title="RFI 대시보드" padding="md">
        <p className="text-text-secondary text-sm">
          데이터를 불러오는 중 오류가 발생했습니다.
        </p>
      </Card>
    );
  }

  if (!data || data.total_items === 0) {
    return (
      <Card title="RFI 대시보드" padding="md">
        <div className="flex flex-col items-center justify-center py-12 gap-3">
          <ClipboardList className="h-10 w-10 text-text-secondary/40" />
          <p className="text-text-secondary text-sm">
            등록된 질의 항목이 없습니다.
          </p>
        </div>
      </Card>
    );
  }

  const { status_counts, category_breakdown, aging_items } = data;

  // -- Pie chart data
  const pieData = (
    Object.entries(STATUS_COLORS) as [RFIItemStatusV2, string][]
  ).map(([status, color]) => ({
    name: RFI_ITEM_STATUS_LABELS[status],
    value: status_counts[status] ?? 0,
    color,
  }));

  // -- Bar chart data
  const barData = category_breakdown.map((cat) => ({
    name: RFI_CATEGORY_LABELS[cat.category as RFICategoryV2] ?? cat.category,
    response_pct: cat.response_pct,
    total: cat.total,
  }));

  return (
    <div className="flex flex-col gap-5">
      {/* ── KPI Cards ────────────────────────────────── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard
          label="총 질의"
          value={String(data.total_items)}
          variant="default"
          icon={ClipboardList}
        />
        <KpiCard
          label="미답변"
          value={String(status_counts["OPEN"] ?? 0)}
          variant="caution"
          icon={AlertCircle}
        />
        <KpiCard
          label="답변완료"
          value={String(status_counts["ANSWERED"] ?? 0)}
          variant="positive"
          icon={CheckCircle2}
        />
        <KpiCard
          label="마감"
          value={String(status_counts["CLOSED"] ?? 0)}
          variant="default"
          icon={Lock}
        />
      </div>

      {/* ── Charts ───────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Status Distribution Pie */}
        <Card title="상태별 분포" padding="md">
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={pieData}
                  cx="50%"
                  cy="50%"
                  innerRadius={50}
                  outerRadius={90}
                  dataKey="value"
                  paddingAngle={2}
                >
                  {pieData.map((entry) => (
                    <Cell key={entry.name} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip
                  formatter={(value, name) => [
                    `${value ?? 0}건`,
                    name ?? "",
                  ]}
                />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </Card>

        {/* Category Breakdown Bar */}
        <Card title="카테고리별 응답률" padding="md">
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={barData}
                layout="vertical"
                margin={{ left: 60, right: 20, top: 5, bottom: 5 }}
              >
                <XAxis
                  type="number"
                  domain={[0, 100]}
                  tickFormatter={(v: number) => `${v}%`}
                />
                <YAxis
                  type="category"
                  dataKey="name"
                  width={55}
                  tick={{ fontSize: 12 }}
                />
                <Tooltip
                  formatter={(value) => [`${value ?? 0}%`, "응답률"]}
                />
                <Bar
                  dataKey="response_pct"
                  fill="#10b981"
                  radius={[0, 4, 4, 0]}
                  barSize={16}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>

      {/* ── Aging Alerts ─────────────────────────────── */}
      {aging_items.length > 0 && (
        <Card title="장기 미답변 항목" padding="md" variant="default">
          <div className="flex flex-col gap-2">
            {aging_items.map((item) => {
              const days = daysSince(item.created_at);
              return (
                <div
                  key={item.id}
                  className="flex items-center justify-between rounded-dr border border-caution/30 bg-amber-50/30 px-4 py-3"
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <Clock className="h-4 w-4 shrink-0 text-caution" />
                    <span className="text-sm font-medium text-text-dark truncate">
                      {item.item_number}
                    </span>
                    <span className="text-sm text-text-secondary truncate">
                      {item.question_text}
                    </span>
                  </div>
                  <div className="flex items-center gap-2 shrink-0 ml-3">
                    <Badge variant="warning">
                      {days >= AGING_THRESHOLD_DAYS
                        ? `${days}일 경과`
                        : `${days}일`}
                    </Badge>
                    <Badge variant="neutral">
                      {RFI_CATEGORY_LABELS[item.category] ?? item.category}
                    </Badge>
                  </div>
                </div>
              );
            })}
          </div>
        </Card>
      )}
    </div>
  );
}

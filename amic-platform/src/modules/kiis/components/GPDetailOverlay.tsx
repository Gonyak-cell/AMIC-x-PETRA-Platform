import { useState } from "react";
import {
  Briefcase,
  PieChart as PieIcon,
  Users,
  Calendar,
  GraduationCap,
  ArrowUpRight,
  ArrowDownRight,
  Minus,
} from "lucide-react";
import { Badge, KpiCard, Tabs, Card } from "@/components/ui";
import type { TabItem } from "@/components/ui";
import type { GPResearchItem } from "@/modules/kiis/types/gpResearch";
import {
  SPONSOR_LABELS,
  SPONSOR_BADGE_VARIANT,
} from "@/modules/kiis/types/gpResearch";
import { ComboChart } from "./charts/ComboChart";
import { ScatterPlot } from "./charts/ScatterPlot";
import { GPLogo } from "./GPLogo";
import { DonutChart } from "./charts/DonutChart";

interface GPDetailOverlayProps {
  gp: GPResearchItem;
}

const DETAIL_TABS: TabItem[] = [
  { id: "track-record", label: "정량 실적", icon: Briefcase },
  { id: "portfolio", label: "포트폴리오", icon: PieIcon },
  { id: "people", label: "인력 및 평판", icon: Users },
];

const PORTFOLIO_STATUS_VARIANT: Record<string, "success" | "info" | "error"> = {
  active: "success",
  exited: "info",
  written_off: "error",
};

const PORTFOLIO_STATUS_LABEL: Record<string, string> = {
  active: "운용중",
  exited: "Exit",
  written_off: "손실",
};

function formatAum(value: number): string {
  if (value >= 10000) return `${(value / 10000).toFixed(1)}조`;
  return `${value.toLocaleString()}억`;
}

const SENTIMENT_ICON = {
  positive: <ArrowUpRight className="h-3.5 w-3.5 text-positive" />,
  negative: <ArrowDownRight className="h-3.5 w-3.5 text-negative" />,
  neutral: <Minus className="h-3.5 w-3.5 text-text-secondary" />,
};

export function GPDetailOverlay({ gp }: GPDetailOverlayProps) {
  const [activeTab, setActiveTab] = useState("track-record");

  return (
    <div className="space-y-6">
      {/* ── 헤더 영역 ── */}
      <div className="flex items-start gap-4">
        <GPLogo logoUrl={gp.logoUrl} name={gp.name} size="lg" />
        <div className="min-w-0 flex-1">
          <h3 className="text-xl font-heading font-bold text-text-dark">
            {gp.name}
          </h3>
          {gp.nameEn && (
            <p className="text-sm text-text-secondary">{gp.nameEn}</p>
          )}
          <div className="mt-1.5">
            <Badge variant={SPONSOR_BADGE_VARIANT[gp.sponsorType]} pill>
              {SPONSOR_LABELS[gp.sponsorType]}
            </Badge>
          </div>
        </div>
      </div>

      {/* ── KPI 위젯 ── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <KpiCard title="누적 AUM" value={formatAum(gp.cumAum)} />
        <KpiCard title="결성 펀드" value={`${gp.totalFundCount}개`} />
        <KpiCard
          title="포트폴리오 기업"
          value={`${gp.portfolioCompanyCount}개`}
        />
        <KpiCard
          title="추정 드라이파우더"
          value={formatAum(gp.estimatedDryPowder)}
        />
      </div>

      {/* ── 탭 ── */}
      <Tabs
        tabs={DETAIL_TABS}
        activeTab={activeTab}
        onTabChange={setActiveTab}
        variant="underline"
        size="sm"
      />

      {/* ── 탭 콘텐츠 ── */}
      {activeTab === "track-record" && (
        <div className="space-y-6">
          <Card title="연도별 펀드 결성액 & 누적 AUM" headerBar>
            <ComboChart data={gp.fundHistory} height={280} />
          </Card>
          <Card title="개별 펀드 Gross IRR" headerBar>
            <ScatterPlot data={gp.irrScatter} height={260} />
          </Card>
        </div>
      )}

      {activeTab === "portfolio" && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* 도넛 차트 */}
          <Card title="섹터별 투자 비중" headerBar>
            <DonutChart data={gp.sectorAllocation} height={280} />
          </Card>

          {/* 포트폴리오 기업 카드 */}
          <div className="space-y-3">
            <h4 className="text-sm font-semibold text-text-dark">
              주요 투자 기업
            </h4>
            {gp.portfolioCompanies.map((company) => (
              <Card key={company.name} variant="forest-lift" padding="sm">
                <div className="flex items-center justify-between">
                  <div className="min-w-0">
                    <p className="font-medium text-text-dark text-sm">
                      {company.name}
                    </p>
                    <p className="text-xs text-text-secondary">
                      {company.sector} · {company.investDate}
                    </p>
                    {company.coGPs.length > 0 && (
                      <p className="text-[11px] text-text-muted mt-0.5">
                        Co-GP: {company.coGPs.join(", ")}
                      </p>
                    )}
                  </div>
                  <div className="text-right shrink-0 ml-3">
                    <p className="font-mono text-sm font-medium tabular-nums">
                      {company.investAmount.toLocaleString()}억
                    </p>
                    <Badge
                      variant={PORTFOLIO_STATUS_VARIANT[company.status]}
                      pill
                    >
                      {PORTFOLIO_STATUS_LABEL[company.status]}
                    </Badge>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        </div>
      )}

      {activeTab === "people" && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Key-man 리스트 */}
          <div className="space-y-3">
            <h4 className="text-sm font-semibold text-text-dark">
              핵심 운용인력
            </h4>
            {gp.keyManList.map((person) => (
              <Card key={person.name} padding="sm">
                <div className="space-y-2">
                  <div className="flex items-center gap-3">
                    <div className="h-10 w-10 rounded-full bg-amic-100 flex items-center justify-center shrink-0">
                      <span className="text-sm font-bold text-amic">
                        {person.name.charAt(0)}
                      </span>
                    </div>
                    <div>
                      <p className="font-semibold text-text-dark text-sm">
                        {person.name}
                      </p>
                      <p className="text-xs text-text-secondary">
                        {person.title}
                      </p>
                    </div>
                  </div>
                  <div className="flex gap-4 text-xs text-text-secondary">
                    <span className="flex items-center gap-1">
                      <Calendar className="h-3 w-3" />
                      {person.yearsExperience}년 경력
                    </span>
                    <span className="flex items-center gap-1">
                      <GraduationCap className="h-3 w-3" />
                      {person.education}
                    </span>
                  </div>
                  {person.previousFirm && (
                    <p className="text-[11px] text-text-muted">
                      전직: {person.previousFirm}
                    </p>
                  )}
                  <div className="flex flex-wrap gap-1">
                    {person.trackRecord.map((tr) => (
                      <Badge key={tr} variant="neutral" pill>
                        {tr}
                      </Badge>
                    ))}
                  </div>
                </div>
              </Card>
            ))}
          </div>

          {/* 뉴스 타임라인 */}
          <div className="space-y-3">
            <h4 className="text-sm font-semibold text-text-dark">최신 뉴스</h4>
            <div className="relative pl-4 border-l-2 border-amic-100 space-y-4">
              {gp.newsTimeline.map((news, idx) => (
                <div key={idx} className="relative">
                  <div className="absolute -left-[21px] top-1.5 h-2.5 w-2.5 rounded-full bg-amic border-2 border-white" />
                  <div className="space-y-0.5">
                    <div className="flex items-center gap-2">
                      <span className="text-[11px] text-text-muted font-mono">
                        {news.date}
                      </span>
                      {SENTIMENT_ICON[news.sentiment]}
                    </div>
                    <p className="text-sm text-text-dark leading-snug">
                      {news.title}
                    </p>
                    <p className="text-[11px] text-text-secondary">
                      {news.source}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

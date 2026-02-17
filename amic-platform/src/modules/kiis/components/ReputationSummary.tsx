import { CheckCircle2, Newspaper } from "lucide-react";
import { Card, Spinner, EmptyState } from "@/components/ui";
import ThemeCard from "@/modules/kiis/components/ThemeCard";
import type { QualitativeReputationResponse } from "@/modules/kiis/types/analysis";

interface ReputationSummaryProps {
  data: QualitativeReputationResponse | undefined;
  isLoading: boolean;
}

export default function ReputationSummary({
  data,
  isLoading,
}: ReputationSummaryProps) {
  if (isLoading) {
    return (
      <Card title="업계 평판" headerBar>
        <Spinner />
      </Card>
    );
  }

  if (!data || data.total_articles === 0) {
    return (
      <Card title="업계 평판" headerBar>
        <EmptyState
          icon={Newspaper}
          title="분석 대상 없음"
          description="분석 대상 뉴스가 없습니다."
        />
      </Card>
    );
  }

  return (
    <Card title="업계 평판" headerBar>
      <div className="space-y-5">
        {/* Summary stats bar */}
        <div className="flex items-center gap-4 rounded-dr-sm bg-bg-cool px-4 py-3">
          <p className="text-sm text-text-secondary">
            최근 <span className="font-semibold text-text-dark">{data.months}개월</span>간
          </p>
          <div className="h-4 w-px bg-gray-border" />
          <div className="flex items-center gap-1.5">
            <span className="inline-block h-2 w-2 rounded-full bg-accent" />
            <span className="text-sm font-semibold text-accent">
              긍정 {data.positive_count}건
            </span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="inline-block h-2 w-2 rounded-full bg-negative" />
            <span className="text-sm font-semibold text-negative">
              부정 {data.negative_count}건
            </span>
          </div>
          <div className="h-4 w-px bg-gray-border" />
          <span className="text-xs text-text-muted font-mono">
            총 {data.total_articles}건 분석
          </span>
        </div>

        {/* Theme cards */}
        {data.themes.length > 0 && (
          <div className="space-y-3">
            {data.themes.map((theme) => (
              <ThemeCard key={theme.theme_code} theme={theme} />
            ))}
          </div>
        )}

        {/* Risk absences */}
        {data.risk_absences.length > 0 && (
          <div className="rounded-dr-sm border border-accent/20 bg-accent/5 px-4 py-3 space-y-1.5">
            <p className="text-xs font-semibold uppercase tracking-wider text-accent mb-2">
              리스크 부재 확인
            </p>
            {data.risk_absences.map((absence) => (
              <div
                key={absence}
                className="flex items-center gap-2.5 text-sm text-accent"
              >
                <div className="flex items-center justify-center h-5 w-5 rounded-full bg-accent/10 shrink-0">
                  <CheckCircle2 className="h-3 w-3" />
                </div>
                <span className="font-medium">{absence} 보도 없음</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </Card>
  );
}

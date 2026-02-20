import { ExternalLink } from "lucide-react";
import { Card, Badge, Spinner, EmptyState } from "@/components/ui";
import { BarChart3 } from "lucide-react";
import type {
  TendencySummaryResponse,
  TendencyDealItem,
} from "@/modules/kiis/types/deal";

/* ─── Deal list row ─── */

function DealRow({ deal }: { deal: TendencyDealItem }) {
  return (
    <div className="flex items-center gap-2.5 text-sm py-1.5 px-2 -mx-2 rounded-dr-sm hover:bg-accent/5 transition-colors duration-150">
      <span className="text-accent shrink-0">&bull;</span>
      <span className="font-medium text-text-dark truncate">
        {deal.target_company}
      </span>
      {deal.amount_display && (
        <>
          <span className="text-gray-border">—</span>
          <span className="font-mono text-sm text-text-secondary">
            {deal.amount_display}
          </span>
        </>
      )}
      {deal.round_stage && (
        <>
          <span className="text-gray-border">&middot;</span>
          <Badge variant="neutral">{deal.round_stage}</Badge>
        </>
      )}
      {deal.deal_date && (
        <>
          <span className="text-gray-border">&middot;</span>
          <span className="text-xs text-text-muted">
            {deal.deal_date.slice(0, 7)}
          </span>
        </>
      )}
      {deal.source_url && (
        <a
          href={deal.source_url}
          target="_blank"
          rel="noopener noreferrer"
          className="shrink-0 text-accent hover:underline"
        >
          <ExternalLink className="h-3 w-3" />
        </a>
      )}
    </div>
  );
}

/* ─── Section card (shared for sector & stage) ─── */

function SectionCard({
  title,
  count,
  amountDisplay,
  percentage,
  description,
  deals,
}: {
  title: string;
  count: number;
  amountDisplay: string | null;
  percentage: number;
  description: string;
  deals: TendencyDealItem[];
}) {
  return (
    <div className="rounded-dr border border-gray-border bg-white shadow-dr-sm transition-all duration-200 hover:shadow-dr-md">
      {/* Header */}
      <div className="flex items-center justify-between gap-3 px-5 py-3.5">
        <span className="font-heading font-semibold text-text-dark">{title}</span>
        <div className="flex items-center gap-2.5 text-xs text-text-secondary">
          <span className="font-mono font-medium">{count}건</span>
          {amountDisplay && (
            <>
              <span className="text-gray-border">&middot;</span>
              <span className="font-mono font-medium">{amountDisplay}</span>
            </>
          )}
          <span className="text-gray-border">&middot;</span>
          <Badge variant="neutral">{percentage}%</Badge>
        </div>
      </div>

      {/* Percentage bar */}
      <div className="px-5 pb-1">
        <div className="h-1 w-full rounded-full bg-bg-cool overflow-hidden">
          <div
            className="h-full rounded-full bg-gradient-to-r from-amic-500 to-accent transition-all duration-500"
            style={{ width: `${Math.min(percentage, 100)}%` }}
          />
        </div>
      </div>

      {/* Description */}
      <div className="px-5 pb-3 pt-2">
        <p className="text-sm text-text-secondary leading-relaxed">{description}</p>
      </div>

      {/* Deals */}
      {deals.length > 0 && (
        <div className="border-t border-gray-border bg-bg-cool/50 px-5 py-2.5 rounded-b-dr">
          {deals.map((deal, idx) => (
            <DealRow key={`${deal.target_company}-${idx}`} deal={deal} />
          ))}
        </div>
      )}
    </div>
  );
}

/* ─── Main component ─── */

interface TendencySummaryProps {
  data: TendencySummaryResponse | undefined;
  isLoading: boolean;
}

export default function TendencySummary({
  data,
  isLoading,
}: TendencySummaryProps) {
  if (isLoading) {
    return (
      <Card title="투자 전략 분석" headerBar>
        <Spinner />
      </Card>
    );
  }

  if (!data || data.total_deals === 0) {
    return (
      <Card>
        <EmptyState
          icon={BarChart3}
          title="투자 실적 없음"
          description="분석 기간 내 투자 딜 데이터가 없습니다."
        />
      </Card>
    );
  }

  return (
    <Card title="투자 전략 분석" headerBar>
      <div className="space-y-6">
        {/* Summary texts */}
        <div className="rounded-dr-sm bg-bg-cool px-4 py-3 space-y-1.5">
          <p className="text-sm text-text-dark font-semibold">
            {data.sector_summary}
          </p>
          {data.stage_summary && (
            <p className="text-sm text-text-secondary">{data.stage_summary}</p>
          )}
          <p className="text-sm text-text-secondary">{data.summary_text}</p>
        </div>

        {/* Sectors */}
        {data.sectors.length > 0 && (
          <div className="space-y-3">
            <h4 className="text-xs font-semibold uppercase tracking-wider text-text-secondary flex items-center gap-2">
              <span className="inline-block w-1 h-3 bg-amic-500 rounded-full" />
              섹터별 투자 현황
            </h4>
            {data.sectors.map((sector) => (
              <SectionCard
                key={sector.sector}
                title={sector.sector_name}
                count={sector.deal_count}
                amountDisplay={sector.total_amount_display}
                percentage={sector.percentage}
                description={sector.description}
                deals={sector.deals}
              />
            ))}
          </div>
        )}

        {/* Stages */}
        {data.stages.length > 0 && (
          <div className="space-y-3">
            <h4 className="text-xs font-semibold uppercase tracking-wider text-text-secondary flex items-center gap-2">
              <span className="inline-block w-1 h-3 bg-accent rounded-full" />
              스테이지별 분포
            </h4>
            {data.stages.map((stage) => (
              <SectionCard
                key={stage.stage}
                title={stage.stage_name}
                count={stage.deal_count}
                amountDisplay={stage.total_amount_display}
                percentage={stage.percentage}
                description={stage.description}
                deals={stage.deals}
              />
            ))}
          </div>
        )}
      </div>
    </Card>
  );
}

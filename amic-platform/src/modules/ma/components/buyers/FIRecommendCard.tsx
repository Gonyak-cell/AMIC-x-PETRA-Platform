import {
  Building2,
  TrendingUp,
  Target,
  Star,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { Badge, Card } from "@/components/ui";
import { formatBillions } from "@/modules/ma/utils/format";
import type { FIRecommendation } from "@/modules/ma/types/pef_registry";

interface FIRecommendCardProps {
  rec: FIRecommendation;
  isSelected: boolean;
  isExisting: boolean;
  isExpanded: boolean;
  onToggleSelect: (gpName: string) => void;
  onToggleExpand: (gpName: string) => void;
}

export default function FIRecommendCard({
  rec,
  isSelected,
  isExisting,
  isExpanded,
  onToggleSelect,
  onToggleExpand,
}: FIRecommendCardProps) {
  return (
    <Card
      role="listitem"
      padding="sm"
      className={
        isSelected
          ? "ring-2 ring-accent-primary"
          : isExisting
            ? "bg-bg-muted"
            : ""
      }
    >
      <label className="flex items-center gap-3 cursor-pointer">
        <input
          type="checkbox"
          checked={isSelected}
          disabled={isExisting}
          onChange={() => !isExisting && onToggleSelect(rec.gp_name)}
          className="h-4 w-4 rounded border-border"
        />

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-medium text-sm">{rec.gp_name}</span>
            {rec.tier === 1 && (
              <Badge variant="success">
                <Star className="h-2.5 w-2.5 mr-0.5" aria-hidden="true" />
                Tier 1
              </Badge>
            )}
            {rec.tier === 2 && <Badge variant="info">Tier 2</Badge>}
            {isExisting && <Badge variant="neutral">추가됨</Badge>}
          </div>
          <div className="flex items-center gap-3 mt-0.5 text-xs text-text-muted">
            <span className="flex items-center gap-1">
              <Building2 className="h-3 w-3" aria-hidden="true" />
              펀드 {rec.fund_count}개
            </span>
            <span className="flex items-center gap-1">
              <Target className="h-3 w-3" aria-hidden="true" />
              최소 {formatBillions(rec.min_fund_size)}
            </span>
            <span className="flex items-center gap-1">
              <TrendingUp className="h-3 w-3" aria-hidden="true" />
              총약정 {formatBillions(rec.total_committed_sum)}
            </span>
          </div>

          {/* GP 프로필 요약 (UX-2) */}
          {rec.gp_profile && (
            <div className="flex flex-wrap gap-1 mt-1">
              {rec.gp_profile.portfolio_sectors?.slice(0, 4).map((sector) => (
                <span
                  key={sector}
                  className="inline-block rounded bg-bg-cool px-1.5 py-0.5 text-[10px] text-text-secondary"
                >
                  {sector}
                </span>
              ))}
              {rec.gp_profile.portfolio_sectors &&
                rec.gp_profile.portfolio_sectors.length > 4 && (
                  <span className="text-[10px] text-text-muted">
                    +{rec.gp_profile.portfolio_sectors.length - 4}
                  </span>
                )}
            </div>
          )}

          <p className="text-[11px] text-text-muted mt-1">{rec.match_reason}</p>
        </div>
      </label>

      {/* 매칭 펀드 상세 (UX-6) */}
      {rec.matching_funds.length > 0 && (
        <div className="mt-1 ml-7">
          <button
            type="button"
            className="flex items-center gap-1 text-[11px] text-text-muted hover:text-text-secondary"
            onClick={(e) => {
              e.preventDefault();
              onToggleExpand(rec.gp_name);
            }}
            aria-expanded={isExpanded}
          >
            {isExpanded ? (
              <ChevronUp className="h-3 w-3" />
            ) : (
              <ChevronDown className="h-3 w-3" />
            )}
            펀드 목록 {isExpanded ? "접기" : "펼치기"}
          </button>
          {isExpanded && (
            <ul className="mt-1 space-y-0.5">
              {rec.matching_funds.map((fund) => (
                <li
                  key={fund.id}
                  className="text-[11px] text-text-muted flex justify-between"
                >
                  <span className="truncate mr-2">{fund.pef_name}</span>
                  <span className="shrink-0 text-text-secondary">
                    {fund.total_committed_capital
                      ? formatBillions(fund.total_committed_capital)
                      : "—"}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </Card>
  );
}

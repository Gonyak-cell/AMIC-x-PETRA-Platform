import { ExternalLink } from "lucide-react";
import type { BadgeVariant } from "@/components/ui";
import { Badge } from "@/components/ui";
import { cn } from "@/lib/cn";
import { formatDate } from "@/lib/format";
import { IB_SOURCE_LABELS } from "@/modules/kiis/constants/ibInsights";
import SentimentIndicator from "./SentimentIndicator";
import type { IBArticleItem } from "@/modules/kiis/types/ibInsight";

interface IBArticleCardProps {
  article: IBArticleItem;
  badgeVariant: BadgeVariant;
  className?: string;
}

export default function IBArticleCard({
  article,
  badgeVariant,
  className,
}: IBArticleCardProps) {
  return (
    <div
      className={cn(
        "px-4 py-3 hover:bg-white-alt transition-colors",
        className,
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <a
            href={article.canonical_url}
            target="_blank"
            rel="noopener noreferrer"
            title={article.title}
            className="text-sm font-medium text-text-dark hover:text-accent transition-colors line-clamp-1 inline-flex items-center gap-1"
          >
            {article.title}
            <ExternalLink
              className="h-3 w-3 shrink-0 text-text-secondary"
              aria-hidden="true"
            />
            <span className="sr-only">(새 창에서 열림)</span>
          </a>
          {article.lead_text && (
            <p className="text-xs text-text-secondary mt-1 line-clamp-2">
              {article.lead_text}
            </p>
          )}
          <div className="flex items-center gap-2 mt-1.5">
            <span className="text-xs text-text-secondary">
              {IB_SOURCE_LABELS[article.source] ?? article.source}
            </span>
            <span className="text-xs text-text-secondary">&middot;</span>
            <span className="text-xs text-text-secondary">
              {article.published_at
                ? formatDate(article.published_at, "short")
                : "-"}
            </span>
            {article.is_paywalled && <Badge variant="warning">유료</Badge>}
          </div>
        </div>
        <div className="shrink-0 flex flex-col items-end gap-1">
          <Badge variant={badgeVariant}>{article.category_display}</Badge>
          <SentimentIndicator score={article.sentiment_score} />
        </div>
      </div>
    </div>
  );
}

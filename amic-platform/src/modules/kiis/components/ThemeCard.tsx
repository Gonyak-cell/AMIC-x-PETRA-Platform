import { useState } from "react";
import { ChevronDown, ChevronUp, ExternalLink, TrendingUp, TrendingDown } from "lucide-react";
import { Badge } from "@/components/ui";
import type { ReputationTheme } from "@/modules/kiis/types/analysis";

interface ThemeCardProps {
  theme: ReputationTheme;
}

export default function ThemeCard({ theme }: ThemeCardProps) {
  const [expanded, setExpanded] = useState(false);
  const isPositive = theme.sentiment === "positive";

  return (
    <div className="rounded-dr border border-gray-border bg-white shadow-dr-sm transition-all duration-200 hover:shadow-dr-md">
      {/* Sentiment accent bar */}
      <div
        className={`h-0.5 rounded-t-dr ${
          isPositive
            ? "bg-gradient-to-r from-accent to-accent/60"
            : "bg-gradient-to-r from-negative to-negative/60"
        }`}
      />

      {/* Header — clickable to expand/collapse */}
      <button
        type="button"
        onClick={() => setExpanded((prev) => !prev)}
        className="flex w-full items-center justify-between gap-3 px-5 py-3.5 text-left hover:bg-accent/5 transition-colors duration-200"
        aria-expanded={expanded}
      >
        <div className="flex items-center gap-2.5 min-w-0">
          {isPositive ? (
            <div className="flex items-center justify-center h-7 w-7 rounded-full bg-accent/10 shrink-0">
              <TrendingUp className="h-3.5 w-3.5 text-accent" />
            </div>
          ) : (
            <div className="flex items-center justify-center h-7 w-7 rounded-full bg-negative/10 shrink-0">
              <TrendingDown className="h-3.5 w-3.5 text-negative" />
            </div>
          )}
          <span className="font-heading font-semibold text-text-dark truncate">
            {theme.theme_name}
          </span>
        </div>

        <div className="flex items-center gap-2.5 shrink-0">
          <Badge variant={isPositive ? "success" : "error"}>
            {theme.article_count}건
          </Badge>
          <div className="flex items-center justify-center h-6 w-6 rounded-full bg-bg-cool transition-colors duration-200">
            {expanded ? (
              <ChevronUp className="h-3.5 w-3.5 text-text-secondary" />
            ) : (
              <ChevronDown className="h-3.5 w-3.5 text-text-secondary" />
            )}
          </div>
        </div>
      </button>

      {/* Description */}
      <div className="px-5 pb-3">
        <p className="text-sm text-text-secondary leading-relaxed">{theme.description}</p>
      </div>

      {/* Expanded article list */}
      {expanded && theme.articles.length > 0 && (
        <div className="border-t border-gray-border bg-bg-cool/50 px-5 py-3 space-y-2.5 rounded-b-dr">
          {theme.articles.map((article, idx) => (
            <div
              key={`${article.url}-${idx}`}
              className="flex items-start gap-2.5 text-sm"
            >
              <span
                className={`shrink-0 mt-0.5 ${
                  isPositive ? "text-accent" : "text-negative"
                }`}
              >
                {isPositive ? "↗" : "↘"}
              </span>
              <div className="min-w-0 flex-1">
                <p className="text-text-dark truncate font-medium">{article.title}</p>
                <div className="flex items-center gap-2 text-xs text-text-secondary mt-1">
                  <span className="font-medium">{article.source}</span>
                  {article.published_at && (
                    <>
                      <span className="text-gray-border">|</span>
                      <span>
                        {new Date(article.published_at).toLocaleDateString(
                          "ko-KR",
                        )}
                      </span>
                    </>
                  )}
                  <a
                    href={article.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-0.5 text-accent hover:underline font-medium"
                    onClick={(e) => e.stopPropagation()}
                  >
                    원문
                    <ExternalLink className="h-3 w-3" />
                  </a>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

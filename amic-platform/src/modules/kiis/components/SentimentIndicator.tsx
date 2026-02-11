import type { SentimentType } from "@/modules/kiis/types/news";
import { cn } from "@/lib/cn";

interface SentimentIndicatorProps {
  sentiment: SentimentType | null;
  score?: number | null;
  className?: string;
}

const SENTIMENT_STYLES: Record<SentimentType, string> = {
  positive: "text-positive bg-bg-light-green/40",
  neutral: "text-text-secondary bg-gray-100",
  negative: "text-negative bg-red-50",
};

const SENTIMENT_LABELS: Record<SentimentType, string> = {
  positive: "Positive",
  neutral: "Neutral",
  negative: "Negative",
};

export default function SentimentIndicator({
  sentiment,
  score,
  className,
}: SentimentIndicatorProps) {
  if (!sentiment) return <span className="text-text-secondary text-xs">-</span>;

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium",
        SENTIMENT_STYLES[sentiment],
        className,
      )}
    >
      {SENTIMENT_LABELS[sentiment]}
      {score != null && (
        <span className="font-mono text-[10px]">
          ({(score * 100).toFixed(0)}%)
        </span>
      )}
    </span>
  );
}

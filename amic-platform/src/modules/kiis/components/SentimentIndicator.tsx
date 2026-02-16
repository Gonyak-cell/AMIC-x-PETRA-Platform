import { cn } from "@/lib/cn";

type SentimentType = "positive" | "neutral" | "negative";

interface SentimentIndicatorProps {
  score: number | null;
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

function deriveSentiment(score: number): SentimentType {
  if (score > 0) return "positive";
  if (score < 0) return "negative";
  return "neutral";
}

export default function SentimentIndicator({
  score,
  className,
}: SentimentIndicatorProps) {
  if (score == null) return <span className="text-text-secondary text-xs">-</span>;

  const sentiment = deriveSentiment(score);

  return (
    <span
      role="status"
      aria-label={`Sentiment: ${SENTIMENT_LABELS[sentiment]} (${(score * 100).toFixed(0)}%)`}
      className={cn(
        "inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium",
        SENTIMENT_STYLES[sentiment],
        className,
      )}
    >
      {SENTIMENT_LABELS[sentiment]}
      <span className="font-mono text-[10px]">
        ({(score * 100).toFixed(0)}%)
      </span>
    </span>
  );
}

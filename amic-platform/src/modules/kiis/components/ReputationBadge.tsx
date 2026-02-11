import type { StatusTag } from "@/modules/kiis/types/analysis";
import { cn } from "@/lib/cn";

interface ReputationBadgeProps {
  score: number;
  statusTag?: StatusTag;
  showTag?: boolean;
  className?: string;
}

function getScoreColor(score: number): string {
  if (score >= 80) return "text-positive bg-bg-light-green/40";
  if (score >= 60) return "text-blue-700 bg-blue-50";
  if (score >= 40) return "text-caution bg-amber-50";
  return "text-negative bg-red-50";
}

const TAG_LABELS: Record<StatusTag, string> = {
  rising: "Rising",
  stable: "Stable",
  risk: "Risk",
};

const TAG_STYLES: Record<StatusTag, string> = {
  rising: "text-positive",
  stable: "text-blue-700",
  risk: "text-negative",
};

export default function ReputationBadge({
  score,
  statusTag,
  showTag = true,
  className,
}: ReputationBadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-semibold font-mono",
        getScoreColor(score),
        className,
      )}
    >
      {score.toFixed(0)}
      {showTag && statusTag && (
        <span className={cn("text-[10px] font-normal", TAG_STYLES[statusTag])}>
          {TAG_LABELS[statusTag]}
        </span>
      )}
    </span>
  );
}

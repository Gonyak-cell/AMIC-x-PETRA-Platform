import { IB_OPINION_BADGE_VARIANT } from "@/modules/kiis/constants/ibInsights";
import IBArticleCard from "./IBArticleCard";
import type { IBArticleItem } from "@/modules/kiis/types/ibInsight";

interface IBOpinionCardProps {
  article: IBArticleItem;
  className?: string;
}

export default function IBOpinionCard({
  article,
  className,
}: IBOpinionCardProps) {
  const badgeVariant =
    IB_OPINION_BADGE_VARIANT[article.category ?? ""] ?? "neutral";

  return (
    <IBArticleCard
      article={article}
      badgeVariant={badgeVariant}
      className={className}
    />
  );
}

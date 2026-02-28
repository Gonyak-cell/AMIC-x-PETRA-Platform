import IBArticleCard from "./IBArticleCard";
import type { IBArticleItem } from "@/modules/kiis/types/ibInsight";

interface IBFactCardProps {
  article: IBArticleItem;
  className?: string;
}

export default function IBFactCard({ article, className }: IBFactCardProps) {
  return (
    <IBArticleCard
      article={article}
      badgeVariant="info"
      className={className}
    />
  );
}

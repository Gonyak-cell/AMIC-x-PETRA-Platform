import { Star } from "lucide-react";
import { cn } from "@/lib/cn";
import { useFavorites } from "@/hooks/useFavorites";
import type { FavoriteType } from "@/types/favorite";

interface FavoriteButtonProps {
  id: string;
  type: FavoriteType;
  name: string;
  path: string;
  className?: string;
}

export function FavoriteButton({
  id,
  type,
  name,
  path,
  className,
}: FavoriteButtonProps) {
  const { isFavorite, toggleFavorite } = useFavorites();
  const favorited = isFavorite(id);

  return (
    <button
      onClick={(e) => {
        e.stopPropagation();
        toggleFavorite({ id, type, name, path });
      }}
      className={cn(
        "p-1.5 rounded-lg transition-colors",
        favorited
          ? "text-amber-500 hover:text-amber-600"
          : "text-text-secondary hover:text-amber-500",
        className,
      )}
      aria-label={favorited ? `Remove ${name} from favorites` : `Add ${name} to favorites`}
      aria-pressed={favorited}
    >
      <Star
        className="h-4 w-4"
        fill={favorited ? "currentColor" : "none"}
      />
    </button>
  );
}

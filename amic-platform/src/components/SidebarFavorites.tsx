import { NavLink } from "react-router-dom";
import { Star, Clock, Briefcase, Building2, FileText } from "lucide-react";
import { cn } from "@/lib/cn";
import { useFavorites } from "@/hooks/useFavorites";
import { useRecentItems } from "@/hooks/useRecentItems";
import type { FavoriteType } from "@/types/favorite";

const TYPE_ICONS: Record<FavoriteType, typeof Briefcase> = {
  deal: Briefcase,
  company: Building2,
  "im-project": FileText,
};

interface SidebarFavoritesProps {
  onNavItemClick?: () => void;
}

export function SidebarFavorites({ onNavItemClick }: SidebarFavoritesProps) {
  const { favorites } = useFavorites();
  const { recentItems } = useRecentItems();

  const topFavorites = favorites.slice(0, 5);
  const topRecent = recentItems.slice(0, 3);

  if (topFavorites.length === 0 && topRecent.length === 0) return null;

  return (
    <div className="mt-4 border-t border-white/10 pt-2">
      {/* Favorites */}
      {topFavorites.length > 0 && (
        <div>
          <h3
            id="sidebar-section-favorites"
            className="px-4 mb-2 mt-2 text-xs font-semibold text-white/40 uppercase tracking-wider flex items-center gap-1.5"
          >
            <Star className="h-3 w-3" />
            Favorites
          </h3>
          <nav
            className="space-y-0.5"
            aria-labelledby="sidebar-section-favorites"
          >
            {topFavorites.map((item) => {
              const Icon = TYPE_ICONS[item.type];
              return (
                <NavLink
                  key={item.id}
                  to={item.path}
                  onClick={onNavItemClick}
                  className={({ isActive }) =>
                    cn(
                      "flex items-center gap-3 px-4 py-2 text-sm rounded-lg transition-colors",
                      isActive
                        ? "bg-white/10 text-white"
                        : "text-white/70 hover:bg-white/5 hover:text-white",
                    )
                  }
                >
                  <Icon className="h-4 w-4 flex-shrink-0" aria-hidden="true" />
                  <span className="truncate">{item.name}</span>
                </NavLink>
              );
            })}
          </nav>
        </div>
      )}

      {/* Recent */}
      {topRecent.length > 0 && (
        <div>
          <h3
            id="sidebar-section-recent"
            className="px-4 mb-2 mt-3 text-xs font-semibold text-white/40 uppercase tracking-wider flex items-center gap-1.5"
          >
            <Clock className="h-3 w-3" />
            Recent
          </h3>
          <nav
            className="space-y-0.5"
            aria-labelledby="sidebar-section-recent"
          >
            {topRecent.map((item) => {
              const Icon = TYPE_ICONS[item.type];
              return (
                <NavLink
                  key={item.id}
                  to={item.path}
                  onClick={onNavItemClick}
                  className={({ isActive }) =>
                    cn(
                      "flex items-center gap-3 px-4 py-2 text-sm rounded-lg transition-colors",
                      isActive
                        ? "bg-white/10 text-white"
                        : "text-white/60 hover:bg-white/5 hover:text-white",
                    )
                  }
                >
                  <Icon className="h-4 w-4 flex-shrink-0" aria-hidden="true" />
                  <span className="truncate">{item.name}</span>
                </NavLink>
              );
            })}
          </nav>
        </div>
      )}
    </div>
  );
}

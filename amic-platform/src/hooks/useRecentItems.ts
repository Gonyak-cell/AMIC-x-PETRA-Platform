import { useState, useCallback } from "react";
import { getItem, setItem } from "@/lib/storage";
import type { RecentItem, FavoriteType } from "@/types/favorite";

const RECENT_KEY = "recent_items";
const MAX_RECENT = 10;

export function useRecentItems() {
  const [recentItems, setRecentItems] = useState<RecentItem[]>(() =>
    getItem<RecentItem[]>(RECENT_KEY, []),
  );

  const trackVisit = useCallback(
    (item: { id: string; type: FavoriteType; name: string; path: string }) => {
      setRecentItems((prev) => {
        const filtered = prev.filter((r) => r.id !== item.id);
        const next = [
          { ...item, visitedAt: new Date().toISOString() },
          ...filtered,
        ].slice(0, MAX_RECENT);
        setItem(RECENT_KEY, next);
        return next;
      });
    },
    [],
  );

  return { recentItems, trackVisit };
}

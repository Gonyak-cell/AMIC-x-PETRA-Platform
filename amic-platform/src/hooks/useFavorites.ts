import { useState, useCallback } from "react";
import { getItem, setItem } from "@/lib/storage";
import type { FavoriteItem, FavoriteType } from "@/types/favorite";

const FAVORITES_KEY = "favorites";

export function useFavorites() {
  const [favorites, setFavorites] = useState<FavoriteItem[]>(() =>
    getItem<FavoriteItem[]>(FAVORITES_KEY, []),
  );

  const isFavorite = useCallback(
    (id: string): boolean => favorites.some((f) => f.id === id),
    [favorites],
  );

  const toggleFavorite = useCallback(
    (item: { id: string; type: FavoriteType; name: string; path: string }) => {
      setFavorites((prev) => {
        const exists = prev.some((f) => f.id === item.id);
        const next = exists
          ? prev.filter((f) => f.id !== item.id)
          : [...prev, { ...item, addedAt: new Date().toISOString() }];
        setItem(FAVORITES_KEY, next);
        return next;
      });
    },
    [],
  );

  return { favorites, toggleFavorite, isFavorite };
}

import { useState, useCallback } from "react";
import { getItem, setItem } from "@/lib/storage";
import type { UserPreferences } from "@/types/settings";

const PREFS_KEY = "preferences";

const DEFAULT_PREFERENCES: UserPreferences = {
  defaultModule: "/",
  dateFormat: "short",
};

export function usePreferences() {
  const [preferences, setPreferences] = useState<UserPreferences>(() =>
    getItem<UserPreferences>(PREFS_KEY, DEFAULT_PREFERENCES),
  );

  const updatePreferences = useCallback(
    (updates: Partial<UserPreferences>) => {
      setPreferences((prev) => {
        const next = { ...prev, ...updates };
        setItem(PREFS_KEY, next);
        return next;
      });
    },
    [],
  );

  return { preferences, updatePreferences };
}

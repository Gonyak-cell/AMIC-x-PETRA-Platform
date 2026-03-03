import { useState, useCallback, useEffect } from "react";
import { getItem, setItem } from "@/lib/storage";
import type { SidebarTheme, SidebarAppearance } from "@/types/settings";

// ── AMIC 브랜드 기반 CSS variable maps ──

const SIDEBAR_THEME_VARS: Record<SidebarTheme, Record<string, string>> = {
  AMIC_FOREST: {
    "--sidebar-bg-start": "#07201C",
    "--sidebar-bg-mid": "#0F3A32",
    "--sidebar-bg-end": "#0B2D27",
    "--sidebar-text": "#FFFFFF",
    "--sidebar-text-muted": "rgba(255,255,255,0.6)",
    "--sidebar-accent": "#26C260",
    "--sidebar-accent-glow": "rgba(38,194,96,0.4)",
    "--sidebar-active-bg": "rgba(255,255,255,0.08)",
    "--sidebar-hover-bg": "rgba(255,255,255,0.07)",
    "--sidebar-divider": "rgba(255,255,255,0.1)",
    "--sidebar-logo-bg": "#FFFFFF",
    "--sidebar-backdrop": "none",
  },
  AMIC_DEEP: {
    "--sidebar-bg-start": "#041210",
    "--sidebar-bg-mid": "#07201C",
    "--sidebar-bg-end": "#0F3A32",
    "--sidebar-text": "#F0FDF4",
    "--sidebar-text-muted": "rgba(240,253,244,0.45)",
    "--sidebar-accent": "#34D399",
    "--sidebar-accent-glow": "rgba(52,211,153,0.4)",
    "--sidebar-active-bg": "rgba(52,211,153,0.12)",
    "--sidebar-hover-bg": "rgba(52,211,153,0.08)",
    "--sidebar-divider": "rgba(52,211,153,0.15)",
    "--sidebar-logo-bg": "#041210",
    "--sidebar-backdrop": "none",
  },
  AMIC_GLASS: {
    "--sidebar-bg-start": "rgba(15,58,50,0.85)",
    "--sidebar-bg-mid": "rgba(15,58,50,0.75)",
    "--sidebar-bg-end": "rgba(15,58,50,0.65)",
    "--sidebar-text": "#FFFFFF",
    "--sidebar-text-muted": "rgba(255,255,255,0.5)",
    "--sidebar-accent": "#26C260",
    "--sidebar-accent-glow": "rgba(38,194,96,0.5)",
    "--sidebar-active-bg": "rgba(255,255,255,0.12)",
    "--sidebar-hover-bg": "rgba(255,255,255,0.1)",
    "--sidebar-divider": "rgba(255,255,255,0.15)",
    "--sidebar-logo-bg": "rgba(255,255,255,0.08)",
    "--sidebar-backdrop": "blur(12px)",
  },
};

// ── Helpers ──

/** Hex (#RRGGBB) → rgba glow 문자열 (alpha=0.4). 잘못된 형식이면 기본 green glow 반환 */
function hexToRgbaGlow(hex: string): string {
  if (!/^#[0-9A-Fa-f]{6}$/.test(hex)) {
    return "rgba(38,194,96,0.4)";
  }
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  return `rgba(${r},${g},${b},0.4)`;
}

/** localStorage에서 읽은 데이터가 유효한 SidebarAppearance인지 런타임 검증 */
function isValidAppearance(val: unknown): val is SidebarAppearance {
  if (typeof val !== "object" || val === null) return false;
  const obj = val as Record<string, unknown>;
  return (
    typeof obj.sidebarTheme === "string" &&
    obj.sidebarTheme in SIDEBAR_THEME_VARS &&
    typeof obj.sidebarAccentColor === "string" &&
    typeof obj.sidebarLayout === "string"
  );
}

// ── Constants ──

const PREFS_KEY = "sidebar_appearance";

const DEFAULT_APPEARANCE: SidebarAppearance = {
  sidebarTheme: "AMIC_FOREST",
  sidebarAccentColor: "#26C260",
  sidebarLayout: "COMPACT",
};

// ── Hook ──

export function useSidebarAppearance() {
  const [appearance, setAppearance] = useState<SidebarAppearance>(() => {
    const stored = getItem<unknown>(PREFS_KEY, null);
    return isValidAppearance(stored) ? stored : DEFAULT_APPEARANCE;
  });

  // Apply CSS variables to :root whenever appearance changes
  useEffect(() => {
    const vars =
      SIDEBAR_THEME_VARS[appearance.sidebarTheme] ??
      SIDEBAR_THEME_VARS.AMIC_FOREST;
    const root = document.documentElement;

    for (const [key, value] of Object.entries(vars)) {
      root.style.setProperty(key, value);
    }

    // Override accent color if custom
    if (appearance.sidebarAccentColor) {
      root.style.setProperty("--sidebar-accent", appearance.sidebarAccentColor);
      root.style.setProperty(
        "--sidebar-accent-glow",
        hexToRgbaGlow(appearance.sidebarAccentColor),
      );
    }
  }, [appearance]);

  const updateAppearance = useCallback(
    (updates: Partial<SidebarAppearance>) => {
      setAppearance((prev) => {
        const next = { ...prev, ...updates };
        setItem(PREFS_KEY, next);
        return next;
      });
    },
    [],
  );

  return { appearance, updateAppearance } as const;
}

// Re-export for convenience
export { SIDEBAR_THEME_VARS };
export { DEFAULT_APPEARANCE as SIDEBAR_DEFAULTS };

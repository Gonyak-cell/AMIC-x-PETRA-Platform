import { createContext, useContext, useEffect, type ReactNode } from "react";

import {
  usePlatformSettings,
  type TableStyleTheme,
} from "@/hooks/usePlatformSettings";

interface PlatformSettingsContextValue {
  tableStyle: TableStyleTheme;
  isLoading: boolean;
}

const PlatformSettingsContext = createContext<PlatformSettingsContextValue>({
  tableStyle: "DEFAULT",
  isLoading: true,
});

const CSS_VARS: Record<TableStyleTheme, Record<string, string>> = {
  DEFAULT: {
    "--table-header-bg": "#0F3A32",
    "--table-header-text": "#FFFFFF",
    "--table-header-font-weight": "600",
    "--table-row-border": "1px solid #E5E7EB",
    "--table-row-border-last": "1px solid #E5E7EB",
    "--table-row-hover": "rgba(16,185,129,0.05)",
    "--table-summary-color": "#0F3A32",
    "--table-stripe-bg": "#F7F8FA",
    "--table-footer-bg": "#EDF5F3",
    "--table-section-bg": "#0F3A32",
  },
  MODERN_GREEN: {
    "--table-header-bg": "#26C260",
    "--table-header-text": "#FFFFFF",
    "--table-header-font-weight": "700",
    "--table-row-border": "1px solid #CCCCCC",
    "--table-row-border-last": "1px solid #CCCCCC",
    "--table-row-hover": "rgba(38,194,96,0.05)",
    "--table-summary-color": "#26C260",
    "--table-stripe-bg": "transparent",
    "--table-footer-bg": "rgba(38,194,96,0.08)",
    "--table-section-bg": "#26C260",
  },
};

export function PlatformSettingsProvider({
  children,
}: {
  children: ReactNode;
}) {
  const { data, isLoading } = usePlatformSettings();
  const tableStyle: TableStyleTheme = data?.table_style ?? "DEFAULT";

  useEffect(() => {
    const vars = CSS_VARS[tableStyle] ?? CSS_VARS.DEFAULT;
    const root = document.documentElement;
    for (const [key, value] of Object.entries(vars)) {
      root.style.setProperty(key, value);
    }
  }, [tableStyle]);

  return (
    <PlatformSettingsContext.Provider value={{ tableStyle, isLoading }}>
      {children}
    </PlatformSettingsContext.Provider>
  );
}

// eslint-disable-next-line react-refresh/only-export-components
export function usePlatformSettingsContext() {
  return useContext(PlatformSettingsContext);
}

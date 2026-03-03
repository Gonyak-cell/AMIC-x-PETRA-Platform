import { useCallback, useState } from "react";
import type { KeyboardEvent } from "react";
import { Check, Paintbrush } from "lucide-react";

import { cn } from "@/lib/cn";
import { PageHero } from "@/components/ui";
import {
  usePlatformSettings,
  useUpdatePlatformSettings,
  type TableStyleTheme,
} from "@/hooks/usePlatformSettings";
import {
  useSidebarAppearance,
  SIDEBAR_THEME_VARS,
} from "@/hooks/useSidebarAppearance";
import type { SidebarTheme, SidebarLayout } from "@/types/settings";

const THEME_OPTIONS: {
  value: TableStyleTheme;
  label: string;
  description: string;
  preview: { headerBg: string; headerText: string; borderStyle: string };
}[] = [
  {
    value: "DEFAULT",
    label: "Default (AMIC Forest)",
    description: "진한 녹색 헤더, 실선 구분, 줄무늬 배경",
    preview: {
      headerBg: "#0F3A32",
      headerText: "#FFFFFF",
      borderStyle: "1px solid #E5E7EB",
    },
  },
  {
    value: "MODERN_GREEN",
    label: "Modern Green",
    description: "연녹색 헤더, 점선 구분, 깔끔한 배경",
    preview: {
      headerBg: "#26C260",
      headerText: "#FFFFFF",
      borderStyle: "1px dashed #CCCCCC",
    },
  },
];

// ── Sidebar theme presets ──

const SIDEBAR_THEME_PRESETS: Array<{
  key: SidebarTheme;
  label: string;
  description: string;
}> = [
  {
    key: "AMIC_FOREST",
    label: "AMIC Forest",
    description: "클래식 Forest Green 그라디언트",
  },
  {
    key: "AMIC_DEEP",
    label: "AMIC Deep",
    description: "더 깊고 어두운 Forest 변형",
  },
  {
    key: "AMIC_GLASS",
    label: "AMIC Glass",
    description: "글래스모피즘 반투명 스타일",
  },
];

const SIDEBAR_ACCENT_COLORS = [
  { hex: "#26C260", label: "AMIC Green" },
  { hex: "#34D399", label: "Emerald" },
  { hex: "#10B981", label: "Emerald 500" },
  { hex: "#059669", label: "Emerald 600" },
  { hex: "#14B8A6", label: "Teal" },
  { hex: "#22D3EE", label: "Cyan" },
];

const SIDEBAR_LAYOUT_OPTIONS: Array<{
  key: SidebarLayout;
  label: string;
  description: string;
}> = [
  {
    key: "COMPACT",
    label: "Compact",
    description: "아이콘 + 텍스트 수평 배치",
  },
  {
    key: "EXPANDED",
    label: "Iconic",
    description: "큰 아이콘 + 텍스트 수직 배치",
  },
];

// ── Mini sidebar preview ──

function MiniSidebarPreview({
  theme,
  accentColor,
}: {
  theme: SidebarTheme;
  accentColor: string;
}) {
  const vars = SIDEBAR_THEME_VARS[theme];
  const bgStart = vars["--sidebar-bg-start"];
  const bgMid = vars["--sidebar-bg-mid"];
  const bgEnd = vars["--sidebar-bg-end"];
  const divider = vars["--sidebar-divider"];
  const logoBg = vars["--sidebar-logo-bg"];

  return (
    <div
      className="w-full h-full rounded-lg overflow-hidden"
      style={{
        background: `linear-gradient(to bottom, ${bgStart}, ${bgMid}, ${bgEnd})`,
        backdropFilter: theme === "AMIC_GLASS" ? "blur(12px)" : undefined,
      }}
    >
      <div
        className="h-6 mx-2 mt-2 rounded-sm"
        style={{ backgroundColor: logoBg }}
      />
      <div className="h-px mx-2 my-2" style={{ backgroundColor: divider }} />
      <div className="space-y-1.5 px-2">
        <div
          className="h-4 rounded-sm"
          style={{ backgroundColor: "rgba(255,255,255,0.06)" }}
        />
        <div
          className="h-4 rounded-sm"
          style={{ backgroundColor: accentColor, opacity: 0.2 }}
        />
        <div
          className="h-4 rounded-sm"
          style={{ backgroundColor: "rgba(255,255,255,0.06)" }}
        />
        <div
          className="h-4 rounded-sm"
          style={{ backgroundColor: "rgba(255,255,255,0.06)" }}
        />
      </div>
      <div className="relative -mt-[54px] ml-[calc(100%-4px)]">
        <div
          className="w-[3px] h-4 rounded-l-full"
          style={{ backgroundColor: accentColor }}
        />
      </div>
    </div>
  );
}

const SAMPLE_DATA = [
  { name: "삼성전자", sector: "반도체", revenue: "302.2조" },
  { name: "SK하이닉스", sector: "반도체", revenue: "66.3조" },
  { name: "LG에너지솔루션", sector: "배터리", revenue: "33.7조" },
];

const TABS = [
  { key: "theme", label: "테마 & 외관" },
  { key: "general", label: "일반 정보" },
  { key: "legal", label: "법률 & 개인정보" },
] as const;

type TabKey = (typeof TABS)[number]["key"];

function ThemePreviewTable({
  headerBg,
  headerText,
  borderStyle,
}: {
  headerBg: string;
  headerText: string;
  borderStyle: string;
}) {
  return (
    <div className="mt-2 overflow-hidden rounded-lg border border-slate-200">
      <table className="w-full text-sm">
        <thead>
          <tr style={{ background: headerBg }}>
            <th
              className="px-3 py-2 text-left font-semibold"
              style={{ color: headerText }}
            >
              기업명
            </th>
            <th
              className="px-3 py-2 text-left font-semibold"
              style={{ color: headerText }}
            >
              업종
            </th>
            <th
              className="px-3 py-2 text-right font-semibold"
              style={{ color: headerText }}
            >
              매출액
            </th>
          </tr>
        </thead>
        <tbody>
          {SAMPLE_DATA.map((row) => (
            <tr key={row.name} style={{ borderBottom: borderStyle }}>
              <td className="px-3 py-2 font-medium text-slate-800">
                {row.name}
              </td>
              <td className="px-3 py-2 text-slate-600">{row.sector}</td>
              <td className="px-3 py-2 text-right tabular-nums text-slate-700">
                {row.revenue}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function AdminSettingsPage() {
  const { data: settings, isLoading } = usePlatformSettings();
  const updateMutation = useUpdatePlatformSettings();
  const [selectedTheme, setSelectedTheme] = useState<TableStyleTheme | null>(
    null,
  );
  const [activeTab, setActiveTab] = useState<TabKey>("theme");
  const { appearance, updateAppearance } = useSidebarAppearance();

  const currentTheme = selectedTheme ?? settings?.table_style ?? "DEFAULT";
  const isDirty =
    selectedTheme !== null && selectedTheme !== settings?.table_style;

  const handleTabKeyDown = useCallback(
    (e: KeyboardEvent<HTMLButtonElement>) => {
      const idx = TABS.findIndex((t) => t.key === activeTab);
      let next = idx;
      if (e.key === "ArrowRight") {
        next = (idx + 1) % TABS.length;
      } else if (e.key === "ArrowLeft") {
        next = idx === 0 ? TABS.length - 1 : idx - 1;
      } else {
        return;
      }
      e.preventDefault();
      setActiveTab(TABS[next].key);
      (e.currentTarget.parentElement?.children[next] as HTMLElement)?.focus();
    },
    [activeTab],
  );

  const handleSave = () => {
    if (!isDirty) return;
    updateMutation.mutate(
      { table_style: currentTheme },
      { onSuccess: () => setSelectedTheme(null) },
    );
  };

  return (
    <div>
      <PageHero
        title="플랫폼 설정"
        subtitle="전역 테마, 일반 정보, 법률/개인정보 정책을 관리합니다."
        compact
      />

      <div className="mx-auto max-w-4xl px-6 py-8">
        {/* 탭 내비게이션 */}
        <div
          className="mb-8 flex gap-1 rounded-lg bg-slate-100 p-1"
          role="tablist"
          aria-label="설정 카테고리"
        >
          {TABS.map((tab) => (
            <button
              key={tab.key}
              type="button"
              role="tab"
              aria-selected={activeTab === tab.key}
              aria-controls={`panel-${tab.key}`}
              tabIndex={activeTab === tab.key ? 0 : -1}
              onClick={() => setActiveTab(tab.key)}
              onKeyDown={handleTabKeyDown}
              className={cn(
                "flex-1 rounded-md px-4 py-2 text-sm font-medium transition-colors",
                "focus:outline-none focus:ring-2 focus:ring-inset focus:ring-accent",
                activeTab === tab.key
                  ? "bg-white text-slate-900 shadow-sm"
                  : "text-slate-500 hover:text-slate-700",
              )}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* 탭 컨텐츠 */}
        {activeTab === "theme" && (
          <div id="panel-theme" role="tabpanel" className="space-y-6">
            <div>
              <h2 className="text-lg font-semibold text-slate-900">
                테이블 스타일
              </h2>
              <p className="mt-1 text-sm text-slate-500">
                플랫폼 전체 DataTable 및 Excel 내보내기에 적용됩니다.
              </p>
            </div>

            {isLoading ? (
              <div className="space-y-4">
                <div className="h-48 animate-pulse rounded-lg bg-slate-100" />
                <div className="h-48 animate-pulse rounded-lg bg-slate-100" />
              </div>
            ) : (
              <div className="space-y-4">
                {THEME_OPTIONS.map((option) => {
                  const isSelected = currentTheme === option.value;
                  return (
                    <button
                      key={option.value}
                      type="button"
                      onClick={() => setSelectedTheme(option.value)}
                      className={cn(
                        "w-full rounded-xl border-2 p-5 text-left transition-all",
                        isSelected
                          ? "border-emerald-500 bg-emerald-50/50 ring-1 ring-emerald-500/20"
                          : "border-slate-200 hover:border-slate-300",
                      )}
                    >
                      <div className="flex items-center justify-between">
                        <div>
                          <div className="flex items-center gap-2">
                            <div
                              className={cn(
                                "h-4 w-4 rounded-full border-2",
                                isSelected
                                  ? "border-emerald-500 bg-emerald-500"
                                  : "border-slate-300",
                              )}
                            >
                              {isSelected && (
                                <svg
                                  className="h-full w-full text-white"
                                  viewBox="0 0 16 16"
                                  fill="currentColor"
                                >
                                  <path d="M12.207 4.793a1 1 0 010 1.414l-5 5a1 1 0 01-1.414 0l-2-2a1 1 0 011.414-1.414L6.5 9.086l4.293-4.293a1 1 0 011.414 0z" />
                                </svg>
                              )}
                            </div>
                            <span className="text-sm font-semibold text-slate-900">
                              {option.label}
                            </span>
                          </div>
                          <p className="ml-6 mt-0.5 text-xs text-slate-500">
                            {option.description}
                          </p>
                        </div>
                      </div>
                      <div className="ml-6">
                        <ThemePreviewTable {...option.preview} />
                      </div>
                    </button>
                  );
                })}
              </div>
            )}

            {/* 저장 버튼 */}
            <div className="flex justify-end pt-4">
              <button
                type="button"
                onClick={handleSave}
                disabled={!isDirty || updateMutation.isPending}
                className={cn(
                  "rounded-lg px-6 py-2.5 text-sm font-semibold text-white transition-colors",
                  updateMutation.isError && isDirty
                    ? "bg-red-600 hover:bg-red-700"
                    : isDirty
                      ? "bg-emerald-600 hover:bg-emerald-700"
                      : "cursor-not-allowed bg-slate-300",
                )}
              >
                {updateMutation.isPending
                  ? "저장 중..."
                  : updateMutation.isError && isDirty
                    ? "저장 실패 — 재시도"
                    : "저장"}
              </button>
            </div>

            {/* ── 사이드바 외관 ── */}
            <div className="border-t border-slate-200 pt-8">
              <div>
                <h2 className="text-lg font-semibold text-slate-900">
                  사이드바 외관
                </h2>
                <p className="mt-1 text-sm text-slate-500">
                  사이드바 테마, 강조 색상, 레이아웃 스타일을 설정합니다. 변경
                  사항은 즉시 반영됩니다.
                </p>
              </div>

              {/* 사이드바 테마 선택 */}
              <div className="mt-6">
                <h3 className="text-sm font-semibold text-slate-700 mb-3">
                  테마
                </h3>
                <div className="grid grid-cols-3 gap-4">
                  {SIDEBAR_THEME_PRESETS.map((preset) => {
                    const selected = appearance.sidebarTheme === preset.key;
                    return (
                      <button
                        key={preset.key}
                        type="button"
                        onClick={() =>
                          updateAppearance({ sidebarTheme: preset.key })
                        }
                        className={cn(
                          "relative flex flex-col items-center rounded-xl border-2 p-3 transition-all cursor-pointer",
                          "hover:shadow-md",
                          selected
                            ? "border-emerald-500 ring-2 ring-emerald-500/30 shadow-sm"
                            : "border-slate-200 hover:border-slate-300",
                        )}
                      >
                        <div className="w-full aspect-[3/5] mb-3">
                          <MiniSidebarPreview
                            theme={preset.key}
                            accentColor={appearance.sidebarAccentColor}
                          />
                        </div>
                        <span className="text-sm font-semibold text-slate-900">
                          {preset.label}
                        </span>
                        <span className="text-xs text-slate-500 mt-0.5">
                          {preset.description}
                        </span>
                        {selected && (
                          <div className="absolute top-2 right-2 w-5 h-5 bg-emerald-500 rounded-full flex items-center justify-center">
                            <Check className="h-3 w-3 text-white" />
                          </div>
                        )}
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* 강조 색상 */}
              <div className="mt-6">
                <h3 className="flex items-center gap-2 text-sm font-semibold text-slate-700 mb-3">
                  <Paintbrush className="h-4 w-4" />
                  강조 색상
                </h3>
                <div className="flex flex-wrap gap-3">
                  {SIDEBAR_ACCENT_COLORS.map((color) => {
                    const selected =
                      appearance.sidebarAccentColor === color.hex;
                    return (
                      <button
                        key={color.hex}
                        type="button"
                        onClick={() =>
                          updateAppearance({ sidebarAccentColor: color.hex })
                        }
                        className={cn(
                          "relative w-10 h-10 rounded-full transition-all cursor-pointer",
                          "ring-offset-2 ring-offset-white",
                          selected
                            ? "ring-2 ring-emerald-500 scale-110"
                            : "hover:scale-105",
                        )}
                        style={{ backgroundColor: color.hex }}
                        aria-label={color.label}
                        title={color.label}
                      >
                        {selected && (
                          <Check className="absolute inset-0 m-auto h-4 w-4 text-white drop-shadow-sm" />
                        )}
                      </button>
                    );
                  })}
                </div>
                <div className="mt-3 flex items-center gap-3">
                  <label
                    htmlFor="custom-accent"
                    className="text-sm text-slate-500"
                  >
                    커스텀:
                  </label>
                  <div className="flex items-center gap-2">
                    <input
                      type="color"
                      id="custom-accent"
                      value={appearance.sidebarAccentColor}
                      onChange={(e) =>
                        updateAppearance({ sidebarAccentColor: e.target.value })
                      }
                      className="w-8 h-8 rounded-full border border-slate-200 cursor-pointer"
                    />
                    <span className="text-xs font-mono text-slate-400">
                      {appearance.sidebarAccentColor}
                    </span>
                  </div>
                </div>
              </div>

              {/* 레이아웃 스타일 */}
              <div className="mt-6">
                <h3 className="text-sm font-semibold text-slate-700 mb-3">
                  레이아웃
                </h3>
                <div className="grid grid-cols-2 gap-4">
                  {SIDEBAR_LAYOUT_OPTIONS.map((option) => {
                    const selected = appearance.sidebarLayout === option.key;
                    return (
                      <button
                        key={option.key}
                        type="button"
                        onClick={() =>
                          updateAppearance({ sidebarLayout: option.key })
                        }
                        className={cn(
                          "relative flex flex-col items-center rounded-xl border-2 p-4 transition-all cursor-pointer",
                          "hover:shadow-md",
                          selected
                            ? "border-emerald-500 ring-2 ring-emerald-500/30 shadow-sm"
                            : "border-slate-200 hover:border-slate-300",
                        )}
                      >
                        <div className="w-full h-24 bg-slate-50 rounded-lg flex items-center justify-center mb-3">
                          {option.key === "COMPACT" ? (
                            <div className="flex gap-1.5">
                              <div className="w-12 h-20 bg-emerald-900/20 rounded-sm" />
                              <div className="w-32 h-20 bg-slate-200 rounded-sm" />
                            </div>
                          ) : (
                            <div className="flex gap-1.5">
                              <div className="w-8 h-20 bg-emerald-900/20 rounded-sm flex flex-col items-center gap-1 pt-1">
                                <div className="w-4 h-4 bg-emerald-900/30 rounded-sm" />
                                <div className="w-4 h-4 bg-emerald-500/40 rounded-sm" />
                                <div className="w-4 h-4 bg-emerald-900/30 rounded-sm" />
                              </div>
                              <div className="w-36 h-20 bg-slate-200 rounded-sm" />
                            </div>
                          )}
                        </div>
                        <span className="text-sm font-semibold text-slate-900">
                          {option.label}
                        </span>
                        <span className="text-xs text-slate-500 mt-0.5">
                          {option.description}
                        </span>
                        {selected && (
                          <div className="absolute top-2 right-2 w-5 h-5 bg-emerald-500 rounded-full flex items-center justify-center">
                            <Check className="h-3 w-3 text-white" />
                          </div>
                        )}
                      </button>
                    );
                  })}
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === "general" && (
          <div
            id="panel-general"
            role="tabpanel"
            className="rounded-xl border border-slate-200 bg-slate-50 p-12 text-center"
          >
            <p className="text-sm text-slate-400">
              일반 정보 설정은 향후 구현 예정입니다.
            </p>
          </div>
        )}

        {activeTab === "legal" && (
          <div
            id="panel-legal"
            role="tabpanel"
            className="rounded-xl border border-slate-200 bg-slate-50 p-12 text-center"
          >
            <p className="text-sm text-slate-400">
              법률 & 개인정보 정책 설정은 향후 구현 예정입니다.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

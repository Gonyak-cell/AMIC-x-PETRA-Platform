import { useCallback, useState } from "react";
import type { KeyboardEvent } from "react";

import { cn } from "@/lib/cn";
import { PageHero } from "@/components/ui";
import {
  usePlatformSettings,
  useUpdatePlatformSettings,
  type TableStyleTheme,
} from "@/hooks/usePlatformSettings";

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
      headerBg: "#4A8A4A",
      headerText: "#FFFFFF",
      borderStyle: "1px dashed #CCCCCC",
    },
  },
];

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

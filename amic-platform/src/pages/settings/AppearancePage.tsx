import { Palette, Check, Layout, Paintbrush } from "lucide-react";
import { cn } from "@/lib/cn";
import { PageHero, Card } from "@/components/ui";
import {
  useSidebarAppearance,
  SIDEBAR_THEME_VARS,
} from "@/hooks/useSidebarAppearance";
import type { SidebarTheme, SidebarLayout } from "@/types/settings";

// ── Theme presets ──

const THEME_PRESETS: Array<{
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

// ── Accent colors (Green/Teal/Cyan family) ──

const ACCENT_COLORS = [
  { hex: "#26C260", label: "AMIC Green" },
  { hex: "#34D399", label: "Emerald" },
  { hex: "#10B981", label: "Emerald 500" },
  { hex: "#059669", label: "Emerald 600" },
  { hex: "#14B8A6", label: "Teal" },
  { hex: "#22D3EE", label: "Cyan" },
];

// ── Layout options ──

const LAYOUT_OPTIONS: Array<{
  key: SidebarLayout;
  label: string;
  description: string;
}> = [
  {
    key: "COMPACT",
    label: "Compact",
    description: "아이콘 + 텍스트 수평 배치 (기본)",
  },
  {
    key: "EXPANDED",
    label: "Iconic",
    description: "큰 아이콘 + 텍스트 수직 배치",
  },
];

// ── Section Title ──

function SectionTitle({
  icon: Icon,
  children,
}: {
  icon: typeof Palette;
  children: React.ReactNode;
}) {
  return (
    <h2 className="flex items-center gap-2 text-lg font-semibold text-text-dark mb-4">
      <Icon className="h-5 w-5 text-amic" />
      {children}
    </h2>
  );
}

// ── Mini Sidebar Preview ──

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
      {/* Mini logo area */}
      <div
        className="h-6 mx-2 mt-2 rounded-sm"
        style={{ backgroundColor: logoBg }}
      />
      {/* Mini divider */}
      <div className="h-px mx-2 my-2" style={{ backgroundColor: divider }} />
      {/* Mini nav items */}
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
      {/* Mini accent bar on second item */}
      <div className="relative -mt-[54px] ml-[calc(100%-4px)]">
        <div
          className="w-[3px] h-4 rounded-l-full"
          style={{ backgroundColor: accentColor }}
        />
      </div>
    </div>
  );
}

// ── Main Page ──

export default function AppearancePage() {
  const { appearance, updateAppearance } = useSidebarAppearance();

  return (
    <div>
      <PageHero
        title="외관 설정"
        subtitle="사이드바 테마, 강조 색상, 레이아웃 스타일을 커스터마이즈합니다."
        compact
      />

      <div className="grid lg:grid-cols-[1fr_280px] gap-6 mt-6">
        {/* Left: Controls */}
        <div className="space-y-8">
          {/* Section 1: Theme */}
          <Card>
            <div className="p-6">
              <SectionTitle icon={Palette}>사이드바 테마</SectionTitle>
              <div className="grid grid-cols-3 gap-4">
                {THEME_PRESETS.map((preset) => {
                  const selected = appearance.sidebarTheme === preset.key;
                  return (
                    <button
                      key={preset.key}
                      type="button"
                      onClick={() =>
                        updateAppearance({ sidebarTheme: preset.key })
                      }
                      className={cn(
                        "relative flex flex-col items-center rounded-dr border-2 p-3 transition-all cursor-pointer",
                        "hover:shadow-dr-md",
                        selected
                          ? "border-accent ring-2 ring-accent/30 shadow-dr-sm"
                          : "border-gray-border hover:border-amic-200",
                      )}
                    >
                      {/* Mini preview */}
                      <div className="w-full aspect-[3/5] mb-3">
                        <MiniSidebarPreview
                          theme={preset.key}
                          accentColor={appearance.sidebarAccentColor}
                        />
                      </div>
                      {/* Label */}
                      <span className="text-sm font-semibold text-text-dark">
                        {preset.label}
                      </span>
                      <span className="text-xs text-text-secondary mt-0.5">
                        {preset.description}
                      </span>
                      {/* Check overlay */}
                      {selected && (
                        <div className="absolute top-2 right-2 w-5 h-5 bg-accent rounded-full flex items-center justify-center">
                          <Check className="h-3 w-3 text-white" />
                        </div>
                      )}
                    </button>
                  );
                })}
              </div>
            </div>
          </Card>

          {/* Section 2: Accent Color */}
          <Card>
            <div className="p-6">
              <SectionTitle icon={Paintbrush}>강조 색상</SectionTitle>
              <p className="text-sm text-text-secondary mb-4">
                사이드바 활성 항목의 강조 색상을 선택합니다. Green 계열 권장.
              </p>
              <div className="flex flex-wrap gap-3">
                {ACCENT_COLORS.map((color) => {
                  const selected = appearance.sidebarAccentColor === color.hex;
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
                          ? "ring-2 ring-amic scale-110"
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
              {/* Custom hex input */}
              <div className="mt-4 flex items-center gap-3">
                <label
                  htmlFor="custom-accent"
                  className="text-sm text-text-secondary"
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
                    className="w-8 h-8 rounded-full border border-gray-border cursor-pointer"
                  />
                  <span className="text-xs font-mono text-text-muted">
                    {appearance.sidebarAccentColor}
                  </span>
                </div>
              </div>
            </div>
          </Card>

          {/* Section 3: Layout */}
          <Card>
            <div className="p-6">
              <SectionTitle icon={Layout}>레이아웃 스타일</SectionTitle>
              <div className="grid grid-cols-2 gap-4">
                {LAYOUT_OPTIONS.map((option) => {
                  const selected = appearance.sidebarLayout === option.key;
                  return (
                    <button
                      key={option.key}
                      type="button"
                      onClick={() =>
                        updateAppearance({ sidebarLayout: option.key })
                      }
                      className={cn(
                        "relative flex flex-col items-center rounded-dr border-2 p-4 transition-all cursor-pointer",
                        "hover:shadow-dr-md",
                        selected
                          ? "border-accent ring-2 ring-accent/30 shadow-dr-sm"
                          : "border-gray-border hover:border-amic-200",
                      )}
                    >
                      {/* Wireframe preview */}
                      <div className="w-full h-24 bg-bg-cool rounded-dr-sm flex items-center justify-center mb-3">
                        {option.key === "COMPACT" ? (
                          <div className="flex gap-1.5">
                            <div className="w-12 h-20 bg-amic/20 rounded-sm" />
                            <div className="w-32 h-20 bg-gray-200 rounded-sm" />
                          </div>
                        ) : (
                          <div className="flex gap-1.5">
                            <div className="w-8 h-20 bg-amic/20 rounded-sm flex flex-col items-center gap-1 pt-1">
                              <div className="w-4 h-4 bg-amic/40 rounded-sm" />
                              <div className="w-4 h-4 bg-accent/40 rounded-sm" />
                              <div className="w-4 h-4 bg-amic/40 rounded-sm" />
                            </div>
                            <div className="w-36 h-20 bg-gray-200 rounded-sm" />
                          </div>
                        )}
                      </div>
                      <span className="text-sm font-semibold text-text-dark">
                        {option.label}
                      </span>
                      <span className="text-xs text-text-secondary mt-0.5">
                        {option.description}
                      </span>
                      {selected && (
                        <div className="absolute top-2 right-2 w-5 h-5 bg-accent rounded-full flex items-center justify-center">
                          <Check className="h-3 w-3 text-white" />
                        </div>
                      )}
                    </button>
                  );
                })}
              </div>
            </div>
          </Card>
        </div>

        {/* Right: Live Preview */}
        <div className="hidden lg:block">
          <div className="sticky top-24">
            <Card>
              <div className="p-4">
                <h3 className="text-sm font-semibold text-text-dark mb-3">
                  실시간 미리보기
                </h3>
                <div className="w-full aspect-[3/6] rounded-dr overflow-hidden shadow-dr-sm">
                  <MiniSidebarPreview
                    theme={appearance.sidebarTheme}
                    accentColor={appearance.sidebarAccentColor}
                  />
                </div>
                <p className="text-xs text-text-muted mt-3 text-center">
                  변경 사항은 사이드바에 즉시 반영됩니다
                </p>
              </div>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}

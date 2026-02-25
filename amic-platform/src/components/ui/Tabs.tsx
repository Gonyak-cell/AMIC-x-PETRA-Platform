import { useRef, useCallback, useEffect } from "react";
import { cn } from "@/lib/cn";
import { gsap } from "@/lib/gsap";
import type { LucideIcon } from "lucide-react";

export interface TabItem {
  id: string;
  label: string;
  icon?: LucideIcon;
  badge?: string | number;
  disabled?: boolean;
}

export interface TabsProps {
  tabs: TabItem[];
  activeTab: string;
  onTabChange: (tabId: string) => void;
  variant?: "underline" | "pill";
  size?: "sm" | "md";
  className?: string;
}

export function Tabs({
  tabs,
  activeTab,
  onTabChange,
  variant = "underline",
  size = "md",
  className,
}: TabsProps) {
  const tabsRef = useRef<(HTMLButtonElement | null)[]>([]);
  const indicatorRef = useRef<HTMLDivElement>(null);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent, index: number) => {
      const enabledTabs = tabs
        .map((t, i) => ({ ...t, index: i }))
        .filter((t) => !t.disabled);
      const currentIdx = enabledTabs.findIndex((t) => t.index === index);
      if (currentIdx === -1) return;

      let nextIdx = -1;
      if (e.key === "ArrowRight") {
        nextIdx = enabledTabs[(currentIdx + 1) % enabledTabs.length].index;
      } else if (e.key === "ArrowLeft") {
        nextIdx =
          enabledTabs[(currentIdx - 1 + enabledTabs.length) % enabledTabs.length]
            .index;
      } else if (e.key === "Home") {
        nextIdx = enabledTabs[0].index;
      } else if (e.key === "End") {
        nextIdx = enabledTabs[enabledTabs.length - 1].index;
      }

      if (nextIdx >= 0) {
        e.preventDefault();
        tabsRef.current[nextIdx]?.focus();
        onTabChange(tabs[nextIdx].id);
      }
    },
    [tabs, onTabChange],
  );

  // Animate underline indicator to active tab position
  useEffect(() => {
    if (variant !== "underline" || !indicatorRef.current) return;

    const activeIndex = tabs.findIndex((t) => t.id === activeTab);
    const activeEl = tabsRef.current[activeIndex];
    if (!activeEl) return;

    gsap.to(indicatorRef.current, {
      x: activeEl.offsetLeft,
      width: activeEl.offsetWidth,
      duration: 0.3,
      ease: "power2.inOut",
    });
  }, [activeTab, tabs, variant]);

  const isUnderline = variant === "underline";

  return (
    <div
      role="tablist"
      aria-orientation="horizontal"
      className={cn(
        isUnderline && "relative border-b border-gray-border",
        !isUnderline && "flex gap-1 rounded-dr bg-bg-cool p-1",
        className,
      )}
    >
      <div
        className={cn(
          isUnderline && "flex gap-1 overflow-x-auto scrollbar-hide",
          !isUnderline && "flex gap-1 w-full overflow-x-auto scrollbar-hide",
        )}
      >
        {tabs.map((tab, index) => {
          const isActive = tab.id === activeTab;
          const Icon = tab.icon;

          return (
            <button
              key={tab.id}
              ref={(el) => {
                tabsRef.current[index] = el;
              }}
              role="tab"
              id={`tab-${tab.id}`}
              aria-selected={isActive}
              aria-controls={`tabpanel-${tab.id}`}
              aria-disabled={tab.disabled}
              tabIndex={isActive ? 0 : -1}
              disabled={tab.disabled}
              onClick={() => onTabChange(tab.id)}
              onKeyDown={(e) => handleKeyDown(e, index)}
              className={cn(
                "inline-flex items-center gap-1.5 whitespace-nowrap font-medium transition-colors duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/40",
                size === "sm" ? "text-xs px-3 py-1.5" : "text-sm px-4 py-2.5",
                tab.disabled && "opacity-40 cursor-not-allowed",
                // Underline variant — no static border-b, indicator handles it
                isUnderline && [
                  "-mb-px",
                  isActive
                    ? "text-accent"
                    : "text-text-secondary hover:text-text-dark",
                ],
                // Pill variant
                !isUnderline && [
                  "rounded-dr-sm flex-1 justify-center",
                  isActive
                    ? "bg-white text-accent shadow-dr-sm"
                    : "text-text-secondary hover:text-text-dark",
                ],
              )}
            >
              {Icon && (
                <Icon
                  className={size === "sm" ? "h-3.5 w-3.5" : "h-4 w-4"}
                />
              )}
              {tab.label}
              {tab.badge != null && (
                <span
                  className={cn(
                    "ml-1 inline-flex items-center justify-center rounded-full text-[10px] font-semibold leading-none",
                    size === "sm"
                      ? "h-4 min-w-4 px-1"
                      : "h-5 min-w-5 px-1.5",
                    isActive
                      ? "bg-accent/10 text-accent"
                      : "bg-gray-200 text-text-secondary",
                  )}
                >
                  {tab.badge}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Sliding underline indicator */}
      {isUnderline && (
        <div
          ref={indicatorRef}
          className="absolute bottom-0 left-0 h-0.5 bg-accent rounded-full"
          style={{ width: 0 }}
        />
      )}
    </div>
  );
}

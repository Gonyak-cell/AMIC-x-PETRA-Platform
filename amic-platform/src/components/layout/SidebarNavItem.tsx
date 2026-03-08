import { useState, useRef, useCallback } from "react";
import { NavLink } from "react-router-dom";
import type { LucideIcon } from "lucide-react";
import { ChevronDown, CheckCircle2 } from "lucide-react";
import { cn } from "@/lib/cn";
import { gsap } from "@/lib/gsap";

export interface SidebarNavItemProps {
  to: string;
  label: string;
  icon: LucideIcon;
  end?: boolean;
  disabled?: boolean;
  comingSoon?: boolean;
  onClick?: () => void;
}

export function SidebarNavItem({
  to,
  label,
  icon: Icon,
  end,
  disabled,
  comingSoon,
  onClick,
}: SidebarNavItemProps) {
  const iconRef = useRef<SVGSVGElement>(null);

  const handleMouseEnter = useCallback(() => {
    if (iconRef.current) {
      gsap.fromTo(
        iconRef.current,
        { scale: 1 },
        {
          scale: 1.15,
          duration: 0.15,
          yoyo: true,
          repeat: 1,
          ease: "power2.out",
        },
      );
    }
  }, []);

  if (disabled || comingSoon) {
    return (
      <span
        className="flex items-center gap-3 px-4 py-2.5 text-sm font-medium rounded-lg min-h-[44px] cursor-not-allowed"
        style={{ color: "var(--sidebar-text)", opacity: 0.4 }}
        aria-disabled="true"
      >
        <Icon className="h-5 w-5 flex-shrink-0" aria-hidden="true" />
        <span>{label}</span>
        {comingSoon && (
          <span
            className="ml-auto text-[9px] font-semibold uppercase tracking-wider px-1.5 py-0.5 rounded-full"
            style={{
              color: "var(--sidebar-text)",
              opacity: 0.2,
              backgroundColor: "var(--sidebar-hover-bg)",
            }}
          >
            Soon
          </span>
        )}
      </span>
    );
  }

  return (
    <NavLink
      to={to}
      end={end}
      onClick={onClick}
      onMouseEnter={handleMouseEnter}
      className={({ isActive }) =>
        cn(
          "flex items-center gap-3 px-4 py-2.5 text-sm font-medium rounded-lg transition-colors",
          "min-h-[44px]",
          isActive ? "sidebar-accent-bar-right" : "sidebar-hover",
        )
      }
      style={({ isActive }) => ({
        backgroundColor: isActive ? "var(--sidebar-active-bg)" : undefined,
        color: isActive ? "var(--sidebar-text)" : "var(--sidebar-text-muted)",
      })}
    >
      {({ isActive }) => (
        <>
          <Icon
            ref={iconRef}
            className="h-5 w-5 flex-shrink-0"
            aria-hidden="true"
          />
          <span aria-current={isActive ? "page" : undefined}>{label}</span>
        </>
      )}
    </NavLink>
  );
}

export interface SidebarSectionProps {
  title: string;
  children: React.ReactNode;
  collapsible?: boolean;
  defaultOpen?: boolean;
  storageKey?: string;
  className?: string;
}

function getInitialOpen(
  storageKey: string | undefined,
  defaultOpen: boolean,
): boolean {
  if (!storageKey) return defaultOpen;
  try {
    const stored = sessionStorage.getItem(`sidebar-section-${storageKey}`);
    if (stored !== null) return stored === "true";
  } catch {
    // sessionStorage unavailable
  }
  return defaultOpen;
}

export function SidebarSection({
  title,
  children,
  collapsible = false,
  defaultOpen = true,
  storageKey,
  className,
}: SidebarSectionProps) {
  const [isOpen, setIsOpen] = useState(() =>
    getInitialOpen(storageKey, defaultOpen),
  );

  const sectionId = `sidebar-section-${title.toLowerCase().replace(/\s+/g, "-")}`;

  const toggle = () => {
    const next = !isOpen;
    setIsOpen(next);
    if (storageKey) {
      try {
        sessionStorage.setItem(`sidebar-section-${storageKey}`, String(next));
      } catch {
        // sessionStorage unavailable
      }
    }
  };

  return (
    <div className={cn("mt-6", className)}>
      {collapsible ? (
        <button
          type="button"
          onClick={toggle}
          aria-expanded={isOpen}
          aria-controls={sectionId}
          className="w-full flex items-center justify-between px-4 mb-2 text-[10px] font-semibold uppercase tracking-[0.15em] transition-colors cursor-pointer"
          style={{ color: "var(--sidebar-text-muted)" }}
        >
          <span>{title}</span>
          <ChevronDown
            className={cn(
              "h-3.5 w-3.5 transition-transform duration-200",
              !isOpen && "-rotate-90",
            )}
            aria-hidden="true"
          />
        </button>
      ) : (
        <h3
          id={sectionId}
          className="px-4 mb-2 text-[10px] font-semibold uppercase tracking-[0.15em]"
          style={{ color: "var(--sidebar-text-muted)" }}
        >
          {title}
        </h3>
      )}
      <div
        id={collapsible ? sectionId : undefined}
        className={cn(
          "overflow-hidden transition-all duration-200 ease-in-out",
          collapsible && !isOpen
            ? "max-h-0 opacity-0"
            : "max-h-[1000px] opacity-100",
        )}
      >
        <nav
          className="space-y-1"
          aria-labelledby={!collapsible ? sectionId : undefined}
          aria-label={collapsible ? title : undefined}
        >
          {children}
        </nav>
      </div>
    </div>
  );
}

// ── Phase-aware sidebar item for MA workflow ──

export interface SidebarPhaseItemProps {
  to: string;
  label: string;
  icon: LucideIcon;
  status: "done" | "current" | "future";
  onClick?: () => void;
}

export function SidebarPhaseItem({
  to,
  label,
  icon: Icon,
  status,
  onClick,
}: SidebarPhaseItemProps) {
  const iconRef = useRef<SVGSVGElement>(null);

  const handleMouseEnter = useCallback(() => {
    if (status === "future") return;
    if (iconRef.current) {
      gsap.fromTo(
        iconRef.current,
        { scale: 1 },
        {
          scale: 1.15,
          duration: 0.15,
          yoyo: true,
          repeat: 1,
          ease: "power2.out",
        },
      );
    }
  }, [status]);

  // future: disabled, not clickable
  if (status === "future") {
    return (
      <span
        className="flex items-center gap-3 px-4 py-2 text-sm font-medium rounded-lg min-h-[40px] cursor-not-allowed"
        style={{ color: "var(--sidebar-text)", opacity: 0.4 }}
        aria-disabled="true"
      >
        <Icon className="h-[18px] w-[18px] flex-shrink-0" aria-hidden="true" />
        <span>{label}</span>
      </span>
    );
  }

  // done: accent check icon, clickable
  if (status === "done") {
    return (
      <NavLink
        to={to}
        onClick={onClick}
        onMouseEnter={handleMouseEnter}
        className="flex items-center gap-3 px-4 py-2 text-sm font-medium rounded-lg min-h-[40px] transition-colors"
        style={{ color: "var(--sidebar-accent)", opacity: 0.8 }}
      >
        <CheckCircle2
          ref={iconRef}
          className="h-[18px] w-[18px] flex-shrink-0"
          aria-hidden="true"
        />
        <span>{label}</span>
      </NavLink>
    );
  }

  // current: highlighted with accent bar + pulse indicator
  return (
    <NavLink
      to={to}
      onClick={onClick}
      onMouseEnter={handleMouseEnter}
      className="flex items-center gap-3 px-4 py-2 text-sm font-medium rounded-lg min-h-[40px] sidebar-accent-bar-right transition-colors"
      style={{
        backgroundColor: "var(--sidebar-active-bg)",
        color: "var(--sidebar-text)",
      }}
      aria-current="step"
    >
      <span className="relative flex-shrink-0">
        <Icon ref={iconRef} className="h-[18px] w-[18px]" aria-hidden="true" />
        <span
          className="absolute -top-0.5 -right-0.5 h-2 w-2 rounded-full animate-pulse"
          style={{ backgroundColor: "var(--sidebar-accent)" }}
        />
      </span>
      <span className="font-semibold">{label}</span>
    </NavLink>
  );
}

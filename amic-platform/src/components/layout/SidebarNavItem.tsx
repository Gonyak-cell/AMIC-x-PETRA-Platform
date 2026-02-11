import { useState } from "react";
import { NavLink } from "react-router-dom";
import type { LucideIcon } from "lucide-react";
import { ChevronDown } from "lucide-react";
import { cn } from "@/lib/cn";

export interface SidebarNavItemProps {
  to: string;
  label: string;
  icon: LucideIcon;
  end?: boolean;
  disabled?: boolean;
  onClick?: () => void;
}

export function SidebarNavItem({ to, label, icon: Icon, end, disabled, onClick }: SidebarNavItemProps) {
  if (disabled) {
    return (
      <span
        className="flex items-center gap-3 px-4 py-2.5 text-sm font-medium rounded-lg min-h-[44px] text-white/25 cursor-not-allowed"
        aria-disabled="true"
      >
        <Icon className="h-5 w-5 flex-shrink-0" aria-hidden="true" />
        <span>{label}</span>
      </span>
    );
  }

  return (
    <NavLink
      to={to}
      end={end}
      onClick={onClick}
      className={({ isActive }) =>
        cn(
          "flex items-center gap-3 px-4 py-2.5 text-sm font-medium rounded-lg transition-colors",
          "min-h-[44px]", // WCAG 2.5.5 touch target
          isActive
            ? "bg-white/[0.08] text-white relative before:absolute before:right-0 before:top-1 before:bottom-1 before:w-[3px] before:bg-accent before:rounded-l-full"
            : "text-white/60 hover:bg-white/5 hover:text-white"
        )
      }
    >
      {({ isActive }) => (
        <>
          <Icon className="h-5 w-5 flex-shrink-0" aria-hidden="true" />
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
}

function getInitialOpen(storageKey: string | undefined, defaultOpen: boolean): boolean {
  if (!storageKey) return defaultOpen;
  try {
    const stored = localStorage.getItem(`sidebar-section-${storageKey}`);
    if (stored !== null) return stored === "true";
  } catch {
    // localStorage unavailable
  }
  return defaultOpen;
}

export function SidebarSection({
  title,
  children,
  collapsible = false,
  defaultOpen = true,
  storageKey,
}: SidebarSectionProps) {
  const [isOpen, setIsOpen] = useState(() => getInitialOpen(storageKey, defaultOpen));

  const sectionId = `sidebar-section-${title.toLowerCase().replace(/\s+/g, "-")}`;

  const toggle = () => {
    const next = !isOpen;
    setIsOpen(next);
    if (storageKey) {
      try {
        localStorage.setItem(`sidebar-section-${storageKey}`, String(next));
      } catch {
        // localStorage unavailable
      }
    }
  };

  return (
    <div className="mt-6">
      {collapsible ? (
        <button
          type="button"
          onClick={toggle}
          aria-expanded={isOpen}
          aria-controls={sectionId}
          className="w-full flex items-center justify-between px-4 mb-2 text-[10px] font-semibold text-white/30 uppercase tracking-[0.15em] hover:text-white/50 transition-colors cursor-pointer"
        >
          <span>{title}</span>
          <ChevronDown
            className={cn(
              "h-3.5 w-3.5 transition-transform duration-200",
              !isOpen && "-rotate-90"
            )}
            aria-hidden="true"
          />
        </button>
      ) : (
        <h3
          id={sectionId}
          className="px-4 mb-2 text-[10px] font-semibold text-white/30 uppercase tracking-[0.15em]"
        >
          {title}
        </h3>
      )}
      <div
        id={collapsible ? sectionId : undefined}
        className={cn(
          "overflow-hidden transition-all duration-200 ease-in-out",
          collapsible && !isOpen ? "max-h-0 opacity-0" : "max-h-[1000px] opacity-100"
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

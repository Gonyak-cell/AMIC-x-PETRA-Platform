import { useState, useEffect, useRef, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import type { LucideIcon } from "lucide-react";
import { ChevronDown } from "lucide-react";
import { cn } from "@/lib/cn";
import { gsap } from "@/lib/gsap";

export interface SidebarModuleGroupProps {
  id: string;
  label: string;
  icon: LucideIcon;
  basePath: string;
  isActive: boolean;
  storageKey: string;
  defaultOpen?: boolean;
  children: React.ReactNode;
  onNavItemClick?: () => void;
}

function getInitialOpen(storageKey: string, defaultOpen: boolean): boolean {
  try {
    const stored = sessionStorage.getItem(`sidebar-module-${storageKey}`);
    if (stored !== null) return stored === "true";
  } catch {
    // sessionStorage unavailable
  }
  return defaultOpen;
}

function persistState(storageKey: string, open: boolean) {
  try {
    sessionStorage.setItem(`sidebar-module-${storageKey}`, String(open));
  } catch {
    // sessionStorage unavailable
  }
}

export function SidebarModuleGroup({
  id,
  label,
  icon: Icon,
  basePath,
  isActive,
  storageKey,
  defaultOpen = false,
  children,
  onNavItemClick,
}: SidebarModuleGroupProps) {
  const navigate = useNavigate();
  const iconRef = useRef<SVGSVGElement>(null);
  const [isOpen, setIsOpen] = useState(() =>
    getInitialOpen(storageKey, defaultOpen || isActive),
  );

  // Auto-expand when this module becomes active
  useEffect(() => {
    if (isActive && !isOpen) {
      setIsOpen(true);
      persistState(storageKey, true);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isActive]);

  const handleToggle = () => {
    const next = !isOpen;
    setIsOpen(next);
    persistState(storageKey, next);

    // Opening from closed + not already on this module → navigate
    if (next && !isActive) {
      navigate(basePath);
      onNavItemClick?.();
    }
  };

  // GSAP icon hover animation (same pattern as SidebarNavItem)
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

  const contentId = `sidebar-module-${id}`;

  return (
    <div className="mt-1">
      <button
        type="button"
        onClick={handleToggle}
        onMouseEnter={handleMouseEnter}
        aria-expanded={isOpen}
        aria-controls={contentId}
        className={cn(
          "w-full flex items-center gap-3 px-3 py-2.5 rounded-lg",
          "text-sm font-semibold transition-colors cursor-pointer",
          "min-h-[44px]",
          isActive ? "sidebar-accent-bar-left" : "sidebar-hover",
        )}
        style={{
          backgroundColor: isActive ? "var(--sidebar-active-bg)" : undefined,
          color: isActive ? "var(--sidebar-text)" : "var(--sidebar-text-muted)",
        }}
      >
        <Icon
          ref={iconRef}
          className="h-5 w-5 flex-shrink-0"
          aria-hidden="true"
        />
        <span className="flex-1 text-left">{label}</span>
        <ChevronDown
          className={cn(
            "h-4 w-4 transition-transform duration-200",
            !isOpen && "-rotate-90",
          )}
          aria-hidden="true"
        />
      </button>

      <div
        id={contentId}
        role="region"
        aria-label={`${label} navigation`}
        className={cn(
          "overflow-hidden transition-all duration-500 ease-in-out",
          isOpen ? "max-h-[2000px] opacity-100" : "max-h-0 opacity-0",
        )}
      >
        <div
          className="ml-2 pl-3 border-l mt-1 pb-1"
          style={{ borderColor: "var(--sidebar-divider)" }}
        >
          {children}
        </div>
      </div>
    </div>
  );
}

import { NavLink } from "react-router-dom";
import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/cn";

export interface SidebarNavItemProps {
  to: string;
  label: string;
  icon: LucideIcon;
  end?: boolean;
  onClick?: () => void;
}

export function SidebarNavItem({ to, label, icon: Icon, end, onClick }: SidebarNavItemProps) {
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
            ? "bg-white/10 text-white border-l-2 border-accent ml-[-2px]"
            : "text-white/70 hover:bg-white/5 hover:text-white"
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
}

export function SidebarSection({ title, children }: SidebarSectionProps) {
  return (
    <div className="mt-6">
      <h3
        id={`sidebar-section-${title.toLowerCase().replace(/\s+/g, "-")}`}
        className="px-4 mb-2 text-xs font-semibold text-white/40 uppercase tracking-wider"
      >
        {title}
      </h3>
      <nav
        className="space-y-1"
        aria-labelledby={`sidebar-section-${title.toLowerCase().replace(/\s+/g, "-")}`}
      >
        {children}
      </nav>
    </div>
  );
}

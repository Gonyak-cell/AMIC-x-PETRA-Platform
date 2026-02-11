import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/cn";

export interface SectionDividerProps {
  /** Primary text - accepts either `label` or `title` */
  label?: string;
  title?: string;
  route?: string;
  description?: string;
  icon?: LucideIcon;
  anchor?: string;
  className?: string;
}

export function SectionDivider({ label, title, route, description, icon: Icon, anchor, className }: SectionDividerProps) {
  const text = label ?? title ?? "";

  return (
    <div id={anchor} className={cn("pt-12 pb-6 scroll-mt-20", className)}>
      <div className="flex items-center gap-4">
        <div className="border-accent-left pl-4">
          <div className="flex items-center gap-2">
            {Icon && <Icon className="h-4 w-4 text-amic" />}
            <h2 className="label-uppercase text-sm text-amic">{text}</h2>
          </div>
          {description && (
            <p className="text-xs text-text-secondary mt-0.5">{description}</p>
          )}
          {route && (
            <p className="text-xs text-text-muted font-mono mt-0.5">{route}</p>
          )}
        </div>
        <div className="flex-1 h-px bg-gray-border" />
      </div>
    </div>
  );
}

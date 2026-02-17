import { cn } from "@/lib/cn";

export interface PageHeroProps {
  title: string;
  subtitle?: string;
  actions?: React.ReactNode;
  children?: React.ReactNode;
  compact?: boolean;
  className?: string;
}

export function PageHero({
  title,
  subtitle,
  actions,
  children,
  compact = false,
  className,
}: PageHeroProps) {
  return (
    <section
      className={cn(
        "hero-gradient-radial text-white -mx-4 md:-mx-8",
        compact ? "py-8 md:py-12" : "py-12 md:py-16",
        className
      )}
    >
      <div className="max-w-7xl mx-auto px-4 md:px-8">
        {/* Title + Actions */}
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-6">
          <div>
            <h1 className="text-hero-title font-heading text-white mb-2">
              {title}
            </h1>
            {subtitle && (
              <p className="text-hero-subtitle text-white/80">
                {subtitle}
              </p>
            )}
          </div>
          {actions && (
            <div className="flex flex-wrap items-center gap-3">
              {actions}
            </div>
          )}
        </div>

        {/* Optional Content (e.g., KPI cards) */}
        {children && (
          <div className="stagger">
            {children}
          </div>
        )}
      </div>
    </section>
  );
}

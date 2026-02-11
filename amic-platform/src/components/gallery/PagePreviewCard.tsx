import { cn } from "@/lib/cn";
import { Badge } from "@/components/ui";
import { ArrowRight } from "lucide-react";

export interface PagePreviewCardProps {
  /** Page display name — accepts either `pageName` or `title` */
  pageName?: string;
  title?: string;
  /** Route path — accepts either `route` or `path` */
  route?: string;
  path?: string;
  description?: string;
  tags?: string[];
  variant?: string;
  className?: string;
  children?: React.ReactNode;
}

export function PagePreviewCard({
  pageName,
  title,
  route,
  path,
  description,
  tags,
  className,
  children,
}: PagePreviewCardProps) {
  const displayName = pageName ?? title;
  const displayRoute = route ?? path;

  return (
    <div
      className={cn(
        "bg-white rounded-corporate border border-gray-border shadow-forest-subtle hover-lift overflow-hidden",
        className
      )}
    >
      {/* Page Mock Content */}
      {children && (
        <div className="border-b border-gray-border bg-bg-cool p-6 overflow-hidden">
          <div className="pointer-events-none select-none">{children}</div>
        </div>
      )}

      {/* Card Footer Info (only if metadata provided) */}
      {(displayName || displayRoute || description) && (
        <div className="p-5">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0 flex-1">
              {displayName && (
                <h3 className="font-heading font-semibold text-text-dark text-base flex items-center gap-2">
                  {displayName}
                  <ArrowRight className="h-4 w-4 text-text-muted" />
                </h3>
              )}
              {displayRoute && (
                <p className="text-xs font-mono text-accent mt-0.5">{displayRoute}</p>
              )}
              {description && (
                <p className="text-sm text-text-secondary mt-2 leading-relaxed">{description}</p>
              )}
            </div>
          </div>
          {tags && tags.length > 0 && (
            <div className="flex flex-wrap gap-1.5 mt-3">
              {tags.map((tag) => (
                <Badge key={tag} variant="neutral" pill>{tag}</Badge>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

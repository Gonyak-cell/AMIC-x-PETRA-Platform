import { cn } from "@/lib/cn";

export interface CardProps {
  title?: string;
  headerBar?: boolean;
  actions?: React.ReactNode;
  children: React.ReactNode;
  padding?: "none" | "sm" | "md" | "lg";
  className?: string;
}

const paddingStyles = {
  none: "",
  sm: "p-3",
  md: "p-5",
  lg: "p-6",
};

export function Card({
  title,
  headerBar = false,
  actions,
  children,
  padding = "md",
  className,
}: CardProps) {
  return (
    <div
      className={cn(
        "bg-white rounded-lg border border-gray-border shadow-card",
        className
      )}
    >
      {/* 다크그린 헤더바 */}
      {headerBar && title && (
        <div className="bg-amic text-white px-5 py-3 rounded-t-lg flex items-center justify-between">
          <h3 className="font-heading font-semibold">{title}</h3>
          {actions && <div className="flex items-center gap-2">{actions}</div>}
        </div>
      )}

      {/* 일반 헤더 (headerBar 없을 때) */}
      {!headerBar && title && (
        <div className="px-5 py-4 border-b border-gray-border flex items-center justify-between">
          <h3 className="font-heading font-semibold text-text-dark">{title}</h3>
          {actions && <div className="flex items-center gap-2">{actions}</div>}
        </div>
      )}

      {/* 콘텐츠 */}
      <div className={cn(paddingStyles[padding])}>{children}</div>
    </div>
  );
}

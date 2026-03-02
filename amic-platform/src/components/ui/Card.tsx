import { cn } from "@/lib/cn";
import { useTilt } from "@/hooks/useTilt";

export type CardVariant =
  | "default"
  | "forest-lift"
  | "accent-left"
  | "elevated"
  | "hero";

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  title?: string;
  headerBar?: boolean;
  actions?: React.ReactNode;
  children: React.ReactNode;
  padding?: "none" | "sm" | "md" | "lg";
  variant?: CardVariant;
  hoverEffect?: boolean;
  tilt?: boolean;
  headingLevel?: "h2" | "h3" | "h4" | "h5";
}

const paddingStyles = {
  none: "",
  sm: "p-3",
  md: "p-5",
  lg: "p-6",
};

const cardVariantStyles: Record<CardVariant, string> = {
  default: "shadow-dr-sm",
  "forest-lift": "shadow-forest-card hover-glow",
  "accent-left": "shadow-dr-sm border-accent-left",
  elevated: "shadow-elevated",
  hero: "bg-white/[0.06] border-white/[0.08] backdrop-blur-sm shadow-dr-md",
};

export function Card({
  title,
  headerBar = false,
  actions,
  children,
  padding = "md",
  variant = "default",
  hoverEffect = false,
  tilt = false,
  headingLevel: HeadingTag = "h3",
  className,
  onClick,
  ...rest
}: CardProps) {
  const tiltHandlers = useTilt(2);

  return (
    <div
      {...rest}
      className={cn(
        "bg-white rounded-dr border border-gray-border overflow-hidden",
        cardVariantStyles[variant],
        hoverEffect &&
          variant !== "forest-lift" &&
          "transition-shadow duration-200 hover:shadow-dr-md",
        className,
      )}
      onClick={onClick}
      {...(tilt
        ? {
            onMouseMove: tiltHandlers.onMouseMove,
            onMouseLeave: tiltHandlers.onMouseLeave,
            style: tiltHandlers.style,
          }
        : {})}
    >
      {/* 헤더바 */}
      {headerBar && title && (
        <div className="bg-white px-5 py-3 border-b border-gray-border rounded-t-dr flex items-center justify-between">
          <HeadingTag className="font-heading font-semibold text-amic flex items-center gap-2">
            <span className="inline-block w-1 h-4 bg-accent rounded-full" />
            {title}
          </HeadingTag>
          {actions && <div className="flex items-center gap-2">{actions}</div>}
        </div>
      )}

      {/* 일반 헤더 (headerBar 없을 때) */}
      {!headerBar && title && (
        <div className="px-5 py-4 border-b border-gray-border flex items-center justify-between">
          <HeadingTag className="font-heading font-semibold text-text-dark">
            {title}
          </HeadingTag>
          {actions && <div className="flex items-center gap-2">{actions}</div>}
        </div>
      )}

      {/* 콘텐츠 */}
      <div className={cn(paddingStyles[padding])}>{children}</div>
    </div>
  );
}

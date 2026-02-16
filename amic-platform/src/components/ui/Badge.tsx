import { cn } from "@/lib/cn";

export type BadgeVariant = "success" | "warning" | "error" | "info" | "neutral";

export interface BadgeProps {
  variant?: BadgeVariant;
  pill?: boolean;
  children: React.ReactNode;
  className?: string;
}

const variantStyles: Record<BadgeVariant, string> = {
  success: "bg-accent-light text-positive",
  warning: "bg-amber-50 text-caution",
  error: "bg-red-50 text-negative",
  info: "bg-blue-50 text-blue-700",
  neutral: "bg-bg-cool text-text-secondary",
};

export function Badge({ variant = "neutral", pill = false, children, className }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center px-2 py-0.5 text-xs font-medium tracking-wide transition-colors duration-200",
        pill ? "rounded-full" : "rounded-md",
        variantStyles[variant],
        className
      )}
    >
      {children}
    </span>
  );
}

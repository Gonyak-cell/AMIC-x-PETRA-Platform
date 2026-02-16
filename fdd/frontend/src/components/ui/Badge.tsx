import { cn } from "@/lib/cn";

export type BadgeVariant = "success" | "warning" | "error" | "info" | "neutral";

export interface BadgeProps {
  variant?: BadgeVariant;
  children: React.ReactNode;
  className?: string;
}

const variantStyles: Record<BadgeVariant, string> = {
  success: "bg-bg-light-green text-positive",
  warning: "bg-amber-50 text-caution",
  error: "bg-red-50 text-negative",
  info: "bg-blue-50 text-blue-700",
  neutral: "bg-bg-cool text-text-secondary",
};

export function Badge({ variant = "neutral", children, className }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center px-2 py-0.5 rounded text-xs font-medium",
        variantStyles[variant],
        className
      )}
    >
      {children}
    </span>
  );
}

import { forwardRef } from "react";
import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/cn";

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "ghost" | "danger" | "accent";
  size?: "sm" | "md" | "lg";
  icon?: LucideIcon;
  iconPosition?: "left" | "right";
  loading?: boolean;
}

const variantStyles = {
  primary:
    "bg-amic text-white hover:bg-amic-700 focus:ring-amic-600 disabled:bg-amic-200",
  secondary:
    "bg-white text-amic border border-amic hover:bg-bg-light-green focus:ring-amic-600",
  ghost:
    "bg-transparent text-text-secondary hover:bg-bg-cool hover:text-text-body",
  danger:
    "bg-negative text-white hover:bg-red-700 focus:ring-negative",
  accent:
    "bg-accent text-white hover:bg-accent-hover focus:ring-accent",
};

const sizeStyles = {
  sm: "px-3 py-1.5 text-xs",
  md: "px-4 py-2 text-sm",
  lg: "px-5 py-2.5 text-base",
};

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className,
      variant = "primary",
      size = "md",
      icon: Icon,
      iconPosition = "left",
      loading,
      disabled,
      children,
      ...props
    },
    ref
  ) => {
    const isDisabled = disabled || loading;

    return (
      <button
        ref={ref}
        className={cn(
          "inline-flex items-center justify-center gap-2 rounded-lg font-medium transition-colors",
          "focus:outline-none focus:ring-2 focus:ring-offset-2",
          "disabled:opacity-50 disabled:cursor-not-allowed",
          variantStyles[variant],
          sizeStyles[size],
          className
        )}
        disabled={isDisabled}
        {...props}
      >
        {loading ? (
          <svg
            className="animate-spin h-4 w-4"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            />
          </svg>
        ) : Icon && iconPosition === "left" ? (
          <Icon className="h-4 w-4" />
        ) : null}
        {children}
        {Icon && iconPosition === "right" && !loading && (
          <Icon className="h-4 w-4" />
        )}
      </button>
    );
  }
);

Button.displayName = "Button";

export { Button };

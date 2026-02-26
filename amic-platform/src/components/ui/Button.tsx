import { forwardRef, useCallback } from "react";
import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/cn";
import { gsap } from "@/lib/gsap";

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "ghost" | "danger" | "accent" | "brand";
  size?: "sm" | "md" | "lg";
  icon?: LucideIcon;
  iconPosition?: "left" | "right";
  loading?: boolean;
}

const variantStyles = {
  primary:
    "bg-accent text-white hover:bg-accent-hover focus:ring-accent disabled:bg-accent/50 shadow-dr-sm hover:shadow-glow-green",
  secondary:
    "bg-white text-amic border border-amic/20 hover:border-amic/40 hover:bg-amic-50 focus:ring-amic-600",
  ghost:
    "bg-transparent text-text-secondary hover:bg-bg-cool hover:text-text-body",
  danger:
    "bg-negative text-white hover:bg-red-700 focus:ring-negative shadow-dr-sm",
  accent:
    "bg-accent text-white hover:bg-accent-hover focus:ring-accent shadow-dr-sm hover:shadow-glow-green",
  brand:
    "bg-gradient-to-r from-amic to-solid-green text-white hover:from-amic-700 hover:to-solid-green focus:ring-amic-600 shadow-dr-sm hover:shadow-glow-teal",
};

const sizeStyles = {
  sm: "px-3 py-1.5 text-xs",
  md: "px-4 py-2 text-sm",
  lg: "px-6 py-3 text-base",
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
      onClick,
      ...props
    },
    ref,
  ) => {
    const isDisabled = disabled || loading;

    const handleClick = useCallback(
      (e: React.MouseEvent<HTMLButtonElement>) => {
        if (isDisabled) return;

        // Ripple effect
        const btn = e.currentTarget;
        const rect = btn.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        const ripple = document.createElement("span");
        ripple.className =
          "absolute rounded-full bg-white/30 pointer-events-none";
        ripple.style.left = `${x}px`;
        ripple.style.top = `${y}px`;
        ripple.style.width = "0px";
        ripple.style.height = "0px";
        ripple.style.transform = "translate(-50%, -50%)";
        btn.appendChild(ripple);

        const diameter = Math.max(rect.width, rect.height) * 2;

        gsap.to(ripple, {
          width: diameter,
          height: diameter,
          opacity: 0,
          duration: 0.6,
          ease: "power2.out",
          onComplete: () => ripple.remove(),
        });

        onClick?.(e);
      },
      [isDisabled, onClick],
    );

    return (
      <button
        ref={ref}
        className={cn(
          "relative overflow-hidden inline-flex items-center justify-center gap-2 rounded-dr-sm font-medium whitespace-nowrap transition-all duration-200",
          "focus:outline-none focus:ring-2 focus:ring-offset-2",
          "disabled:opacity-50 disabled:cursor-not-allowed",
          "active:scale-[0.98]",
          variantStyles[variant],
          sizeStyles[size],
          className,
        )}
        disabled={isDisabled}
        aria-busy={loading || undefined}
        onClick={handleClick}
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
  },
);

Button.displayName = "Button";

export { Button };

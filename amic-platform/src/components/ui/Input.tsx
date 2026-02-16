import { forwardRef, useId } from "react";
import { cn } from "@/lib/cn";

export interface InputProps
  extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  hint?: string;
}

const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className, label, error, hint, id, ...props }, ref) => {
    const autoId = useId();
    const inputId = id || autoId;
    const errorId = error ? `${inputId}-error` : undefined;
    const hintId = hint && !error ? `${inputId}-hint` : undefined;

    return (
      <div className="w-full">
        {label && (
          <label
            htmlFor={inputId}
            className="block text-sm font-medium text-text-body mb-1.5"
          >
            {label}
          </label>
        )}
        <input
          ref={ref}
          id={inputId}
          aria-invalid={error ? true : undefined}
          aria-describedby={errorId || hintId}
          className={cn(
            "w-full px-3 py-2 text-sm rounded-dr-sm border transition-colors shadow-sm",
            "bg-white text-text-body placeholder:text-text-secondary",
            "focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-amic",
            error
              ? "border-negative focus:ring-negative/20 focus:border-negative"
              : "border-gray-border hover:border-amic-400",
            className
          )}
          {...props}
        />
        {error && <p id={errorId} className="mt-1 text-xs text-negative">{error}</p>}
        {hint && !error && (
          <p id={hintId} className="mt-1 text-xs text-text-secondary">{hint}</p>
        )}
      </div>
    );
  }
);

Input.displayName = "Input";

export { Input };

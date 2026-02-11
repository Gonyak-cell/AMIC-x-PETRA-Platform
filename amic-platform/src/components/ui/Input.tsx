import { forwardRef } from "react";
import { cn } from "@/lib/cn";

export interface InputProps
  extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  hint?: string;
}

const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className, label, error, hint, id, ...props }, ref) => {
    const inputId = id || label?.toLowerCase().replace(/\s+/g, "-");

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
          className={cn(
            "w-full px-3 py-2 text-sm rounded-corporate border transition-colors",
            "bg-white text-text-body placeholder:text-text-secondary",
            "focus:outline-none focus:ring-2 focus:ring-amic/20 focus:border-amic",
            error
              ? "border-negative focus:ring-negative/20 focus:border-negative"
              : "border-gray-border hover:border-amic-400",
            className
          )}
          {...props}
        />
        {error && <p className="mt-1 text-xs text-negative">{error}</p>}
        {hint && !error && (
          <p className="mt-1 text-xs text-text-secondary">{hint}</p>
        )}
      </div>
    );
  }
);

Input.displayName = "Input";

export { Input };

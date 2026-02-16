import { forwardRef, useId } from "react";
import { ChevronDown } from "lucide-react";
import { cn } from "@/lib/cn";

export interface SelectOption {
  value: string;
  label: string;
}

export interface SelectProps
  extends React.SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  options: SelectOption[];
  error?: string;
  hint?: string;
  placeholder?: string;
}

const Select = forwardRef<HTMLSelectElement, SelectProps>(
  (
    { className, label, options, error, hint, id, placeholder, ...props },
    ref
  ) => {
    const autoId = useId();
    const selectId = id || autoId;
    const errorId = error ? `${selectId}-error` : undefined;
    const hintId = hint && !error ? `${selectId}-hint` : undefined;

    return (
      <div className="w-full">
        {label && (
          <label
            htmlFor={selectId}
            className="block text-sm font-medium text-text-body mb-1.5"
          >
            {label}
          </label>
        )}
        <div className="relative">
          <select
            ref={ref}
            id={selectId}
            aria-invalid={error ? true : undefined}
            aria-describedby={errorId || hintId}
            className={cn(
              "w-full px-3 py-2 text-sm rounded-dr-sm border transition-colors appearance-none shadow-sm",
              "bg-white text-text-body pr-10",
              "focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-amic",
              error
                ? "border-negative focus:ring-negative/20 focus:border-negative"
                : "border-gray-border hover:border-amic-400",
              className
            )}
            {...props}
          >
            {placeholder && (
              <option value="" disabled>
                {placeholder}
              </option>
            )}
            {options.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
          <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-text-secondary pointer-events-none" />
        </div>
        {error && <p id={errorId} className="mt-1 text-xs text-negative">{error}</p>}
        {hint && !error && (
          <p id={hintId} className="mt-1 text-xs text-text-secondary">{hint}</p>
        )}
      </div>
    );
  }
);

Select.displayName = "Select";

export { Select };

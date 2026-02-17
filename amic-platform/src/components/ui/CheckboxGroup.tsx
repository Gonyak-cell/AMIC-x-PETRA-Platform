import { useId } from "react";
import { cn } from "@/lib/cn";

export interface CheckboxGroupOption {
  value: string;
  label: string;
}

export interface CheckboxGroupProps {
  label: string;
  options: CheckboxGroupOption[];
  selected: string[];
  onChange: (selected: string[]) => void;
  layout?: "horizontal" | "vertical";
  className?: string;
}

function CheckboxGroup({
  label,
  options,
  selected,
  onChange,
  layout = "vertical",
  className,
}: CheckboxGroupProps) {
  const groupId = useId();

  const toggle = (value: string) => {
    if (selected.includes(value)) {
      onChange(selected.filter((v) => v !== value));
    } else {
      onChange([...selected, value]);
    }
  };

  return (
    <fieldset className={cn("min-w-0", className)}>
      <legend className="block text-sm font-medium text-text-body mb-1.5">
        {label}
      </legend>
      <div
        className={cn(
          "flex gap-x-4 gap-y-1.5",
          layout === "vertical" ? "flex-col" : "flex-row flex-wrap"
        )}
      >
        {options.map((opt) => {
          const id = `${groupId}-${opt.value}`;
          const checked = selected.includes(opt.value);
          return (
            <label
              key={opt.value}
              htmlFor={id}
              className={cn(
                "flex items-center gap-2 cursor-pointer text-sm select-none",
                "transition-colors hover:text-amic-600",
                checked ? "text-text-dark font-medium" : "text-text-body"
              )}
            >
              <input
                type="checkbox"
                id={id}
                checked={checked}
                onChange={() => toggle(opt.value)}
                className={cn(
                  "h-4 w-4 rounded border-gray-border text-amic",
                  "focus:ring-2 focus:ring-accent/30 focus:ring-offset-0",
                  "transition-colors cursor-pointer"
                )}
              />
              {opt.label}
            </label>
          );
        })}
      </div>
    </fieldset>
  );
}

CheckboxGroup.displayName = "CheckboxGroup";

export { CheckboxGroup };

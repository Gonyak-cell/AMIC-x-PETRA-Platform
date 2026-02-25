import { ChevronDown } from "lucide-react";
import { cn } from "@/lib/cn";

/** DataTable 셀 내 인라인 input/select 공용 스타일 */
export const INLINE_INPUT_CLS =
  "text-xs border border-gray-border rounded-dr-sm px-1.5 py-0.5 bg-transparent hover:bg-white focus:bg-white focus:ring-2 focus:ring-accent/30 focus:border-amic transition-colors";

export interface InlineSelectOption {
  value: string;
  label: string;
}

export interface InlineSelectProps {
  options: InlineSelectOption[];
  value: string;
  onChange: (value: string) => void;
  className?: string;
  disabled?: boolean;
}

export function InlineSelect({ options, value, onChange, className, disabled }: InlineSelectProps) {
  return (
    <div className="relative inline-flex items-center">
      <select
        className={cn(INLINE_INPUT_CLS, "pr-5 appearance-none cursor-pointer", className)}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
      >
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
      <ChevronDown className="absolute right-1 top-1/2 -translate-y-1/2 h-3 w-3 text-text-secondary pointer-events-none" />
    </div>
  );
}

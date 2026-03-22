import type { ButtonHTMLAttributes } from "react";
import type { LucideIcon } from "lucide-react";
import { Loader2 } from "lucide-react";
import { cn } from "@/lib/cn";

interface WorkspaceHeaderActionButtonProps
  extends ButtonHTMLAttributes<HTMLButtonElement> {
  icon: LucideIcon;
  label: string;
  active?: boolean;
  loading?: boolean;
}

export default function WorkspaceHeaderActionButton({
  icon: Icon,
  label,
  active = false,
  loading = false,
  className,
  disabled,
  ...props
}: WorkspaceHeaderActionButtonProps) {
  const isDisabled = disabled || loading;

  return (
    <button
      type="button"
      className={cn(
        "inline-flex items-center gap-2 rounded-dr-sm border px-3 py-1.5 text-sm font-medium transition-colors",
        active
          ? "border-accent bg-accent/10 text-accent"
          : "border-gray-border text-text-secondary hover:bg-bg-cool hover:text-text-dark",
        "disabled:cursor-not-allowed disabled:opacity-60",
        className,
      )}
      disabled={isDisabled}
      {...props}
    >
      {loading ? (
        <Loader2 className="h-4 w-4 animate-spin" />
      ) : (
        <Icon className="h-4 w-4" />
      )}
      <span>{label}</span>
    </button>
  );
}

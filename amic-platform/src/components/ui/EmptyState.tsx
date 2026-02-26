import type { LucideIcon } from "lucide-react";
import { FileQuestion } from "lucide-react";
import { cn } from "@/lib/cn";
import { Button } from "./Button";

export interface EmptyStateProps {
  icon?: LucideIcon;
  title: string;
  description?: string;
  actionLabel?: string;
  onAction?: () => void;
  className?: string;
}

export function EmptyState({
  icon: Icon = FileQuestion,
  title,
  description,
  actionLabel,
  onAction,
  className,
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center py-12 px-6 text-center",
        className
      )}
    >
      <div className="w-16 h-16 bg-bg-cool rounded-full flex items-center justify-center mb-4">
        <Icon className="h-8 w-8 text-text-secondary" />
      </div>
      <h3 className="text-lg font-heading font-semibold text-text-dark mb-1">
        {title}
      </h3>
      {description && (
        <p className="text-text-secondary text-sm max-w-sm mb-4">
          {description}
        </p>
      )}
      {actionLabel && onAction && (
        <Button variant="accent" onClick={onAction}>
          {actionLabel}
        </Button>
      )}
    </div>
  );
}

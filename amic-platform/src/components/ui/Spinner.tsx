import { cn } from "@/lib/cn";

export interface SpinnerProps {
  size?: "sm" | "md" | "lg";
  className?: string;
}

const sizeStyles = {
  sm: "h-4 w-4 border-2",
  md: "h-6 w-6 border-2",
  lg: "h-8 w-8 border-[3px]",
};

export function Spinner({ size = "md", className }: SpinnerProps) {
  return (
    <div
      className={cn(
        "animate-spin rounded-full border-amic border-t-transparent",
        sizeStyles[size],
        className
      )}
      role="status"
      aria-live="polite"
      aria-label="Loading"
    />
  );
}

/**
 * 전체 화면 로딩 오버레이
 */
export function LoadingOverlay({ message = "Loading..." }: { message?: string }) {
  return (
    <div className="fixed inset-0 bg-white/80 flex flex-col items-center justify-center z-50">
      <Spinner size="lg" />
      <p className="mt-4 text-text-secondary">{message}</p>
    </div>
  );
}

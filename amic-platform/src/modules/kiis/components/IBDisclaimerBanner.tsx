import { AlertTriangle } from "lucide-react";
import { cn } from "@/lib/cn";

interface IBDisclaimerBannerProps {
  text: string;
  className?: string;
}

export default function IBDisclaimerBanner({
  text,
  className,
}: IBDisclaimerBannerProps) {
  return (
    <div
      role="note"
      className={cn(
        "flex items-start gap-3 rounded-dr-sm border border-caution/30 bg-caution/5 px-4 py-3",
        className,
      )}
    >
      <AlertTriangle className="h-4 w-4 shrink-0 text-caution mt-0.5" />
      <p className="text-xs text-text-secondary leading-relaxed">{text}</p>
    </div>
  );
}

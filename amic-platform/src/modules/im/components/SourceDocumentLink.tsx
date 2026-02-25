import { FileText, ExternalLink } from "lucide-react";
import { cn } from "@/lib/cn";

export interface SourceDocumentLinkProps {
  docName: string | null;
  location: string | null;
  className?: string;
}

/**
 * Displays the VDR source document name and location info.
 * Renders as a compact inline badge with file icon.
 */
export function SourceDocumentLink({
  docName,
  location,
  className,
}: SourceDocumentLinkProps) {
  if (!docName) {
    return (
      <span className={cn("text-xs text-text-secondary italic", className)}>
        No source
      </span>
    );
  }

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 max-w-[220px]",
        className,
      )}
      title={`${docName}${location ? ` — ${location}` : ""}`}
    >
      <FileText className="h-3.5 w-3.5 text-amic flex-shrink-0" />
      <span className="text-xs text-text-dark truncate">{docName}</span>
      {location && (
        <span className="text-[10px] text-text-secondary flex-shrink-0">
          ({location})
        </span>
      )}
      <ExternalLink className="h-3 w-3 text-text-secondary flex-shrink-0" />
    </span>
  );
}

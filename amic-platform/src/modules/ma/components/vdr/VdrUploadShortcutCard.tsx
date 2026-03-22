import { ArrowRight, FolderUp } from "lucide-react";

import { Button } from "@/components/ui/Button";
import { cn } from "@/lib/cn";

interface VdrUploadShortcutCardProps {
  title: string;
  description: string;
  onOpen: () => void;
  actionLabel?: string;
  className?: string;
}

export default function VdrUploadShortcutCard({
  title,
  description,
  onOpen,
  actionLabel = "VDR에서 업로드",
  className,
}: VdrUploadShortcutCardProps) {
  return (
    <div
      className={cn(
        "rounded-lg border border-sky-200 bg-sky-50 px-4 py-4",
        className,
      )}
    >
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="space-y-1">
          <div className="flex items-center gap-2 text-sm font-medium text-sky-900">
            <FolderUp className="h-4 w-4" />
            {title}
          </div>
          <p className="text-sm text-sky-800">{description}</p>
        </div>

        <Button
          type="button"
          size="sm"
          variant="secondary"
          icon={ArrowRight}
          iconPosition="right"
          onClick={onOpen}
          className="whitespace-nowrap"
        >
          {actionLabel}
        </Button>
      </div>
    </div>
  );
}

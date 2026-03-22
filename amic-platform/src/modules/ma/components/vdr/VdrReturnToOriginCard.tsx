import { ArrowLeft, Upload } from "lucide-react";

import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";

interface VdrReturnToOriginCardProps {
  returnLabel?: string;
  onReturn: () => void;
}

export default function VdrReturnToOriginCard({
  returnLabel,
  onReturn,
}: VdrReturnToOriginCardProps) {
  return (
    <Card padding="md" className="border border-sky-200 bg-sky-50">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="space-y-1">
          <div className="flex items-center gap-2 text-sm font-medium text-sky-900">
            <Upload className="h-4 w-4" />
            Upload to VDR
          </div>
          <p className="text-sm text-sky-800">
            Drop files here to upload and auto-route them into the VDR.
          </p>
        </div>

        <Button
          type="button"
          size="sm"
          variant="secondary"
          onClick={onReturn}
          className="whitespace-nowrap"
        >
          <ArrowLeft className="mr-1.5 h-4 w-4" />
          {returnLabel ? `Back to ${returnLabel}` : "Go Back"}
        </Button>
      </div>
    </Card>
  );
}

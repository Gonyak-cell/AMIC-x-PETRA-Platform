import { Download, Lock } from "lucide-react";
import { toast } from "sonner";
import { Badge, Card, Button } from "@/components/ui";
import { formatDate } from "@/lib/format";
import { useFinalizeReportVersion } from "@/modules/fdd/hooks/useReportVersions";
import type { ReportVersion } from "@/modules/fdd/types/report-version";

interface ReportVersionCardProps {
  version: ReportVersion;
  dealId: string;
}

export default function ReportVersionCard({ version, dealId }: ReportVersionCardProps) {
  const finalizeMutation = useFinalizeReportVersion(dealId);

  const handleFinalize = async () => {
    try {
      await finalizeMutation.mutateAsync(version.version);
      toast.success(`Version ${version.version} finalized`);
    } catch {
      toast.error("Failed to finalize version");
    }
  };

  const downloadUrl = `/api/v1/deals/${dealId}/reports/versions/${version.version}/download`;

  return (
    <Card className="p-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="text-sm font-medium text-text-dark">
            v{version.version}
          </span>
          <Badge variant={version.status === "DRAFT" ? "warning" : "success"}>
            {version.status}
          </Badge>
          <span className="text-xs text-text-secondary">
            {version.file_format.toUpperCase()}
          </span>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs text-text-secondary">
            {version.created_by} &middot; {formatDate(version.created_at, "short")}
          </span>

          <a
            href={downloadUrl}
            target="_blank"
            rel="noopener noreferrer"
          >
            <Button variant="ghost" size="sm" icon={Download}>
              Download
            </Button>
          </a>

          {version.status === "DRAFT" && (
            <Button
              variant="secondary"
              size="sm"
              icon={Lock}
              onClick={handleFinalize}
              loading={finalizeMutation.isPending}
            >
              Finalize
            </Button>
          )}
        </div>
      </div>
    </Card>
  );
}

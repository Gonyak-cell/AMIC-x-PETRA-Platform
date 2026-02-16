import { useState } from "react";
import { Download, Lock } from "lucide-react";
import { toast } from "sonner";
import api from "@/api/client";
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
  const [downloading, setDownloading] = useState(false);

  const handleFinalize = async () => {
    try {
      await finalizeMutation.mutateAsync({ version: version.version });
      toast.success(`Version ${version.version} finalized`);
    } catch {
      toast.error("Failed to finalize version");
    }
  };

  const handleDownload = async () => {
    setDownloading(true);
    try {
      const { data } = await api.get(
        `/deals/${dealId}/reports/versions/${version.version}/download`,
        { responseType: "blob" },
      );
      const blob = new Blob([data]);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `FDD_Report_v${version.version}.${version.file_format}`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch {
      toast.error("Failed to download report");
    } finally {
      setDownloading(false);
    }
  };

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

          <Button
            variant="ghost"
            size="sm"
            icon={Download}
            onClick={handleDownload}
            loading={downloading}
          >
            Download
          </Button>

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

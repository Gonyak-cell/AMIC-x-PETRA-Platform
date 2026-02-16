import type { ReportVersion } from "@/types/report-version";
import ReportVersionCard from "./ReportVersionCard";

interface ReportVersionListProps {
  versions: ReportVersion[];
  dealId: string;
}

export default function ReportVersionList({ versions, dealId }: ReportVersionListProps) {
  return (
    <div className="space-y-3">
      {versions.map((version) => (
        <ReportVersionCard key={version.id} version={version} dealId={dealId} />
      ))}
    </div>
  );
}

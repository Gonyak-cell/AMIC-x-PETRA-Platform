import { useState } from "react";
import { FileOutput, CheckCircle, XCircle, HardDrive, AlertCircle } from "lucide-react";
import { useExports, useRedownload, useBatchDownload, useDeleteExport } from "@/hooks/useExports";
import { ExportFilterBar } from "@/components/exports/ExportFilterBar";
import { ExportTable } from "@/components/exports/ExportTable";
import { KpiCard, KpiCardSkeleton, EmptyState, PageHero } from "@/components/ui";
import type { ExportModule, ExportStatus, ExportRecord } from "@/types/export";
import heroImg from "@/assets/images/heroes/hero-arch-blue-wave.jpg";

export default function ExportsPage() {
  const [module, setModule] = useState<ExportModule | undefined>();
  const [status, setStatus] = useState<ExportStatus | undefined>();

  const { data, isLoading, endpointAvailable } = useExports({ module, status });
  const redownload = useRedownload();
  const batchDownload = useBatchDownload();
  const deleteExport = useDeleteExport();

  const records = data?.items ?? [];
  const completedCount = records.filter((r) => r.status === "completed").length;
  const failedCount = records.filter((r) => r.status === "failed").length;
  const totalSize = records.reduce(
    (sum, r) => sum + (r.file_size_bytes ?? 0),
    0,
  );

  return (
    <div className="space-y-6">
      {/* Hero Section */}
      <PageHero
        title="Data Export Hub"
        subtitle="Unified export history across M&A, Deal Doc Studio, and KIIS modules"
        backgroundImage={heroImg}
        backgroundOpacity={0.18}
        compact
      />

      {/* KPIs */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {isLoading ? (
          <>
            <KpiCardSkeleton />
            <KpiCardSkeleton />
            <KpiCardSkeleton />
            <KpiCardSkeleton />
          </>
        ) : (
          <>
            <KpiCard
              label="Total Exports"
              value={String(data?.total ?? 0)}
              icon={FileOutput}
              hoverLift
              generous
            />
            <KpiCard
              label="Completed"
              value={String(completedCount)}
              icon={CheckCircle}
              variant="positive"
              hoverLift
              generous
            />
            <KpiCard
              label="Failed"
              value={String(failedCount)}
              icon={XCircle}
              variant="negative"
              hoverLift
              generous
            />
            <KpiCard
              label="Storage Used"
              value={
                totalSize > 1_048_576
                  ? `${(totalSize / 1_048_576).toFixed(1)} MB`
                  : `${(totalSize / 1024).toFixed(1)} KB`
              }
              icon={HardDrive}
              hoverLift
              generous
            />
          </>
        )}
      </div>

      {/* Filters */}
      <ExportFilterBar
        module={module}
        status={status}
        onModuleChange={setModule}
        onStatusChange={setStatus}
      />

      {/* Table */}
      {!endpointAvailable ? (
        <EmptyState
          title="Export service is not yet available"
          description="The export backend endpoint is being set up. Exports will appear here once ready."
        />
      ) : records.length === 0 && !isLoading ? (
        <EmptyState
          title="No exports yet"
          description="Exports from M&A deal materials, Deal Doc Studio documents, and KIIS research will appear here."
        />
      ) : (
        <ExportTable
          records={records}
          onRedownload={(record: ExportRecord) => redownload.mutate(record)}
          onDelete={(id: string) => deleteExport.mutate(id)}
          onBatchDownload={(ids: string[]) => batchDownload.mutate(ids)}
          isRedownloading={redownload.isPending}
          isBatchDownloading={batchDownload.isPending}
        />
      )}

      {/* Retention notice */}
      <div className="flex items-center gap-2 text-sm text-text-secondary pt-4 border-t border-gray-border">
        <AlertCircle className="w-4 h-4" />
        <span>Exports are retained for 30 days before auto-deletion</span>
      </div>
    </div>
  );
}

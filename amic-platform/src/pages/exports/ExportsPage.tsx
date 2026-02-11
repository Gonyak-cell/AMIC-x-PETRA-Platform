import { useState } from "react";
import { FileOutput, CheckCircle, XCircle, HardDrive } from "lucide-react";
import { useExports, useRedownload, useBatchDownload, useDeleteExport } from "@/hooks/useExports";
import { ExportFilterBar } from "@/components/exports/ExportFilterBar";
import { ExportTable } from "@/components/exports/ExportTable";
import { KpiCard, KpiCardSkeleton, EmptyState } from "@/components/ui";
import type { ExportModule, ExportStatus, ExportRecord } from "@/types/export";

export default function ExportsPage() {
  const [module, setModule] = useState<ExportModule | undefined>();
  const [status, setStatus] = useState<ExportStatus | undefined>();

  const { data, isLoading } = useExports({ module, status });
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
      {/* Header */}
      <div>
        <h1 className="text-2xl font-heading font-bold text-text-dark">
          Data Export Hub
        </h1>
        <p className="text-sm text-text-secondary mt-1">
          Unified export history across FDD, KIIS, and IM modules
        </p>
      </div>

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
            />
            <KpiCard
              label="Completed"
              value={String(completedCount)}
              icon={CheckCircle}
              variant="positive"
            />
            <KpiCard
              label="Failed"
              value={String(failedCount)}
              icon={XCircle}
              variant="negative"
            />
            <KpiCard
              label="Storage Used"
              value={
                totalSize > 1_048_576
                  ? `${(totalSize / 1_048_576).toFixed(1)} MB`
                  : `${(totalSize / 1024).toFixed(1)} KB`
              }
              icon={HardDrive}
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
      {records.length === 0 && !isLoading ? (
        <EmptyState
          title="No exports yet"
          description="Exports from FDD reports, KIIS research, and IM documents will appear here."
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
    </div>
  );
}

import { useState } from "react";
import { Download, Trash2, Package } from "lucide-react";
import { DataTable, Badge, Button } from "@/components/ui";
import type { Column, BadgeVariant } from "@/components/ui";
import type { ExportRecord } from "@/types/export";
import { formatDate } from "@/lib/format";

const STATUS_VARIANT: Record<string, BadgeVariant> = {
  pending: "warning",
  completed: "success",
  failed: "error",
  expired: "neutral",
};

interface ExportTableProps {
  records: ExportRecord[];
  onRedownload: (record: ExportRecord) => void;
  onDelete: (id: string) => void;
  onBatchDownload: (ids: string[]) => void;
  isRedownloading?: boolean;
  isBatchDownloading?: boolean;
}

export function ExportTable({
  records,
  onRedownload,
  onDelete,
  onBatchDownload,
  isRedownloading,
  isBatchDownloading,
}: ExportTableProps) {
  const [selected, setSelected] = useState<Set<string>>(new Set());

  const toggleSelect = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const columns: Column<ExportRecord>[] = [
    {
      key: "_select",
      header: "",
      width: "40px",
      render: (row) => (
        <input
          type="checkbox"
          checked={selected.has(row.id)}
          onChange={() => toggleSelect(row.id)}
          className="rounded border-gray-border"
          aria-label={`Select ${row.name}`}
        />
      ),
    },
    { key: "name", header: "Name" },
    {
      key: "module",
      header: "Module",
      render: (row) => <Badge variant="info">{row.module.toUpperCase()}</Badge>,
    },
    {
      key: "format",
      header: "Format",
      render: (row) => (
        <span className="text-xs font-mono uppercase">{row.format}</span>
      ),
    },
    {
      key: "file_size_bytes",
      header: "Size",
      align: "right" as const,
      render: (row) =>
        row.file_size_bytes
          ? `${(row.file_size_bytes / 1024).toFixed(1)} KB`
          : "—",
    },
    {
      key: "status",
      header: "Status",
      render: (row) => (
        <Badge variant={STATUS_VARIANT[row.status]}>{row.status}</Badge>
      ),
    },
    {
      key: "created_at",
      header: "Created",
      render: (row) => formatDate(row.created_at, "short"),
    },
    {
      key: "_actions",
      header: "Actions",
      width: "120px",
      render: (row) => (
        <div className="flex gap-1">
          {row.status === "completed" && (
            <Button
              variant="ghost"
              size="sm"
              icon={Download}
              onClick={() => onRedownload(row)}
              loading={isRedownloading}
              aria-label={`Download ${row.name}`}
            />
          )}
          <Button
            variant="ghost"
            size="sm"
            icon={Trash2}
            onClick={() => onDelete(row.id)}
            aria-label={`Delete ${row.name}`}
          />
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-3">
      {/* Batch action bar */}
      {selected.size > 0 && (
        <div className="flex items-center gap-3 bg-bg-cool p-3 rounded-lg">
          <span className="text-sm text-text-secondary">
            {selected.size} item(s) selected
          </span>
          <Button
            variant="primary"
            size="sm"
            icon={Package}
            onClick={() => onBatchDownload(Array.from(selected))}
            loading={isBatchDownloading}
          >
            Download ZIP
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setSelected(new Set())}
          >
            Clear
          </Button>
        </div>
      )}

      <DataTable
        data={records}
        columns={columns}
        keyField="id"
        emptyMessage="No exports found."
        borderless={false}
      />
    </div>
  );
}

import { useState, useCallback } from "react";
import { useParams } from "react-router-dom";
import {
  Upload,
  FileSpreadsheet,
  CheckCircle,
  AlertCircle,
  Loader2,
  ChevronDown,
  ChevronUp,
  Play,
} from "lucide-react";
import { toast } from "sonner";
import {
  useUploads,
  useUploadFile,
  useConfirmType,
  useIngestUpload,
  useUploadDetail,
} from "@/modules/fdd/hooks/useUploads";
import type { UploadFile, UploadType, ValidationErrorItem } from "@/modules/fdd/types/deal";
import {
  Card,
  KpiCard,
  Button,
  Badge,
  Select,
  Spinner,
  PageHero,
} from "@/components/ui";
import type { SelectOption } from "@/components/ui";
import heroImg from "@/assets/images/heroes/hero-arch-dark-round.jpg";

const UPLOAD_TYPE_OPTIONS: SelectOption[] = [
  { value: "TB", label: "TB - Trial Balance" },
  { value: "GL", label: "GL - General Ledger" },
  { value: "AR", label: "AR - Accounts Receivable" },
  { value: "AP", label: "AP - Accounts Payable" },
  { value: "BANK", label: "BANK - Bank Statement" },
  { value: "DEBT", label: "DEBT - Debt Schedule" },
  { value: "LEASE", label: "LEASE - Lease Schedule" },
];

const STATUS_VARIANTS: Record<string, "success" | "warning" | "error" | "info" | "neutral"> = {
  PENDING: "neutral",
  DETECTING: "info",
  VALIDATING: "warning",
  INGESTING: "info",
  COMPLETED: "success",
  FAILED: "error",
};

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

// ── Validation Errors ────────────────────────────────────

function ValidationErrors({ errors }: { errors: ValidationErrorItem[] }) {
  if (errors.length === 0) return null;

  const errorList = errors.filter((e) => e.severity === "ERROR");
  const warnList = errors.filter((e) => e.severity === "WARNING");

  return (
    <div className="mt-3 space-y-2">
      {errorList.length > 0 && (
        <div className="bg-red-50 border border-negative/20 rounded-lg p-3">
          <p className="text-sm font-medium text-negative mb-2">
            Errors ({errorList.length})
          </p>
          <div className="space-y-1">
            {errorList.map((err) => (
              <div key={err.id} className="text-xs text-negative/80">
                <span className="font-mono">[{err.error_code}]</span>{" "}
                {err.field_name && (
                  <span className="font-medium">{err.field_name}: </span>
                )}
                {err.message}
                {err.row_number && (
                  <span className="text-negative/60"> (row {err.row_number})</span>
                )}
                {err.suggestion && (
                  <p className="text-negative/60 ml-4 mt-0.5">{err.suggestion}</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
      {warnList.length > 0 && (
        <div className="bg-amber-50 border border-caution/20 rounded-lg p-3">
          <p className="text-sm font-medium text-caution mb-2">
            Warnings ({warnList.length})
          </p>
          <div className="space-y-1">
            {warnList.map((err) => (
              <div key={err.id} className="text-xs text-caution/80">
                <span className="font-mono">[{err.error_code}]</span>{" "}
                {err.field_name && (
                  <span className="font-medium">{err.field_name}: </span>
                )}
                {err.message}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Upload Card ────────────────────────────────────────

function UploadCard({
  upload,
  dealId,
}: {
  upload: UploadFile;
  dealId: string;
}) {
  const [expanded, setExpanded] = useState(false);
  const [overrideType, setOverrideType] = useState<UploadType | "">(
    upload.confirmed_type || ""
  );
  const confirmType = useConfirmType(dealId);
  const ingest = useIngestUpload(dealId);
  const { data: detail } = useUploadDetail(
    dealId,
    expanded ? upload.id : null
  );

  const effectiveType = upload.confirmed_type || upload.detected_type;
  const canIngest =
    effectiveType !== null &&
    (upload.status === "PENDING" || upload.status === "FAILED");

  const isProcessing =
    upload.status === "INGESTING" ||
    upload.status === "VALIDATING" ||
    upload.status === "DETECTING";

  const handleTypeChange = (value: string) => {
    const val = value as UploadType;
    setOverrideType(val);
    if (val) {
      confirmType.mutate(
        { uploadId: upload.id, confirmedType: val },
        {
          onSuccess: () => toast.success("File type confirmed"),
          onError: () => toast.error("Failed to confirm type"),
        }
      );
    }
  };

  const handleIngest = () => {
    ingest.mutate(upload.id, {
      onSuccess: () => toast.success("Ingestion started"),
      onError: () => toast.error("Failed to start ingestion"),
    });
  };

  return (
    <div className="bg-white border border-gray-border rounded-lg p-4 shadow-card hover:shadow-card-hover transition-shadow">
      <div className="flex items-center justify-between">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-3">
            <FileSpreadsheet className="h-5 w-5 text-amic flex-shrink-0" />
            <h3 className="text-sm font-semibold text-text-dark truncate">
              {upload.original_filename}
            </h3>
            <Badge variant={STATUS_VARIANTS[upload.status] ?? "neutral"}>
              {upload.status}
            </Badge>
          </div>
          <div className="flex items-center gap-4 mt-2 text-xs text-text-secondary">
            <span>{formatBytes(upload.file_size_bytes)}</span>
            {upload.detected_type && (
              <span>
                Detected:{" "}
                <span className="font-medium text-text-body">
                  {upload.detected_type}
                </span>
                {upload.detection_confidence !== null && (
                  <span
                    className={`ml-1 ${
                      upload.detection_confidence >= 0.7
                        ? "text-positive"
                        : upload.detection_confidence >= 0.4
                          ? "text-caution"
                          : "text-negative"
                    }`}
                  >
                    ({Math.round(upload.detection_confidence * 100)}%)
                  </span>
                )}
              </span>
            )}
            {upload.confirmed_type && (
              <span className="text-amic">
                Confirmed:{" "}
                <span className="font-medium">{upload.confirmed_type}</span>
              </span>
            )}
            {upload.total_rows !== null && (
              <span>
                {upload.rows_processed ?? 0}/{upload.total_rows} rows
              </span>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2 ml-4">
          {upload.status === "PENDING" && (
            <Select
              value={overrideType}
              onChange={(e) => handleTypeChange(e.target.value)}
              options={UPLOAD_TYPE_OPTIONS}
              placeholder={
                upload.detected_type
                  ? `Auto: ${upload.detected_type}`
                  : "Select type..."
              }
              className="w-48"
            />
          )}

          {canIngest && (
            <Button
              variant="accent"
              size="sm"
              icon={Play}
              onClick={handleIngest}
              loading={ingest.isPending}
            >
              Ingest
            </Button>
          )}

          <Button
            variant="ghost"
            size="sm"
            icon={expanded ? ChevronUp : ChevronDown}
            onClick={() => setExpanded(!expanded)}
          >
            {expanded ? "Hide" : "Details"}
          </Button>
        </div>
      </div>

      {/* Progress bar */}
      {isProcessing && upload.total_rows && upload.rows_processed !== null && (
        <div className="mt-3">
          <div className="flex items-center justify-between text-xs text-text-secondary mb-1">
            <span>Processing...</span>
            <span>
              {Math.round((upload.rows_processed / upload.total_rows) * 100)}%
            </span>
          </div>
          <div className="w-full bg-bg-cool rounded-full h-2">
            <div
              className="bg-amic h-2 rounded-full transition-all duration-300"
              style={{
                width: `${Math.round((upload.rows_processed / upload.total_rows) * 100)}%`,
              }}
            />
          </div>
        </div>
      )}

      {/* Error message */}
      {upload.error_message && upload.status === "FAILED" && (
        <div className="mt-3 flex items-start gap-2 text-sm text-negative">
          <AlertCircle className="h-4 w-4 flex-shrink-0 mt-0.5" />
          <span>{upload.error_message}</span>
        </div>
      )}

      {/* Validation summary */}
      {upload.validation_summary && upload.status === "COMPLETED" && (
        <div className="mt-3 flex items-center gap-2 text-xs text-text-secondary">
          <CheckCircle className="h-4 w-4 text-positive" />
          <span>
            {upload.validation_summary.rows_ingested ?? 0} rows
            ingested
          </span>
          {(upload.validation_summary.total_warnings ?? 0) > 0 && (
            <Badge variant="warning">
              {upload.validation_summary.total_warnings} warnings
            </Badge>
          )}
        </div>
      )}

      {/* Expanded detail */}
      {expanded && detail && (
        <ValidationErrors errors={detail.validation_errors} />
      )}
    </div>
  );
}

// ── Main Upload Page ────────────────────────────────────

export default function UploadPage() {
  const { dealId } = useParams<{ dealId: string }>();
  const { data: uploads, isLoading } = useUploads(dealId!);
  const uploadFile = useUploadFile(dealId!);
  const [dragActive, setDragActive] = useState(false);

  const handleFiles = useCallback(
    (files: FileList | null) => {
      if (!files || files.length === 0) return;
      const file = files[0];
      const ext = file.name.split(".").pop()?.toLowerCase();
      if (ext !== "xlsx" && ext !== "xls") {
        toast.error("Only .xlsx and .xls files are supported");
        return;
      }
      uploadFile.mutate(file, {
        onSuccess: () => toast.success(`Uploaded: ${file.name}`),
        onError: () => toast.error(`Failed to upload: ${file.name}`),
      });
    },
    [uploadFile]
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragActive(false);
      handleFiles(e.dataTransfer.files);
    },
    [handleFiles]
  );

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragActive(true);
  }, []);

  const handleDragLeave = useCallback(() => {
    setDragActive(false);
  }, []);

  // KPI 계산
  const totalCount = uploads?.length ?? 0;
  const completedCount = uploads?.filter((u) => u.status === "COMPLETED").length ?? 0;
  const processingCount = uploads?.filter((u) =>
    ["DETECTING", "VALIDATING", "INGESTING"].includes(u.status)
  ).length ?? 0;
  const failedCount = uploads?.filter((u) => u.status === "FAILED").length ?? 0;

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Spinner size="lg" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <PageHero
        title="Data Uploads"
        subtitle="Upload Excel files for FDD analysis"
        compact
        backgroundImage={heroImg}
        backgroundOpacity={0.18}
      />

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard
          label="Total Files"
          value={String(totalCount)}
          icon={FileSpreadsheet}
        />
        <KpiCard
          label="Completed"
          value={String(completedCount)}
          variant="positive"
          icon={CheckCircle}
        />
        <KpiCard
          label="Processing"
          value={String(processingCount)}
          variant="caution"
          icon={Loader2}
        />
        <KpiCard
          label="Failed"
          value={String(failedCount)}
          variant={failedCount > 0 ? "negative" : "default"}
          icon={AlertCircle}
        />
      </div>

      {/* Drop Zone */}
      <Card padding="none">
        <div
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
            dragActive
              ? "border-amic bg-bg-light-green"
              : "border-gray-border bg-bg-cool hover:border-amic-300"
          }`}
        >
          <Upload
            className={`h-12 w-12 mx-auto mb-4 ${
              dragActive ? "text-amic" : "text-text-secondary"
            }`}
          />
          <div className="text-text-body">
            <p className="text-base font-medium">
              {uploadFile.isPending
                ? "Uploading..."
                : "Drag & drop an Excel file here"}
            </p>
            <p className="text-sm text-text-secondary mt-1">
              or click to select a file
            </p>
            <p className="text-xs text-text-secondary mt-2">
              Supported formats: .xlsx, .xls
            </p>
          </div>
          <input
            type="file"
            accept=".xlsx,.xls"
            onChange={(e) => handleFiles(e.target.files)}
            className="sr-only"
            id="file-upload"
            aria-label="Upload Excel file"
            disabled={uploadFile.isPending}
          />
          <label htmlFor="file-upload">
            <Button
              variant="secondary"
              className="mt-4"
              disabled={uploadFile.isPending}
              onClick={() => document.getElementById("file-upload")?.click()}
            >
              Select File
            </Button>
          </label>
        </div>
      </Card>

      {/* Upload List */}
      {uploads && uploads.length > 0 ? (
        <div className="space-y-3">
          <h3 className="text-sm font-heading font-semibold text-text-dark">
            Uploaded Files ({uploads.length})
          </h3>
          {uploads.map((upload) => (
            <UploadCard key={upload.id} upload={upload} dealId={dealId!} />
          ))}
        </div>
      ) : (
        <Card>
          <div className="text-center py-8 text-text-secondary">
            <FileSpreadsheet className="h-12 w-12 mx-auto mb-3 opacity-50" />
            <p className="text-sm">No files uploaded yet</p>
            <p className="text-xs mt-1">
              Upload your first file to start the FDD analysis
            </p>
          </div>
        </Card>
      )}
    </div>
  );
}

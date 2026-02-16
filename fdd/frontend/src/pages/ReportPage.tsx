import { useState } from "react";
import { useParams } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import {
  FileOutput,
  Eye,
  Download,
  FileJson,
  Presentation,
} from "lucide-react";
import { toast } from "sonner";
import api from "@/api/client";
import {
  Card,
  Button,
  Badge,
  DataTable,
  Spinner,
  EmptyState,
} from "@/components/ui";
import type { Column } from "@/components/ui";
import { useReportVersions } from "@/hooks/useReportVersions";
import ReportVersionList from "@/components/report/ReportVersionList";

interface ReportPreview {
  deal_id: string;
  deal_name: string;
  sections_count: number;
  sections: { type: string; title?: string }[];
}

interface ReportSection {
  type: string;
  title?: string;
}

export default function ReportPage() {
  const { dealId } = useParams<{ dealId: string }>();
  const { data: versions = [] } = useReportVersions(dealId!);
  const [preview, setPreview] = useState<ReportPreview | null>(null);
  const [options, setOptions] = useState({
    include_qoe: true,
    include_nwc: true,
    include_debt: true,
    include_issues: true,
    format: "pptx",
  });

  // Preview mutation
  const previewMutation = useMutation({
    mutationFn: async () => {
      const params = new URLSearchParams({
        include_qoe: String(options.include_qoe),
        include_nwc: String(options.include_nwc),
        include_debt: String(options.include_debt),
        include_issues: String(options.include_issues),
      });
      const { data } = await api.get<ReportPreview>(
        `/deals/${dealId}/reports/preview?${params}`
      );
      return data;
    },
    onSuccess: (data) => {
      setPreview(data);
      toast.success(`Preview generated: ${data.sections_count} sections`);
    },
    onError: () => {
      toast.error("Failed to generate preview");
    },
  });

  // Generate mutation
  const generateMutation = useMutation({
    mutationFn: async () => {
      const response = await api.post(
        `/deals/${dealId}/reports/generate`,
        { ...options },
        { responseType: options.format === "pptx" ? "blob" : "json" }
      );

      if (options.format === "pptx") {
        // Download PPTX file
        const blob = new Blob([response.data], {
          type: "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `FDD_Report_${dealId}.pptx`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
      }

      return response.data;
    },
    onSuccess: () => {
      toast.success(
        options.format === "pptx"
          ? "Report downloaded successfully"
          : "Report IR generated"
      );
    },
    onError: () => {
      toast.error("Failed to generate report");
    },
  });

  if (!dealId) {
    return <div className="p-4 text-negative">Deal ID not found</div>;
  }

  // Preview 테이블 컬럼
  const previewColumns: Column<ReportSection>[] = [
    {
      key: "index",
      header: "#",
      width: "60px",
      render: (_, index) => (
        <span className="text-text-secondary">{index + 1}</span>
      ),
    },
    {
      key: "type",
      header: "Type",
      width: "140px",
      render: (row) => <Badge variant="info">{row.type}</Badge>,
    },
    {
      key: "title",
      header: "Title",
      render: (row) => (
        <span className="text-text-dark">{row.title || "-"}</span>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-heading font-bold text-text-dark">
          Report Generation
        </h1>
        <p className="text-text-secondary mt-1">
          Generate FDD report in PowerPoint or JSON format
        </p>
      </div>

      {/* Options */}
      <Card title="Report Options" headerBar>
        <div className="space-y-6">
          {/* Section Selection */}
          <div>
            <h4 className="text-sm font-heading font-semibold text-text-dark mb-4">
              Include Sections
            </h4>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <label className="flex items-center gap-3 text-sm text-text-body cursor-pointer p-3 rounded-lg border border-gray-border hover:border-amic transition-colors">
                <input
                  type="checkbox"
                  checked={options.include_qoe}
                  onChange={(e) =>
                    setOptions({ ...options, include_qoe: e.target.checked })
                  }
                  className="rounded border-gray-border text-amic focus:ring-amic h-4 w-4"
                />
                QoE Analysis
              </label>

              <label className="flex items-center gap-3 text-sm text-text-body cursor-pointer p-3 rounded-lg border border-gray-border hover:border-amic transition-colors">
                <input
                  type="checkbox"
                  checked={options.include_nwc}
                  onChange={(e) =>
                    setOptions({ ...options, include_nwc: e.target.checked })
                  }
                  className="rounded border-gray-border text-amic focus:ring-amic h-4 w-4"
                />
                NWC Analysis
              </label>

              <label className="flex items-center gap-3 text-sm text-text-body cursor-pointer p-3 rounded-lg border border-gray-border hover:border-amic transition-colors">
                <input
                  type="checkbox"
                  checked={options.include_debt}
                  onChange={(e) =>
                    setOptions({ ...options, include_debt: e.target.checked })
                  }
                  className="rounded border-gray-border text-amic focus:ring-amic h-4 w-4"
                />
                Net Debt Analysis
              </label>

              <label className="flex items-center gap-3 text-sm text-text-body cursor-pointer p-3 rounded-lg border border-gray-border hover:border-amic transition-colors">
                <input
                  type="checkbox"
                  checked={options.include_issues}
                  onChange={(e) =>
                    setOptions({ ...options, include_issues: e.target.checked })
                  }
                  className="rounded border-gray-border text-amic focus:ring-amic h-4 w-4"
                />
                Issue Log
              </label>
            </div>
          </div>

          {/* Format Selection */}
          <div className="border-t border-gray-border pt-4">
            <h4 className="text-sm font-heading font-semibold text-text-dark mb-4">
              Output Format
            </h4>
            <div className="flex gap-4">
              <label
                className={`flex items-center gap-3 text-sm cursor-pointer p-4 rounded-lg border-2 transition-colors ${
                  options.format === "pptx"
                    ? "border-amic bg-bg-light-green"
                    : "border-gray-border hover:border-amic-300"
                }`}
              >
                <input
                  type="radio"
                  name="format"
                  value="pptx"
                  checked={options.format === "pptx"}
                  onChange={(e) =>
                    setOptions({ ...options, format: e.target.value })
                  }
                  className="sr-only"
                />
                <Presentation
                  className={`h-5 w-5 ${
                    options.format === "pptx" ? "text-amic" : "text-text-secondary"
                  }`}
                />
                <div>
                  <div className="font-medium text-text-dark">PowerPoint</div>
                  <div className="text-xs text-text-secondary">.pptx file</div>
                </div>
              </label>

              <label
                className={`flex items-center gap-3 text-sm cursor-pointer p-4 rounded-lg border-2 transition-colors ${
                  options.format === "json"
                    ? "border-amic bg-bg-light-green"
                    : "border-gray-border hover:border-amic-300"
                }`}
              >
                <input
                  type="radio"
                  name="format"
                  value="json"
                  checked={options.format === "json"}
                  onChange={(e) =>
                    setOptions({ ...options, format: e.target.value })
                  }
                  className="sr-only"
                />
                <FileJson
                  className={`h-5 w-5 ${
                    options.format === "json" ? "text-amic" : "text-text-secondary"
                  }`}
                />
                <div>
                  <div className="font-medium text-text-dark">JSON</div>
                  <div className="text-xs text-text-secondary">Report IR</div>
                </div>
              </label>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex gap-4 pt-4 border-t border-gray-border">
            <Button
              variant="secondary"
              icon={Eye}
              onClick={() => previewMutation.mutate()}
              loading={previewMutation.isPending}
            >
              Preview
            </Button>

            <Button
              variant="accent"
              icon={Download}
              onClick={() => generateMutation.mutate()}
              loading={generateMutation.isPending}
            >
              Generate Report
            </Button>
          </div>
        </div>
      </Card>

      {/* Preview */}
      {preview && (
        <Card title="Report Preview" headerBar padding="none">
          <div className="p-4 border-b border-gray-border bg-bg-cool">
            <div className="flex items-center gap-6">
              <div>
                <span className="text-xs text-text-secondary">Deal:</span>
                <span className="ml-2 font-medium text-text-dark">
                  {preview.deal_name}
                </span>
              </div>
              <div>
                <span className="text-xs text-text-secondary">Sections:</span>
                <span className="ml-2 font-medium text-text-dark">
                  {preview.sections_count}
                </span>
              </div>
            </div>
          </div>
          <DataTable
            columns={previewColumns}
            data={preview.sections}
            keyField="type"
            striped
            compact
            emptyMessage="No sections in preview"
          />
        </Card>
      )}

      {/* No Preview Yet */}
      {!preview && !previewMutation.isPending && (
        <Card>
          <EmptyState
            icon={FileOutput}
            title="No Preview"
            description="Click 'Preview' to see the report structure before generating."
            actionLabel="Preview Report"
            onAction={() => previewMutation.mutate()}
          />
        </Card>
      )}

      {/* Loading State */}
      {(previewMutation.isPending || generateMutation.isPending) && (
        <Card>
          <div className="flex items-center justify-center py-8">
            <Spinner size="lg" />
            <span className="ml-3 text-text-secondary">
              {previewMutation.isPending
                ? "Generating preview..."
                : "Generating report..."}
            </span>
          </div>
        </Card>
      )}

      {/* Error State */}
      {(previewMutation.error || generateMutation.error) && (
        <div className="bg-red-50 border border-negative/20 rounded-lg p-4 text-sm text-negative">
          Failed to process report. Please check if all analyses are completed.
        </div>
      )}

      {/* Version History */}
      <Card title="Version History" headerBar>
        {versions.length === 0 ? (
          <EmptyState
            icon={FileOutput}
            title="No Report Versions"
            description="Generate a report to create your first version."
          />
        ) : (
          <ReportVersionList versions={versions} dealId={dealId!} />
        )}
      </Card>
    </div>
  );
}

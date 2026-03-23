import { useState } from "react";
import {
  AlertTriangle,
  CheckCircle,
  Clock,
  Loader2,
  RefreshCw,
  Sparkles,
  XCircle,
} from "lucide-react";

import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { useExtractions } from "@/modules/ma/hooks/useDocumentExtraction";
import {
  CATEGORY_LABELS,
  getExtractionStatusLabel,
  hasMeaningfulExtractionData,
} from "@/modules/ma/types/document_extraction";
import type {
  DocumentExtraction,
  ExtractionStatus,
} from "@/modules/ma/types/document_extraction";

import ExtractionReviewModal from "./ExtractionReviewModal";

interface Props {
  txnId: string;
}

const STATUS_BADGE: Record<
  ExtractionStatus,
  {
    variant: "info" | "warning" | "success" | "error" | "neutral";
    icon: typeof Sparkles;
  }
> = {
  PENDING: { variant: "neutral", icon: Clock },
  CLASSIFYING: { variant: "info", icon: Loader2 },
  EXTRACTING: { variant: "info", icon: Loader2 },
  COMPLETED: { variant: "warning", icon: Sparkles },
  FAILED: { variant: "error", icon: XCircle },
  CONFIRMED: { variant: "success", icon: CheckCircle },
};

export default function ExtractionList({ txnId }: Props) {
  const { data, isLoading, isError, refetch } = useExtractions(txnId);
  const [selectedExtraction, setSelectedExtraction] =
    useState<DocumentExtraction | null>(null);

  const items = data?.items ?? [];
  const hasCachedData = data != null;

  if (isLoading && !hasCachedData) {
    return (
      <Card padding="md">
        <div className="flex items-center gap-2 text-sm text-text-secondary">
          <Loader2 className="h-4 w-4 animate-spin" />
          Loading AI extraction results...
        </div>
      </Card>
    );
  }

  if (isError && !hasCachedData) {
    return (
      <Card padding="md" className="border border-red-200 bg-red-50">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-start gap-3">
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-red-500" />
            <div className="space-y-1">
              <p className="text-sm font-medium text-red-900">
                AI extraction results could not be loaded.
              </p>
              <p className="text-sm text-red-800">
                Retry without leaving the VDR workspace.
              </p>
            </div>
          </div>
          <Button
            type="button"
            size="sm"
            variant="secondary"
            onClick={() => void refetch()}
          >
            <RefreshCw className="h-4 w-4" />
            Retry
          </Button>
        </div>
      </Card>
    );
  }

  if (items.length === 0) {
    return (
      <Card padding="md">
        <div className="py-4 text-center text-sm text-text-secondary">
          <Sparkles className="mx-auto mb-2 h-5 w-5 text-text-tertiary" />
          No AI extraction results yet. Start an extraction from a VDR document.
        </div>
      </Card>
    );
  }

  return (
    <>
      {isError && (
        <Card padding="sm" className="mb-3 border border-amber-200 bg-amber-50">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <p className="text-sm text-amber-800">
              Showing the last loaded extraction results while refresh retries.
            </p>
            <Button
              type="button"
              size="sm"
              variant="secondary"
              onClick={() => void refetch()}
            >
              <RefreshCw className="h-4 w-4" />
              Refresh
            </Button>
          </div>
        </Card>
      )}

      <Card padding="none">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-border bg-bg-cool">
                <th className="px-4 py-2.5 text-left font-medium text-text-secondary">
                  Document ID
                </th>
                <th className="px-4 py-2.5 text-left font-medium text-text-secondary">
                  Category
                </th>
                <th className="px-4 py-2.5 text-left font-medium text-text-secondary">
                  Status
                </th>
                <th className="px-4 py-2.5 text-center font-medium text-text-secondary">
                  Confidence
                </th>
                <th className="px-4 py-2.5 text-right font-medium text-text-secondary">
                  Cost
                </th>
                <th className="px-4 py-2.5 text-left font-medium text-text-secondary">
                  Reviewer
                </th>
              </tr>
            </thead>
            <tbody>
              {items.map((extraction) => {
                const badge = STATUS_BADGE[extraction.status];
                const Icon = badge.icon;
                const isSpinning =
                  extraction.status === "CLASSIFYING" ||
                  extraction.status === "EXTRACTING";
                const hasMeaningfulData = hasMeaningfulExtractionData(
                  extraction.extracted_data,
                );

                return (
                  <tr
                    key={extraction.id}
                    className="cursor-pointer border-b border-gray-border last:border-0 hover:bg-bg-cool/50 transition-colors"
                    onClick={() => setSelectedExtraction(extraction)}
                  >
                    <td className="px-4 py-3 font-mono text-xs text-text-secondary">
                      {extraction.vdr_document_id.slice(0, 8)}...
                    </td>
                    <td className="px-4 py-3">
                      {extraction.doc_category ? (
                        <Badge variant="info">
                          {CATEGORY_LABELS[extraction.doc_category] ??
                            extraction.doc_category}
                        </Badge>
                      ) : (
                        <span className="text-text-tertiary">-</span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <Badge
                        variant={
                          extraction.status === "COMPLETED" && !hasMeaningfulData
                            ? "neutral"
                            : badge.variant
                        }
                      >
                        <Icon
                          className={`mr-1 h-3 w-3 ${isSpinning ? "animate-spin" : ""}`}
                        />
                        {getExtractionStatusLabel(
                          extraction.status,
                          extraction.extracted_data,
                        )}
                      </Badge>
                    </td>
                    <td className="px-4 py-3 text-center">
                      {extraction.classification_confidence != null
                        ? `${Math.round(extraction.classification_confidence * 100)}%`
                        : "-"}
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-xs">
                      {extraction.llm_cost_usd > 0
                        ? `$${extraction.llm_cost_usd.toFixed(3)}`
                        : "-"}
                    </td>
                    <td className="px-4 py-3 text-xs text-text-secondary">
                      {extraction.reviewed_by_email ?? "-"}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Card>

      <ExtractionReviewModal
        txnId={txnId}
        extraction={selectedExtraction}
        open={selectedExtraction !== null}
        onClose={() => setSelectedExtraction(null)}
      />
    </>
  );
}

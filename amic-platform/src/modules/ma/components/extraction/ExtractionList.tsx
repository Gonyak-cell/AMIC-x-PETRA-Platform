import { useState } from "react";
import { Sparkles, Loader2, CheckCircle, XCircle, Clock } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { useExtractions } from "@/modules/ma/hooks/useDocumentExtraction";
import {
  CATEGORY_LABELS,
  STATUS_LABELS,
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
  { variant: "info" | "warning" | "success" | "error" | "neutral"; icon: typeof Sparkles }
> = {
  PENDING: { variant: "neutral", icon: Clock },
  CLASSIFYING: { variant: "info", icon: Loader2 },
  EXTRACTING: { variant: "info", icon: Loader2 },
  COMPLETED: { variant: "warning", icon: Sparkles },
  FAILED: { variant: "error", icon: XCircle },
  CONFIRMED: { variant: "success", icon: CheckCircle },
};

export default function ExtractionList({ txnId }: Props) {
  const { data, isLoading } = useExtractions(txnId);
  const [selectedExtraction, setSelectedExtraction] =
    useState<DocumentExtraction | null>(null);

  const items = data?.items ?? [];

  if (isLoading) {
    return (
      <Card padding="md">
        <div className="flex items-center gap-2 text-text-secondary text-sm">
          <Loader2 className="h-4 w-4 animate-spin" />
          AI 분석 결과 로딩 중...
        </div>
      </Card>
    );
  }

  if (items.length === 0) {
    return (
      <Card padding="md">
        <div className="text-sm text-text-secondary text-center py-4">
          <Sparkles className="h-5 w-5 mx-auto mb-2 text-text-tertiary" />
          AI 분석 결과가 없습니다. VDR 문서에서 "AI 분석" 버튼을 클릭하세요.
        </div>
      </Card>
    );
  }

  return (
    <>
      <Card padding="none">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-bg-cool border-b border-gray-border">
                <th className="px-4 py-2.5 text-left font-medium text-text-secondary">
                  문서 ID
                </th>
                <th className="px-4 py-2.5 text-left font-medium text-text-secondary">
                  분류
                </th>
                <th className="px-4 py-2.5 text-left font-medium text-text-secondary">
                  상태
                </th>
                <th className="px-4 py-2.5 text-center font-medium text-text-secondary">
                  신뢰도
                </th>
                <th className="px-4 py-2.5 text-right font-medium text-text-secondary">
                  비용
                </th>
                <th className="px-4 py-2.5 text-left font-medium text-text-secondary">
                  검토자
                </th>
              </tr>
            </thead>
            <tbody>
              {items.map((ext) => {
                const badge = STATUS_BADGE[ext.status];
                const Icon = badge.icon;
                const isSpinning =
                  ext.status === "CLASSIFYING" ||
                  ext.status === "EXTRACTING";

                return (
                  <tr
                    key={ext.id}
                    className="border-b border-gray-border last:border-0 hover:bg-bg-cool/50 cursor-pointer transition-colors"
                    onClick={() => setSelectedExtraction(ext)}
                  >
                    <td className="px-4 py-3 font-mono text-xs text-text-secondary">
                      {ext.vdr_document_id.slice(0, 8)}...
                    </td>
                    <td className="px-4 py-3">
                      {ext.doc_category ? (
                        <Badge variant="info">
                          {CATEGORY_LABELS[ext.doc_category] ??
                            ext.doc_category}
                        </Badge>
                      ) : (
                        <span className="text-text-tertiary">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <Badge variant={badge.variant}>
                        <Icon
                          className={`h-3 w-3 mr-1 ${isSpinning ? "animate-spin" : ""}`}
                        />
                        {STATUS_LABELS[ext.status]}
                      </Badge>
                    </td>
                    <td className="px-4 py-3 text-center">
                      {ext.classification_confidence != null
                        ? `${Math.round(ext.classification_confidence * 100)}%`
                        : "—"}
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-xs">
                      {ext.llm_cost_usd > 0
                        ? `$${ext.llm_cost_usd.toFixed(3)}`
                        : "—"}
                    </td>
                    <td className="px-4 py-3 text-xs text-text-secondary">
                      {ext.reviewed_by_email ?? "—"}
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
        open={!!selectedExtraction}
        onClose={() => setSelectedExtraction(null)}
      />
    </>
  );
}

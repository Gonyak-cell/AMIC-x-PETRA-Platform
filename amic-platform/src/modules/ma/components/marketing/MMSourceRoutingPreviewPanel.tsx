import { AlertTriangle, Download, FileSearch, Files, Filter } from "lucide-react";
import { useMemo, useState } from "react";

import { Button, Card, DataTable, EmptyState } from "@/components/ui";
import { useMarketingMaterialSourceRoutingPreview } from "@/modules/ma/hooks/useMarketingMaterials";
import { getVdrDownloadUrl } from "@/modules/ma/hooks/useVdr";
import type {
  MarketingDocType,
  MarketingMaterialSourceRoutingDocument,
} from "@/modules/ma/types/marketing_material";
import { MARKETING_DOC_LABELS } from "@/modules/ma/types/marketing_material";
import {
  VDR_CATEGORY_LABELS,
  VDR_WORKSTREAM_LABELS,
} from "@/modules/ma/types/vdr";

const PREVIEW_DOC_TYPES: MarketingDocType[] = ["TM", "DM", "IM"];

function formatWorkstream(value: string): string {
  return (
    VDR_WORKSTREAM_LABELS[value as keyof typeof VDR_WORKSTREAM_LABELS] ?? value
  );
}

function getStatusTone(document: MarketingMaterialSourceRoutingDocument): string {
  if (document.include_for_marketing_material) {
    return "bg-accent/10 text-accent";
  }
  return "bg-slate-100 text-slate-600";
}

export default function MMSourceRoutingPreviewPanel({
  txnId,
}: {
  txnId: string;
}) {
  const [previewDocType, setPreviewDocType] = useState<MarketingDocType>("IM");
  const { data, isLoading, isError } = useMarketingMaterialSourceRoutingPreview(
    txnId,
    previewDocType,
  );

  const documents = useMemo(() => {
    const items = [...(data?.documents ?? [])];
    return items.sort((a, b) => {
      const includeDelta =
        Number(Boolean(b.include_for_marketing_material)) -
        Number(Boolean(a.include_for_marketing_material));
      if (includeDelta !== 0) return includeDelta;
      const manualDelta =
        Number(a.requires_manual_review) - Number(b.requires_manual_review);
      if (manualDelta !== 0) return manualDelta;
      return b.confidence - a.confidence;
    });
  }, [data?.documents]);

  const summary = data?.summary;
  const includedCount =
    summary?.included_for_marketing_material ??
    documents.filter((document) => document.include_for_marketing_material)
      .length;
  const excludedCount =
    summary?.excluded_from_marketing_material ??
    documents.filter((document) => !document.include_for_marketing_material)
      .length;

  return (
    <Card
      padding="none"
      className="overflow-hidden border-accent/15 bg-gradient-to-br from-[#f6fbf7] via-white to-[#fbfdfb] shadow-dr-md"
    >
      <div className="flex flex-col gap-4 px-5 py-5">
        <div className="flex flex-col justify-between gap-3 lg:flex-row lg:items-start">
          <div>
            <h4 className="text-base font-semibold text-text-dark">
              VDR 입력 파일
            </h4>
            <p className="mt-1 text-sm text-text-secondary">
              현재 VDR에서 마케팅 자료 생성 후보로 분류된 문서와 라우팅 내역을
              미리 보여줍니다.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            {PREVIEW_DOC_TYPES.map((docType) => (
              <Button
                key={docType}
                type="button"
                size="sm"
                variant={previewDocType === docType ? "accent" : "secondary"}
                onClick={() => setPreviewDocType(docType)}
              >
                {MARKETING_DOC_LABELS[docType]}
              </Button>
            ))}
          </div>
        </div>

        <div className="grid gap-3 md:grid-cols-3">
          <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3">
            <div className="flex items-center gap-2 text-[11px] uppercase tracking-[0.14em] text-text-secondary">
              <Files className="h-3.5 w-3.5" />
              포함 문서
            </div>
            <p className="mt-2 text-2xl font-semibold text-text-dark">
              {includedCount}
            </p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3">
            <div className="flex items-center gap-2 text-[11px] uppercase tracking-[0.14em] text-text-secondary">
              <Filter className="h-3.5 w-3.5" />
              제외 문서
            </div>
            <p className="mt-2 text-2xl font-semibold text-text-dark">
              {excludedCount}
            </p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3">
            <div className="flex items-center gap-2 text-[11px] uppercase tracking-[0.14em] text-text-secondary">
              <AlertTriangle className="h-3.5 w-3.5" />
              수동 검토
            </div>
            <p className="mt-2 text-2xl font-semibold text-text-dark">
              {summary?.manual_review_documents ?? 0}
            </p>
          </div>
        </div>

        {isError ? (
          <div className="rounded-xl border border-red-100 bg-red-50 px-4 py-3 text-sm text-red-700">
            마케팅 자료용 VDR 입력 파일을 불러오지 못했습니다.
          </div>
        ) : documents.length === 0 && !isLoading ? (
          <EmptyState
            icon={FileSearch}
            title="아직 분류된 입력 문서가 없습니다"
            description={`${MARKETING_DOC_LABELS[previewDocType]} 생성 후보로 포함된 VDR 문서가 없으면 여기에 표시되지 않습니다.`}
          />
        ) : (
          <DataTable<MarketingMaterialSourceRoutingDocument>
            columns={[
              {
                key: "original_name",
                header: "문서명",
                render: (row) => (
                  <div className="min-w-0">
                    <a
                      href={getVdrDownloadUrl(txnId, row.document_id)}
                      className="truncate text-sm font-medium text-amic hover:underline"
                      title={row.original_name}
                      target="_blank"
                      rel="noreferrer"
                    >
                      {row.original_name}
                    </a>
                    <p className="mt-1 text-xs text-text-secondary">
                      {VDR_CATEGORY_LABELS[
                        row.folder_category as keyof typeof VDR_CATEGORY_LABELS
                      ] ?? row.folder_category}
                    </p>
                  </div>
                ),
              },
              {
                key: "primary_workstream",
                header: "워크스트림",
                width: "240px",
                render: (row) => (
                  <div className="space-y-1">
                    <div className="flex flex-wrap gap-1">
                      {row.workstream_tags.map((tag) => (
                        <span
                          key={`${row.document_id}-${tag}`}
                          className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-medium text-slate-600"
                        >
                          {formatWorkstream(tag)}
                        </span>
                      ))}
                    </div>
                    <p className="text-xs text-text-secondary">
                      Primary {formatWorkstream(row.primary_workstream)} ·{" "}
                      {Math.round(row.confidence * 100)}%
                    </p>
                  </div>
                ),
              },
              {
                key: "status",
                header: "상태",
                width: "190px",
                render: (row) => (
                  <div className="flex flex-wrap gap-1.5">
                    <span
                      className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${getStatusTone(row)}`}
                    >
                      {row.include_for_marketing_material
                        ? "마케팅 자료 입력 포함"
                        : "입력 제외"}
                    </span>
                    {row.requires_manual_review && (
                      <span className="rounded-full bg-amber-50 px-2 py-0.5 text-[11px] font-semibold text-amber-700">
                        수동 검토 필요
                      </span>
                    )}
                  </div>
                ),
              },
              {
                key: "details",
                header: "내역",
                render: (row) => (
                  <div className="space-y-1 text-xs text-text-secondary">
                    <p>
                      DDRL 섹션:{" "}
                      {row.ddrl_sections.length > 0
                        ? row.ddrl_sections.join(", ")
                        : "없음"}
                    </p>
                    {row.is_override && (
                      <p className="text-amber-700">
                        수동 override
                        {row.override_note ? ` · ${row.override_note}` : ""}
                      </p>
                    )}
                  </div>
                ),
              },
              {
                key: "download",
                header: "",
                width: "110px",
                align: "right",
                render: (row) => (
                  <a
                    href={getVdrDownloadUrl(txnId, row.document_id)}
                    className="inline-flex items-center gap-1 text-xs font-medium text-amic hover:underline"
                    target="_blank"
                    rel="noreferrer"
                  >
                    <Download className="h-3.5 w-3.5" />
                    다운로드
                  </a>
                ),
              },
            ]}
            data={documents}
            keyField="document_id"
            loading={isLoading}
            emptyMessage="표시할 입력 문서가 없습니다."
          />
        )}
      </div>
    </Card>
  );
}

import { useState } from "react";
import { Columns, AlignLeft, Sparkles, Download, FileText } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Skeleton } from "@/components/ui/Skeleton";
import type { MarkupComparison } from "@/modules/ma/types/negotiation_workspace";
import type { ContractMarkup } from "@/modules/ma/types/contract_markup";

interface MarkupComparisonPanelProps {
  txnId: string;
  contractId: string;
  comparison: MarkupComparison | null;
  markupA: ContractMarkup | null;
  markupB: ContractMarkup | null;
  isLoading: boolean;
  onRequestAIInsight: (clauseRef: string) => void;
}

type ViewMode = "changes" | "preview";
type DiffMode = "split" | "inline";

export function MarkupComparisonPanel({
  txnId,
  contractId,
  comparison,
  markupA,
  markupB,
  isLoading,
  onRequestAIInsight,
}: MarkupComparisonPanelProps) {
  const [viewMode, setViewMode] = useState<ViewMode>("changes");
  const [diffMode, setDiffMode] = useState<DiffMode>("split");

  const downloadUrl = (markupId: string) =>
    `/api/v1/transactions/${txnId}/contracts/${contractId}/markups/${markupId}/download`;

  if (isLoading) {
    return (
      <div className="space-y-3 p-4">
        <Skeleton className="h-6 w-48" />
        <Skeleton className="h-40 w-full" />
        <Skeleton className="h-40 w-full" />
      </div>
    );
  }

  // 비교 미선택 시 최신 마크업 요약 표시
  if (!comparison) {
    const latest = markupB ?? markupA;
    return (
      <div className="flex h-full flex-col items-center justify-center p-6 text-center">
        <FileText className="mb-3 h-10 w-10 text-text-muted" />
        <p className="text-sm text-text-secondary">좌측 타임라인에서 두 버전을 선택하면 비교합니다.</p>
        {latest?.key_changes && latest.key_changes.length > 0 && (
          <div className="mt-4 w-full max-w-md rounded-lg border border-gray-border bg-white p-4 text-left">
            <p className="mb-2 text-xs font-semibold text-text-dark">
              최신 버전 (v{latest.version_number}) 변경사항
            </p>
            <ul className="space-y-1">
              {latest.key_changes.map((kc, i) => (
                <li key={i} className="flex items-start gap-2 text-xs text-text-secondary">
                  <span className="mt-0.5 inline-block h-1.5 w-1.5 shrink-0 rounded-full bg-primary-400" />
                  {kc}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      {/* 헤더 */}
      <div className="flex items-center justify-between border-b border-gray-border px-4 py-2.5">
        <h3 className="text-sm font-heading font-semibold text-text-dark">
          v{comparison.version_a} ({comparison.markup_a_party ?? "?"}) vs v{comparison.version_b} ({comparison.markup_b_party ?? "?"})
        </h3>
        <div className="flex items-center gap-2">
          {/* 탭: 변경사항 / 파일 미리보기 */}
          <div className="flex rounded-md border border-gray-border">
            <button
              onClick={() => setViewMode("changes")}
              className={`px-2.5 py-1 text-xs ${viewMode === "changes" ? "bg-primary-600 text-white" : "text-text-secondary hover:bg-gray-50"}`}
            >
              변경사항
            </button>
            <button
              onClick={() => setViewMode("preview")}
              className={`px-2.5 py-1 text-xs ${viewMode === "preview" ? "bg-primary-600 text-white" : "text-text-secondary hover:bg-gray-50"}`}
            >
              파일 미리보기
            </button>
          </div>
          {viewMode === "changes" && (
            <div className="flex rounded-md border border-gray-border">
              <button
                onClick={() => setDiffMode("split")}
                className={`p-1 ${diffMode === "split" ? "bg-gray-100" : ""}`}
                title="Split View"
              >
                <Columns className="h-3.5 w-3.5 text-text-secondary" />
              </button>
              <button
                onClick={() => setDiffMode("inline")}
                className={`p-1 ${diffMode === "inline" ? "bg-gray-100" : ""}`}
                title="Inline View"
              >
                <AlignLeft className="h-3.5 w-3.5 text-text-secondary" />
              </button>
            </div>
          )}
          <Button size="sm" variant="secondary" onClick={() => onRequestAIInsight("전체 비교")}>
            <Sparkles className="mr-1 h-3.5 w-3.5" /> AI 분석
          </Button>
        </div>
      </div>

      {/* 콘텐츠 */}
      <div className="flex-1 overflow-y-auto p-4">
        {viewMode === "changes" ? (
          <>
            {/* 요약 */}
            {(comparison.markup_a_summary || comparison.markup_b_summary) && (
              <div className="mb-4 grid grid-cols-2 gap-3">
                {comparison.markup_a_summary && (
                  <div className="rounded-lg border border-gray-border bg-gray-50 p-3">
                    <p className="mb-1 text-[10px] font-semibold text-text-muted">v{comparison.version_a} 요약</p>
                    <p className="text-xs text-text-secondary">{comparison.markup_a_summary}</p>
                  </div>
                )}
                {comparison.markup_b_summary && (
                  <div className="rounded-lg border border-gray-border bg-gray-50 p-3">
                    <p className="mb-1 text-[10px] font-semibold text-text-muted">v{comparison.version_b} 요약</p>
                    <p className="text-xs text-text-secondary">{comparison.markup_b_summary}</p>
                  </div>
                )}
              </div>
            )}

            {diffMode === "split" ? (
              <SplitView comparison={comparison} onClickChange={onRequestAIInsight} />
            ) : (
              <InlineView comparison={comparison} onClickChange={onRequestAIInsight} />
            )}
          </>
        ) : (
          <FilePreview markupA={markupA} markupB={markupB} downloadUrl={downloadUrl} />
        )}
      </div>
    </div>
  );
}

function SplitView({ comparison, onClickChange }: { comparison: MarkupComparison; onClickChange: (s: string) => void }) {
  return (
    <div className="grid grid-cols-2 gap-4">
      {/* 좌: version A */}
      <div>
        <p className="mb-2 text-[10px] font-semibold text-text-muted uppercase">
          v{comparison.version_a} — {comparison.markup_a_label}
        </p>
        <div className="space-y-1.5">
          {comparison.key_changes_a?.map((kc, i) => {
            const isDeleted = comparison.deletions.includes(kc);
            return (
              <button
                key={i}
                onClick={() => onClickChange(kc)}
                className={`w-full rounded px-2.5 py-1.5 text-left text-xs transition-colors ${
                  isDeleted
                    ? "bg-red-50 text-red-700 line-through hover:bg-red-100"
                    : "bg-white text-text-secondary hover:bg-gray-50"
                }`}
              >
                {kc}
              </button>
            );
          })}
          {(!comparison.key_changes_a || comparison.key_changes_a.length === 0) && (
            <p className="py-4 text-center text-xs text-text-muted">변경사항 없음</p>
          )}
        </div>
      </div>

      {/* 우: version B */}
      <div>
        <p className="mb-2 text-[10px] font-semibold text-text-muted uppercase">
          v{comparison.version_b} — {comparison.markup_b_label}
        </p>
        <div className="space-y-1.5">
          {comparison.key_changes_b?.map((kc, i) => {
            const isAdded = comparison.additions.includes(kc);
            return (
              <button
                key={i}
                onClick={() => onClickChange(kc)}
                className={`w-full rounded px-2.5 py-1.5 text-left text-xs transition-colors ${
                  isAdded
                    ? "bg-emerald-50 text-emerald-700 hover:bg-emerald-100"
                    : "bg-white text-text-secondary hover:bg-gray-50"
                }`}
              >
                {isAdded && <span className="mr-1 font-bold">+</span>}
                {kc}
              </button>
            );
          })}
          {(!comparison.key_changes_b || comparison.key_changes_b.length === 0) && (
            <p className="py-4 text-center text-xs text-text-muted">변경사항 없음</p>
          )}
        </div>
      </div>
    </div>
  );
}

function InlineView({ comparison, onClickChange }: { comparison: MarkupComparison; onClickChange: (s: string) => void }) {
  // 통합 리스트: 삭제 → 추가 → 공통 순
  const items = [
    ...comparison.deletions.map((s) => ({ text: s, type: "deletion" as const })),
    ...comparison.additions.map((s) => ({ text: s, type: "addition" as const })),
    ...comparison.common.map((s) => ({ text: s, type: "common" as const })),
  ];

  return (
    <div className="space-y-1">
      {items.length === 0 ? (
        <p className="py-4 text-center text-xs text-text-muted">비교할 변경사항이 없습니다.</p>
      ) : (
        items.map((item, i) => (
          <button
            key={i}
            onClick={() => onClickChange(item.text)}
            className={`flex w-full items-start gap-2 rounded px-2.5 py-1.5 text-left text-xs transition-colors ${
              item.type === "addition"
                ? "bg-emerald-50 text-emerald-700 hover:bg-emerald-100"
                : item.type === "deletion"
                  ? "bg-red-50 text-red-700 line-through hover:bg-red-100"
                  : "bg-white text-text-secondary hover:bg-gray-50"
            }`}
          >
            <span className="mt-px shrink-0 font-mono font-bold">
              {item.type === "addition" ? "+" : item.type === "deletion" ? "−" : " "}
            </span>
            {item.text}
          </button>
        ))
      )}
    </div>
  );
}

function FilePreview({
  markupA,
  markupB,
  downloadUrl,
}: {
  markupA: ContractMarkup | null;
  markupB: ContractMarkup | null;
  downloadUrl: (id: string) => string;
}) {
  return (
    <div className="grid grid-cols-2 gap-4">
      {[markupA, markupB].map((m, i) =>
        m ? (
          <div key={m.id} className="rounded-lg border border-gray-border p-3">
            <p className="mb-2 text-[10px] font-semibold text-text-muted">
              v{m.version_number} — {m.source_party ?? "Unknown"}
            </p>
            {m.file_name?.toLowerCase().endsWith(".pdf") ? (
              <iframe
                src={downloadUrl(m.id)}
                className="h-[400px] w-full rounded border"
                title={`v${m.version_number} preview`}
              />
            ) : (
              <div className="flex flex-col items-center gap-2 py-8">
                <FileText className="h-8 w-8 text-text-muted" />
                <p className="text-xs text-text-secondary">{m.file_name ?? "파일"}</p>
                {m.file_size_bytes && (
                  <p className="text-[10px] text-text-muted">
                    {(m.file_size_bytes / 1024).toFixed(0)} KB
                  </p>
                )}
                <a
                  href={downloadUrl(m.id)}
                  className="mt-1 flex items-center gap-1 text-xs text-primary-600 hover:underline"
                >
                  <Download className="h-3.5 w-3.5" /> 다운로드
                </a>
              </div>
            )}
          </div>
        ) : (
          <div key={i} className="flex items-center justify-center rounded-lg border border-dashed border-gray-300 p-8">
            <p className="text-xs text-text-muted">버전을 선택하세요</p>
          </div>
        ),
      )}
    </div>
  );
}

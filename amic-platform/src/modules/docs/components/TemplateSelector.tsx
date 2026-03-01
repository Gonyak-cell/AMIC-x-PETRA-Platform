/** Step 0: 계약서 유형 선택 카드 */

import { FileText, RefreshCw } from "lucide-react";
import type { ContractTemplate } from "@/modules/docs/types/contract_generation";
import { CONTRACT_TYPE_META } from "@/modules/docs/types/contract_generation";

interface TemplateSelectorProps {
  templates: ContractTemplate[] | undefined;
  isLoading: boolean;
  onSelect: (template: ContractTemplate) => void;
}

export default function TemplateSelector({
  templates,
  isLoading,
  onSelect,
}: TemplateSelectorProps) {
  if (isLoading) {
    return (
      <div
        className="flex h-40 items-center justify-center"
        role="status"
        aria-busy="true"
      >
        <RefreshCw
          className="h-5 w-5 animate-spin text-text-tertiary"
          aria-hidden="true"
        />
        <span className="sr-only">템플릿 목록을 불러오는 중입니다</span>
      </div>
    );
  }

  if (!templates || templates.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center gap-3 rounded-xl border border-dashed border-border py-12 text-center">
        <FileText className="h-8 w-8 text-text-tertiary" aria-hidden="true" />
        <p className="text-sm text-text-secondary">
          사용 가능한 템플릿이 없습니다
        </p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {templates.map((tmpl) => {
        const meta = CONTRACT_TYPE_META[tmpl.doc_type];
        return (
          <button
            key={tmpl.id}
            type="button"
            onClick={() => onSelect(tmpl)}
            aria-label={`${tmpl.doc_type} — ${meta?.labelKo ?? tmpl.name} 선택`}
            className="group flex flex-col gap-3 rounded-xl border border-border bg-white p-5 text-left transition-all hover:border-accent-primary hover:shadow-md"
          >
            <div className="flex items-center gap-2">
              <span
                className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${meta?.color ?? "bg-gray-100 text-gray-600"}`}
              >
                {tmpl.doc_type}
              </span>
              <span className="text-xs text-text-tertiary">
                v{tmpl.version}
              </span>
            </div>
            <div>
              <h4 className="text-sm font-semibold text-text-primary group-hover:text-accent-primary">
                {meta?.labelKo ?? tmpl.name}
              </h4>
              <p className="mt-1 text-xs text-text-secondary line-clamp-2">
                {tmpl.description ?? meta?.description ?? ""}
              </p>
            </div>
          </button>
        );
      })}
    </div>
  );
}

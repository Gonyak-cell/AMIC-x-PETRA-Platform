import { AlertTriangle, Files, Filter, Tags } from "lucide-react";
import { Card } from "@/components/ui";
import type {
  FinancialModel,
  FinancialModelSourceRouting,
  FinancialModelSourceRoutingDocument,
} from "@/modules/ma/types/financial_model";

interface Props {
  model: FinancialModel | null;
}

function formatWorkstreamName(value: string): string {
  switch (value) {
    case "FDD":
      return "FDD";
    case "VALUATION":
      return "Valuation";
    case "LDD":
      return "LDD";
    case "COMMON":
      return "Common";
    default:
      return value;
  }
}

function getSourceRouting(model: FinancialModel | null): FinancialModelSourceRouting | null {
  const routing = model?.parameters?.source_routing;
  if (!routing || typeof routing !== "object") {
    return null;
  }
  return routing;
}

function renderDocumentRow(document: FinancialModelSourceRoutingDocument) {
  return (
    <li
      key={document.document_id}
      className="rounded-md border border-gray-200 bg-white px-3 py-2"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="truncate text-sm font-medium text-text-dark">
            {document.original_name}
          </p>
          <p className="text-[11px] text-text-secondary">
            {formatWorkstreamName(document.primary_workstream)} · {Math.round(document.confidence * 100)}%
          </p>
        </div>
        <div className="flex flex-wrap justify-end gap-1">
          {document.requires_manual_review && (
            <span className="rounded bg-amber-50 px-2 py-0.5 text-[10px] text-amber-700">
              Manual review
            </span>
          )}
          {document.include_for_financial_model === false && (
            <span className="rounded bg-slate-100 px-2 py-0.5 text-[10px] text-slate-600">
              Excluded
            </span>
          )}
        </div>
      </div>
    </li>
  );
}

export default function FMSourceRoutingCard({ model }: Props) {
  const sourceRouting = getSourceRouting(model);
  if (!sourceRouting) {
    return null;
  }

  const summary = sourceRouting.summary;
  const targetWorkstreams = Array.isArray(summary.target_workstreams)
    ? summary.target_workstreams
    : [];
  const manualReviewDocs = sourceRouting.documents.filter(
    (document) => document.requires_manual_review,
  );
  const excludedDocs = sourceRouting.documents.filter(
    (document) => document.include_for_financial_model === false,
  );
  const seededItems =
    typeof model?.parameters?.seeded_checklist_items === "number"
      ? model.parameters.seeded_checklist_items
      : null;

  return (
    <Card className="p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold text-text-dark">Source Routing</h3>
          <p className="text-xs text-text-secondary">
            Financial model inputs filtered through shared FDD and valuation routing.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {targetWorkstreams.map((workstream) => (
            <span
              key={workstream}
              className="rounded-full bg-blue-50 px-2.5 py-1 text-[11px] font-medium text-blue-700"
            >
              {formatWorkstreamName(workstream)}
            </span>
          ))}
        </div>
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-4">
        <div className="rounded-lg bg-slate-50 p-3">
          <div className="flex items-center gap-2 text-[11px] uppercase tracking-wide text-text-secondary">
            <Files className="h-3.5 w-3.5" />
            Documents
          </div>
          <p className="mt-1 text-lg font-semibold text-text-dark">
            {summary.included_for_financial_model ?? 0}
            <span className="ml-1 text-sm font-normal text-text-secondary">
              / {summary.total_documents}
            </span>
          </p>
        </div>
        <div className="rounded-lg bg-slate-50 p-3">
          <div className="flex items-center gap-2 text-[11px] uppercase tracking-wide text-text-secondary">
            <Filter className="h-3.5 w-3.5" />
            Excluded
          </div>
          <p className="mt-1 text-lg font-semibold text-text-dark">
            {summary.excluded_from_financial_model ?? excludedDocs.length}
          </p>
        </div>
        <div className="rounded-lg bg-slate-50 p-3">
          <div className="flex items-center gap-2 text-[11px] uppercase tracking-wide text-text-secondary">
            <AlertTriangle className="h-3.5 w-3.5" />
            Manual Review
          </div>
          <p className="mt-1 text-lg font-semibold text-text-dark">
            {summary.manual_review_documents}
          </p>
        </div>
        <div className="rounded-lg bg-slate-50 p-3">
          <div className="flex items-center gap-2 text-[11px] uppercase tracking-wide text-text-secondary">
            <Tags className="h-3.5 w-3.5" />
            Seeded Items
          </div>
          <p className="mt-1 text-lg font-semibold text-text-dark">
            {seededItems ?? 0}
          </p>
        </div>
      </div>

      <div className="mt-4 flex flex-wrap gap-2 text-xs text-text-secondary">
        {Object.entries(summary.by_primary_workstream).map(([workstream, count]) => (
          <span
            key={workstream}
            className="rounded bg-white px-2 py-1 ring-1 ring-gray-200"
          >
            {formatWorkstreamName(workstream)} {count}
          </span>
        ))}
      </div>

      {(manualReviewDocs.length > 0 || excludedDocs.length > 0) && (
        <div className="mt-4 grid gap-4 lg:grid-cols-2">
          {manualReviewDocs.length > 0 && (
            <div>
              <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-text-secondary">
                Manual Review Documents
              </h4>
              <ul className="space-y-2">
                {manualReviewDocs.slice(0, 4).map(renderDocumentRow)}
              </ul>
            </div>
          )}
          {excludedDocs.length > 0 && (
            <div>
              <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-text-secondary">
                Excluded Documents
              </h4>
              <ul className="space-y-2">
                {excludedDocs.slice(0, 4).map(renderDocumentRow)}
              </ul>
            </div>
          )}
        </div>
      )}
    </Card>
  );
}

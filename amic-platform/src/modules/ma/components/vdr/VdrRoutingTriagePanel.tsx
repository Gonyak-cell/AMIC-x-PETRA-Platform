import {
  AlertTriangle,
  CheckCircle2,
  FolderKanban,
  ShieldCheck,
} from "lucide-react";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import {
  useDeleteVdrRoutingOverride,
  useUpsertVdrRoutingOverride,
  useVdrRoutingQueue,
} from "@/modules/ma/hooks/useVdr";
import type {
  VdrRoutingDecision,
  VdrRoutingQueueItem,
  VdrRoutingQueueStatus,
  VdrWorkstream,
} from "@/modules/ma/types/vdr";
import {
  VDR_CATEGORY_LABELS,
  VDR_WORKSTREAM_LABELS,
} from "@/modules/ma/types/vdr";

interface Props {
  txnId: string;
}

const WORKSTREAMS: VdrWorkstream[] = ["LDD", "FDD", "VALUATION", "COMMON"];

function formatConfidence(value: number): string {
  return `${Math.round(value * 100)}%`;
}

function formatDate(value: string | null): string | null {
  if (!value) {
    return null;
  }
  return new Intl.DateTimeFormat("ko-KR", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function getStatusTone(status: VdrRoutingQueueItem["routing_status"]): string {
  if (status === "OPEN_REVIEW") {
    return "bg-amber-50 text-amber-700 border-amber-200";
  }
  if (status === "OVERRIDDEN") {
    return "bg-emerald-50 text-emerald-700 border-emerald-200";
  }
  return "bg-slate-100 text-slate-600 border-slate-200";
}

function RouteBadge({
  title,
  route,
}: {
  title: string;
  route: VdrRoutingDecision;
}) {
  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
      <div className="mb-1 flex items-center justify-between gap-2">
        <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          {title}
        </span>
        <span className="text-xs font-medium text-slate-500">
          {formatConfidence(route.confidence)}
        </span>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <span className="rounded-full bg-white px-2 py-1 text-xs font-semibold text-slate-700">
          {VDR_WORKSTREAM_LABELS[route.primary_workstream]}
        </span>
        {route.workstream_tags.map((tag) => (
          <span
            key={`${title}-${tag}`}
            className="rounded-full border border-slate-200 bg-white px-2 py-1 text-[11px] text-slate-500"
          >
            {VDR_WORKSTREAM_LABELS[tag]}
          </span>
        ))}
        {route.requires_manual_review && (
          <span className="rounded-full bg-amber-100 px-2 py-1 text-[11px] font-medium text-amber-700">
            Manual review
          </span>
        )}
        {route.is_override && (
          <span className="rounded-full bg-emerald-100 px-2 py-1 text-[11px] font-medium text-emerald-700">
            Override
          </span>
        )}
      </div>
      {route.reasons.length > 0 && (
        <p className="mt-2 text-xs leading-5 text-slate-500">
          {route.reasons.slice(0, 3).join(" · ")}
        </p>
      )}
      {route.is_override && route.override_note && (
        <p className="mt-2 text-xs leading-5 text-slate-600">
          {route.override_note}
        </p>
      )}
    </div>
  );
}

function RoutingQueueRow({
  item,
  saving,
  clearing,
  onSave,
  onClear,
}: {
  item: VdrRoutingQueueItem;
  saving: boolean;
  clearing: boolean;
  onSave: (docId: string, body: {
    primary_workstream: VdrWorkstream;
    workstream_tags: VdrWorkstream[];
    override_note: string | null;
  }) => void;
  onClear: (docId: string) => void;
}) {
  const [primaryWorkstream, setPrimaryWorkstream] = useState<VdrWorkstream>(
    item.effective_route.primary_workstream,
  );
  const [workstreamTags, setWorkstreamTags] = useState<VdrWorkstream[]>(
    item.effective_route.workstream_tags,
  );
  const [overrideNote, setOverrideNote] = useState(
    item.effective_route.override_note ?? "",
  );

  useEffect(() => {
    setPrimaryWorkstream(item.effective_route.primary_workstream);
    setWorkstreamTags(item.effective_route.workstream_tags);
    setOverrideNote(item.effective_route.override_note ?? "");
  }, [item.effective_route]);

  const toggleTag = (tag: VdrWorkstream) => {
    setWorkstreamTags((current) =>
      current.includes(tag)
        ? current.filter((value) => value !== tag)
        : [...current, tag],
    );
  };

  const reviewedAt = formatDate(item.effective_route.reviewed_at);

  return (
    <Card padding="lg" className="space-y-4">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div className="space-y-2">
          <div className="flex flex-wrap items-center gap-2">
            <span
              className={`rounded-full border px-2.5 py-1 text-xs font-semibold ${getStatusTone(item.routing_status)}`}
            >
              {item.routing_status === "OPEN_REVIEW"
                ? "Open review"
                : item.routing_status === "OVERRIDDEN"
                  ? "Reviewed"
                  : "Auto routed"}
            </span>
            <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs text-slate-600">
              {VDR_CATEGORY_LABELS[item.folder_category]}
            </span>
            <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs text-slate-600">
              {item.folder_name}
            </span>
          </div>
          <div>
            <h3 className="text-sm font-semibold text-slate-900">
              {item.document.original_name}
            </h3>
            <p className="text-xs text-slate-500">
              Updated {new Date(item.document.updated_at).toLocaleString("ko-KR")}
            </p>
          </div>
          {item.effective_route.reviewed_by_email && (
            <p className="text-xs text-slate-500">
              Reviewed by {item.effective_route.reviewed_by_email}
              {reviewedAt ? ` · ${reviewedAt}` : ""}
            </p>
          )}
        </div>
        <div className="grid gap-3 lg:w-[28rem] lg:grid-cols-2">
          <RouteBadge title="Auto Route" route={item.auto_route} />
          <RouteBadge title="Current Route" route={item.effective_route} />
        </div>
      </div>

      <div className="grid gap-4 rounded-xl border border-slate-200 bg-white p-4 lg:grid-cols-[180px,1fr]">
        <div className="space-y-2">
          <label className="block text-xs font-semibold uppercase tracking-wide text-slate-500">
            Primary Workstream
          </label>
          <select
            className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700"
            value={primaryWorkstream}
            onChange={(event) =>
              setPrimaryWorkstream(event.target.value as VdrWorkstream)
            }
          >
            {WORKSTREAMS.map((workstream) => (
              <option key={workstream} value={workstream}>
                {VDR_WORKSTREAM_LABELS[workstream]}
              </option>
            ))}
          </select>
        </div>
        <div className="space-y-2">
          <label className="block text-xs font-semibold uppercase tracking-wide text-slate-500">
            Workstream Tags
          </label>
          <div className="flex flex-wrap gap-2">
            {WORKSTREAMS.map((workstream) => {
              const checked = workstreamTags.includes(workstream);
              return (
                <label
                  key={workstream}
                  className={`inline-flex cursor-pointer items-center gap-2 rounded-full border px-3 py-1.5 text-xs ${
                    checked
                      ? "border-emerald-300 bg-emerald-50 text-emerald-700"
                      : "border-slate-200 bg-white text-slate-600"
                  }`}
                >
                  <input
                    type="checkbox"
                    className="h-3.5 w-3.5"
                    checked={checked}
                    onChange={() => toggleTag(workstream)}
                  />
                  {VDR_WORKSTREAM_LABELS[workstream]}
                </label>
              );
            })}
          </div>
        </div>
        <div className="space-y-2 lg:col-span-2">
          <label className="block text-xs font-semibold uppercase tracking-wide text-slate-500">
            Review Note
          </label>
          <textarea
            className="min-h-24 w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700"
            placeholder="Why should this document be routed this way?"
            value={overrideNote}
            onChange={(event) => setOverrideNote(event.target.value)}
          />
        </div>
        <div className="flex flex-wrap items-center gap-2 lg:col-span-2">
          <Button
            variant="brand"
            size="sm"
            loading={saving}
            onClick={() =>
              onSave(item.document.id, {
                primary_workstream: primaryWorkstream,
                workstream_tags: workstreamTags,
                override_note: overrideNote.trim() || null,
              })
            }
          >
            Save Override
          </Button>
          {item.effective_route.is_override && (
            <Button
              variant="secondary"
              size="sm"
              loading={clearing}
              onClick={() => onClear(item.document.id)}
            >
              Remove Override
            </Button>
          )}
        </div>
      </div>
    </Card>
  );
}

export default function VdrRoutingTriagePanel({ txnId }: Props) {
  const [status, setStatus] = useState<VdrRoutingQueueStatus>("open");
  const { data, isLoading } = useVdrRoutingQueue(txnId, status);
  const saveOverride = useUpsertVdrRoutingOverride(txnId);
  const deleteOverride = useDeleteVdrRoutingOverride(txnId);

  const summary = data?.summary;
  const items = data?.items ?? [];

  return (
    <div className="space-y-4">
      <div className="grid gap-4 md:grid-cols-4">
        <Card padding="md">
          <div className="flex items-center gap-3">
            <AlertTriangle className="h-5 w-5 text-amber-500" />
            <div>
              <p className="text-xs uppercase tracking-wide text-slate-500">
                Open Review
              </p>
              <p className="text-2xl font-semibold text-slate-900">
                {summary?.open_documents ?? 0}
              </p>
            </div>
          </div>
        </Card>
        <Card padding="md">
          <div className="flex items-center gap-3">
            <ShieldCheck className="h-5 w-5 text-emerald-500" />
            <div>
              <p className="text-xs uppercase tracking-wide text-slate-500">
                Reviewed
              </p>
              <p className="text-2xl font-semibold text-slate-900">
                {summary?.reviewed_documents ?? 0}
              </p>
            </div>
          </div>
        </Card>
        <Card padding="md">
          <div className="flex items-center gap-3">
            <CheckCircle2 className="h-5 w-5 text-sky-500" />
            <div>
              <p className="text-xs uppercase tracking-wide text-slate-500">
                Auto Routed
              </p>
              <p className="text-2xl font-semibold text-slate-900">
                {summary?.auto_routed_documents ?? 0}
              </p>
            </div>
          </div>
        </Card>
        <Card padding="md">
          <div className="flex items-center gap-3">
            <FolderKanban className="h-5 w-5 text-slate-500" />
            <div>
              <p className="text-xs uppercase tracking-wide text-slate-500">
                Total Documents
              </p>
              <p className="text-2xl font-semibold text-slate-900">
                {summary?.total_documents ?? 0}
              </p>
            </div>
          </div>
        </Card>
      </div>

      <Card padding="lg">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h2 className="text-sm font-semibold text-slate-900">
              Routing Triage Queue
            </h2>
            <p className="text-sm text-slate-500">
              Review low-confidence routing results and persist manual
              workstream decisions.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            {(["open", "reviewed", "all"] as VdrRoutingQueueStatus[]).map(
              (value) => (
                <Button
                  key={value}
                  variant={status === value ? "brand" : "secondary"}
                  size="sm"
                  onClick={() => setStatus(value)}
                >
                  {value === "open"
                    ? "Open"
                    : value === "reviewed"
                      ? "Reviewed"
                      : "All"}
                </Button>
              ),
            )}
          </div>
        </div>
        {summary && Object.keys(summary.by_effective_workstream).length > 0 && (
          <div className="mt-4 flex flex-wrap gap-2">
            {WORKSTREAMS.map((workstream) => {
              const count = summary.by_effective_workstream[workstream] ?? 0;
              return (
                <span
                  key={workstream}
                  className="rounded-full bg-slate-100 px-3 py-1 text-xs text-slate-600"
                >
                  {VDR_WORKSTREAM_LABELS[workstream]} {count}
                </span>
              );
            })}
          </div>
        )}
      </Card>

      {isLoading ? (
        <Card padding="lg">
          <div className="py-16 text-center text-sm text-slate-500">
            Loading routing queue...
          </div>
        </Card>
      ) : items.length === 0 ? (
        <Card padding="lg">
          <div className="py-16 text-center text-sm text-slate-500">
            No documents match the current filter.
          </div>
        </Card>
      ) : (
        <div className="space-y-4">
          {items.map((item) => (
            <RoutingQueueRow
              key={item.document.id}
              item={item}
              saving={saveOverride.isPending}
              clearing={deleteOverride.isPending}
              onSave={(docId, body) =>
                saveOverride.mutate({
                  docId,
                  body,
                })
              }
              onClear={(docId) => deleteOverride.mutate(docId)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

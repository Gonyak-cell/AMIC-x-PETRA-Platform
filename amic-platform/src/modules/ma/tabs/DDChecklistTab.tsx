import { useState, useMemo } from "react";
import { BarChart2, Plus, Trash2, ClipboardCheck } from "lucide-react";
import {
  useDDChecklist,
  useDDChecklistSummary,
  useCreateDDChecklistItem,
  useUpdateDDChecklistItem,
  useDeleteDDChecklistItem,
} from "@/modules/ma/hooks/useDDChecklist";
import type {
  DDChecklistCreate,
  DDWorkstream,
  DDChecklistStatus as DDStatusType,
} from "@/modules/ma/types/dd_checklist";
import {
  DD_WORKSTREAM_OPTIONS,
  DD_WORKSTREAM_HIERARCHY,
  DD_SUB_LABELS,
  DD_STATUS_OPTIONS,
} from "@/modules/ma/constants";
import FileUploadZone from "@/modules/ma/components/FileUploadZone";
import DDReportSection from "@/modules/ma/components/DDReportSection";

import {
  Badge,
  Button,
  Card,
  DataTable,
  EmptyState,
  InlineSelect,
  INLINE_INPUT_CLS,
  Input,
  KpiCard,
  Modal,
  SlidePanel,
} from "@/components/ui";

interface DDChecklistTabProps {
  txnId: string;
  canWrite: boolean;
}

export default function DDChecklistTab({
  txnId,
  canWrite,
}: DDChecklistTabProps) {
  const { data: ddItems } = useDDChecklist(txnId);
  const { data: ddSummary } = useDDChecklistSummary(txnId);
  const createDDItem = useCreateDDChecklistItem(txnId);
  const updateDDItem = useUpdateDDChecklistItem(txnId);
  const deleteDDItem = useDeleteDDChecklistItem(txnId);

  const [showDDReport, setShowDDReport] = useState(false);
  const [showDDModal, setShowDDModal] = useState(false);
  const [ddGroupFilter, setDdGroupFilter] = useState<string>("ALL");
  const [ddSubFilter, setDdSubFilter] = useState<string | null>(null);
  const [ddForm, setDDForm] = useState<DDChecklistCreate>({
    workstream: "FDD_FINANCIAL_STATEMENTS" as DDWorkstream,
    title: "",
  });

  const activeGroup = DD_WORKSTREAM_HIERARCHY.find(
    (g) => g.key === ddGroupFilter,
  );
  const filteredDDItems = useMemo(() => {
    if (!ddItems) return [];
    if (ddGroupFilter === "ALL") return ddItems;
    if (!activeGroup) return ddItems;
    if (ddSubFilter)
      return ddItems.filter((item) => item.workstream === ddSubFilter);
    return ddItems.filter((item) =>
      activeGroup.children.includes(item.workstream),
    );
  }, [ddItems, ddGroupFilter, ddSubFilter, activeGroup]);

  return (
    <div className="space-y-4">
      {/* DD 진행 요약 */}
      {ddSummary && ddSummary.total > 0 && (
        <div className="space-y-3">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <KpiCard label="전체 항목" value={String(ddSummary.total)} />
            <KpiCard
              label="완료율"
              value={`${Math.round(ddSummary.overall_completion_pct)}%`}
              variant={
                ddSummary.overall_completion_pct >= 80 ? "positive" : "default"
              }
            />
            <KpiCard
              label="진행 중"
              value={String(
                ddSummary.by_workstream.reduce((s, w) => s + w.in_progress, 0),
              )}
            />
            <KpiCard
              label="미시작"
              value={String(
                ddSummary.by_workstream.reduce((s, w) => s + w.not_started, 0),
              )}
              variant={
                ddSummary.by_workstream.reduce((s, w) => s + w.not_started, 0) >
                0
                  ? "negative"
                  : "default"
              }
            />
          </div>
          {/* 워크스트림별 진행률 바 (그룹화) */}
          <Card padding="md">
            <div className="space-y-2">
              {DD_WORKSTREAM_HIERARCHY.map((group) => {
                const childStats = ddSummary.by_workstream.filter((ws) =>
                  group.children.includes(ws.workstream),
                );
                const total = childStats.reduce((s, w) => s + w.total, 0);
                const completed = childStats.reduce(
                  (s, w) => s + w.completed,
                  0,
                );
                const pct =
                  total > 0 ? Math.round((completed / total) * 100) : 0;
                return (
                  <div key={group.key}>
                    <div className="flex items-center gap-3">
                      <span className="text-xs font-medium w-24 truncate">
                        {group.label}
                      </span>
                      <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-accent rounded-full transition-all"
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                      <span className="text-xs text-text-muted w-16 text-right">
                        {completed}/{total}
                      </span>
                    </div>
                    {group.children.length > 1 &&
                      childStats.map((ws) => {
                        const subPct =
                          ws.total > 0
                            ? Math.round((ws.completed / ws.total) * 100)
                            : 0;
                        return (
                          <div
                            key={ws.workstream}
                            className="flex items-center gap-3 ml-6 mt-1"
                          >
                            <span className="text-[10px] text-text-muted w-18 truncate">
                              {DD_SUB_LABELS[ws.workstream] ?? ws.workstream}
                            </span>
                            <div className="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                              <div
                                className="h-full bg-accent/60 rounded-full transition-all"
                                style={{ width: `${subPct}%` }}
                              />
                            </div>
                            <span className="text-[10px] text-text-muted w-12 text-right">
                              {ws.completed}/{ws.total}
                            </span>
                          </div>
                        );
                      })}
                  </div>
                );
              })}
            </div>
          </Card>
        </div>
      )}

      {/* 워크스트림 필터 -- 1단: 메인 그룹 */}
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs font-medium text-text-muted">워크스트림:</span>
        <button
          type="button"
          className={`px-3 py-1 text-xs font-medium rounded-dr-sm transition-colors ${
            ddGroupFilter === "ALL"
              ? "bg-accent text-white"
              : "bg-bg-cool text-text-muted hover:bg-gray-border"
          }`}
          onClick={() => {
            setDdGroupFilter("ALL");
            setDdSubFilter(null);
          }}
        >
          전체
        </button>
        {DD_WORKSTREAM_HIERARCHY.map((g) => (
          <button
            key={g.key}
            type="button"
            className={`px-3 py-1 text-xs font-medium rounded-dr-sm transition-colors ${
              ddGroupFilter === g.key
                ? "bg-accent text-white"
                : "bg-bg-cool text-text-muted hover:bg-gray-border"
            }`}
            onClick={() => {
              setDdGroupFilter(g.key);
              setDdSubFilter(null);
            }}
          >
            {g.label}
            {g.children.length > 1 ? " \u25BE" : ""}
          </button>
        ))}
      </div>
      {/* 워크스트림 필터 -- 2단: 서브 필터 */}
      {activeGroup && activeGroup.children.length > 1 && (
        <div className="flex flex-wrap items-center gap-2 ml-4">
          <span className="text-xs text-text-muted">하위:</span>
          <button
            type="button"
            className={`px-2.5 py-0.5 text-[11px] font-medium rounded-dr-sm transition-colors ${
              !ddSubFilter
                ? "bg-accent/80 text-white"
                : "bg-bg-cool text-text-muted hover:bg-gray-border"
            }`}
            onClick={() => setDdSubFilter(null)}
          >
            전체
          </button>
          {activeGroup.children.map((ws) => (
            <button
              key={ws}
              type="button"
              className={`px-2.5 py-0.5 text-[11px] font-medium rounded-dr-sm transition-colors ${
                ddSubFilter === ws
                  ? "bg-accent/80 text-white"
                  : "bg-bg-cool text-text-muted hover:bg-gray-border"
              }`}
              onClick={() => setDdSubFilter(ws)}
            >
              {DD_SUB_LABELS[ws] ?? ws}
            </button>
          ))}
        </div>
      )}

      {/* 체크리스트 목록 */}
      <Card
        title="DD 체크리스트"
        headerBar
        padding="none"
        actions={
          <div className="flex gap-2">
            <Button
              icon={BarChart2}
              variant="ghost"
              size="sm"
              onClick={() => setShowDDReport(true)}
            >
              리포트 생성
            </Button>
            {canWrite && (
              <Button
                icon={Plus}
                onClick={() => setShowDDModal(true)}
                variant="ghost"
                size="sm"
              >
                항목 추가
              </Button>
            )}
          </div>
        }
      >
        {!ddItems?.length ? (
          <EmptyState
            icon={ClipboardCheck}
            title="체크리스트 없음"
            description="실사 체크리스트 항목을 추가하세요."
            actionLabel={canWrite ? "항목 추가" : undefined}
            onAction={canWrite ? () => setShowDDModal(true) : undefined}
          />
        ) : !filteredDDItems?.length ? (
          <div className="p-8 text-center text-text-muted text-sm">
            선택한 워크스트림에 해당하는 항목이 없습니다.
          </div>
        ) : (
          <DataTable
            columns={[
              {
                key: "workstream",
                header: "워크스트림",
                render: (r) => {
                  const group = DD_WORKSTREAM_HIERARCHY.find((g) =>
                    g.children.includes(r.workstream),
                  );
                  const groupLabel = group?.label.split(" ")[0] ?? "";
                  return (
                    <div className="flex items-center gap-1">
                      {group && group.children.length > 1 && (
                        <Badge
                          variant="neutral"
                          className="text-[10px] opacity-60"
                        >
                          {groupLabel}
                        </Badge>
                      )}
                      <Badge variant="neutral">
                        {DD_SUB_LABELS[r.workstream] ??
                          DD_WORKSTREAM_OPTIONS.find(
                            (o) => o.value === r.workstream,
                          )?.label ??
                          r.workstream}
                      </Badge>
                    </div>
                  );
                },
              },
              { key: "title", header: "항목" },
              {
                key: "status",
                header: "상태",
                render: (r) => (
                  <InlineSelect
                    options={DD_STATUS_OPTIONS}
                    value={r.status}
                    onChange={(v) =>
                      updateDDItem.mutate({
                        itemId: r.id,
                        body: { status: v as DDStatusType },
                      })
                    }
                    disabled={!canWrite}
                  />
                ),
              },
              {
                key: "assignee_email",
                header: "담당자",
                render: (r) => (
                  <input
                    key={`${r.id}-assignee-${r.assignee_email}`}
                    type="email"
                    className={`${INLINE_INPUT_CLS} w-36`}
                    defaultValue={r.assignee_email ?? ""}
                    placeholder="이메일"
                    onBlur={(e) => {
                      const v = e.target.value || undefined;
                      if (v !== (r.assignee_email ?? undefined)) {
                        updateDDItem.mutate({
                          itemId: r.id,
                          body: { assignee_email: v },
                        });
                      }
                    }}
                    disabled={!canWrite}
                  />
                ),
              },
              {
                key: "due_date",
                header: "기한",
                render: (r) => (
                  <input
                    key={`${r.id}-due-${r.due_date}`}
                    type="date"
                    className={`${INLINE_INPUT_CLS} w-32`}
                    defaultValue={r.due_date ?? ""}
                    onChange={(e) =>
                      updateDDItem.mutate({
                        itemId: r.id,
                        body: { due_date: e.target.value || undefined },
                      })
                    }
                    disabled={!canWrite}
                  />
                ),
              },
              {
                key: "actions",
                header: "",
                width: "40px",
                render: (r) =>
                  canWrite ? (
                    <button
                      className="text-text-muted hover:text-negative p-1 rounded transition-colors"
                      title="삭제"
                      onClick={() => {
                        if (confirm("이 체크리스트 항목을 삭제하시겠습니까?")) {
                          deleteDDItem.mutate(r.id);
                        }
                      }}
                    >
                      <Trash2 size={14} />
                    </button>
                  ) : null,
              },
            ]}
            data={filteredDDItems ?? []}
            keyField="id"
          />
        )}
        <FileUploadZone txnId={txnId} entityType="DD_CHECKLIST" embedded />
      </Card>

      {/* DD 리포트 SlidePanel */}
      <SlidePanel
        open={showDDReport}
        onClose={() => setShowDDReport(false)}
        title="DD 리포트"
        width="lg"
      >
        <DDReportSection txnId={txnId} />
      </SlidePanel>

      {/* DD 체크리스트 추가 모달 */}
      <Modal
        open={showDDModal}
        onClose={() => setShowDDModal(false)}
        title="DD 체크리스트 항목 추가"
      >
        <form
          onSubmit={(e) => {
            e.preventDefault();
            createDDItem.mutate(ddForm, {
              onSuccess: () => {
                setShowDDModal(false);
                setDDForm({
                  workstream: "FDD_FINANCIAL_STATEMENTS",
                  title: "",
                });
              },
            });
          }}
          className="space-y-4"
        >
          <div className="w-full">
            <label className="block text-sm font-medium text-text-body mb-1.5">
              워크스트림
            </label>
            <div className="relative">
              <select
                className="w-full px-3 py-2 text-sm rounded-dr-sm border transition-colors appearance-none shadow-sm bg-white text-text-body pr-10 focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-amic border-gray-border hover:border-amic-400"
                value={ddForm.workstream}
                onChange={(e) =>
                  setDDForm({
                    ...ddForm,
                    workstream: e.target.value as DDWorkstream,
                  })
                }
              >
                {DD_WORKSTREAM_HIERARCHY.map((g) =>
                  g.children.length === 1 ? (
                    <option key={g.key} value={g.children[0]}>
                      {g.label}
                    </option>
                  ) : (
                    <optgroup key={g.key} label={g.label}>
                      {g.children.map((ws) => (
                        <option key={ws} value={ws}>
                          {DD_SUB_LABELS[ws] ?? ws}
                        </option>
                      ))}
                    </optgroup>
                  ),
                )}
              </select>
            </div>
          </div>
          <Input
            label="항목명"
            required
            value={ddForm.title}
            onChange={(e) => setDDForm({ ...ddForm, title: e.target.value })}
            placeholder="예: 최근 3개년 재무제표 수집"
          />
          <Input
            label="설명"
            value={ddForm.description ?? ""}
            onChange={(e) =>
              setDDForm({ ...ddForm, description: e.target.value || undefined })
            }
          />
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="담당자 이메일"
              type="email"
              value={ddForm.assignee_email ?? ""}
              onChange={(e) =>
                setDDForm({
                  ...ddForm,
                  assignee_email: e.target.value || undefined,
                })
              }
            />
            <Input
              label="기한"
              type="date"
              value={ddForm.due_date ?? ""}
              onChange={(e) =>
                setDDForm({ ...ddForm, due_date: e.target.value || undefined })
              }
            />
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <Button
              variant="ghost"
              type="button"
              onClick={() => setShowDDModal(false)}
            >
              취소
            </Button>
            <Button type="submit" loading={createDDItem.isPending}>
              추가
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}

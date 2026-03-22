import { useState } from "react";
import { Plus, Trash2, Flag } from "lucide-react";
import {
  usePMITasks,
  usePMISummary,
  useCreatePMITask,
  useUpdatePMITask,
  useDeletePMITask,
} from "@/modules/ma/hooks/usePMI";
import type {
  PMITask,
  PMITaskCreate,
  PMICategory,
  PMITaskStatus,
  PMIPriority,
} from "@/modules/ma/types/pmi";
import {
  PMI_CATEGORY_OPTIONS,
  PMI_STATUS_OPTIONS,
  PMI_PRIORITY_OPTIONS,
} from "@/modules/ma/constants";
import FileUploadZone from "@/modules/ma/components/FileUploadZone";

import {
  Button,
  Card,
  DataTable,
  EmptyState,
  InlineSelect,
  INLINE_INPUT_CLS,
  Input,
  KpiCard,
  Modal,
  Select,
  Badge,
} from "@/components/ui";
import type { Column } from "@/components/ui";

interface PMITabProps {
  txnId: string;
  canWrite: boolean;
}

export default function PMITab({ txnId, canWrite }: PMITabProps) {
  const { data: pmiTasks } = usePMITasks(txnId);
  const { data: pmiSummary } = usePMISummary(txnId);
  const createPMITask = useCreatePMITask(txnId);
  const updatePMITask = useUpdatePMITask(txnId);
  const deletePMITask = useDeletePMITask(txnId);

  const [showPMIModal, setShowPMIModal] = useState(false);
  const [pmiCategoryFilter, setPmiCategoryFilter] = useState<string>("ALL");
  const [pmiForm, setPmiForm] = useState<PMITaskCreate>({
    category: "INTEGRATION_PLAN" as PMICategory,
    title: "",
  });

  const filteredPmiTasks =
    pmiCategoryFilter === "ALL"
      ? pmiTasks
      : pmiTasks?.filter((t) => t.category === pmiCategoryFilter);

  return (
    <div className="space-y-4">
      {/* KPI 요약 */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <KpiCard label="총 태스크" value={String(pmiSummary?.total ?? 0)} />
        <KpiCard
          label="완료율"
          value={`${Math.round((pmiSummary?.completion_rate ?? 0) * 100)}%`}
          variant={
            (pmiSummary?.completion_rate ?? 0) >= 0.8
              ? "positive"
              : (pmiSummary?.completion_rate ?? 0) >= 0.5
                ? "caution"
                : "default"
          }
        />
        <KpiCard
          label="진행 중"
          value={String(pmiSummary?.by_status?.IN_PROGRESS ?? 0)}
          variant="caution"
        />
        <KpiCard
          label="차단됨"
          value={String(pmiSummary?.by_status?.BLOCKED ?? 0)}
          variant={
            (pmiSummary?.by_status?.BLOCKED ?? 0) > 0 ? "negative" : "default"
          }
        />
      </div>

      {/* 카테고리 필터 칩 */}
      <div className="flex flex-wrap gap-2">
        <button
          className={`px-3 py-1 rounded-dr-sm text-xs font-medium transition-colors ${pmiCategoryFilter === "ALL" ? "bg-accent text-white" : "bg-bg-cool text-text-muted hover:bg-gray-border"}`}
          onClick={() => setPmiCategoryFilter("ALL")}
        >
          전체
        </button>
        {PMI_CATEGORY_OPTIONS.map((opt) => (
          <button
            key={opt.value}
            className={`px-3 py-1 rounded-dr-sm text-xs font-medium transition-colors ${pmiCategoryFilter === opt.value ? "bg-accent text-white" : "bg-bg-cool text-text-muted hover:bg-gray-border"}`}
            onClick={() => setPmiCategoryFilter(opt.value)}
          >
            {opt.label}
          </button>
        ))}
      </div>

      <Card
        title="PMI 태스크"
        headerBar
        actions={
          canWrite ? (
            <Button
              size="sm"
              variant="ghost"
              icon={Plus}
              onClick={() => setShowPMIModal(true)}
            >
              태스크 추가
            </Button>
          ) : undefined
        }
      >
        {!filteredPmiTasks?.length ? (
          <EmptyState
            icon={Flag}
            title="PMI 태스크 없음"
            description="인수 후 통합 태스크를 추가하세요."
          />
        ) : (
          <DataTable
            columns={
              [
                { key: "title", header: "태스크명" },
                {
                  key: "category",
                  header: "카테고리",
                  render: (t) => (
                    <Badge variant="info">
                      {PMI_CATEGORY_OPTIONS.find((o) => o.value === t.category)
                        ?.label ?? t.category}
                    </Badge>
                  ),
                },
                {
                  key: "priority",
                  header: "우선순위",
                  render: (t) => (
                    <InlineSelect
                      options={PMI_PRIORITY_OPTIONS}
                      value={t.priority}
                      onChange={(v) =>
                        updatePMITask.mutate({
                          taskId: t.id,
                          body: { priority: v as PMIPriority },
                        })
                      }
                      disabled={!canWrite}
                    />
                  ),
                },
                {
                  key: "status",
                  header: "상태",
                  render: (t) => (
                    <InlineSelect
                      options={PMI_STATUS_OPTIONS}
                      value={t.status}
                      onChange={(v) =>
                        updatePMITask.mutate({
                          taskId: t.id,
                          body: { status: v as PMITaskStatus },
                        })
                      }
                      disabled={!canWrite}
                    />
                  ),
                },
                {
                  key: "assignee_name",
                  header: "담당자",
                  render: (t) => (
                    <input
                      key={`${t.id}-assignee`}
                      type="text"
                      className={`${INLINE_INPUT_CLS} w-28`}
                      defaultValue={t.assignee_name ?? ""}
                      placeholder="-"
                      onBlur={(e) => {
                        if (e.target.value.trim() !== (t.assignee_name ?? ""))
                          updatePMITask.mutate({
                            taskId: t.id,
                            body: {
                              assignee_name: e.target.value.trim() || undefined,
                            },
                          });
                      }}
                      disabled={!canWrite}
                    />
                  ),
                },
                {
                  key: "due_date",
                  header: "마감일",
                  render: (t) => (
                    <input
                      type="date"
                      className={`${INLINE_INPUT_CLS} w-32`}
                      defaultValue={t.due_date ?? ""}
                      onChange={(e) =>
                        updatePMITask.mutate({
                          taskId: t.id,
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
                  render: (t) =>
                    canWrite ? (
                      <button
                        className="text-text-muted hover:text-negative p-1 rounded transition-colors"
                        onClick={() => {
                          if (confirm("삭제하시겠습니까?"))
                            deletePMITask.mutate(t.id);
                        }}
                      >
                        <Trash2 size={14} />
                      </button>
                    ) : null,
                },
              ] as Column<PMITask>[]
            }
            data={filteredPmiTasks ?? []}
            keyField="id"
          />
        )}
        <FileUploadZone
          txnId={txnId}
          entityType="PMI"
          embedded
          embeddedLabel={pmiTasks?.length ? "PMI 파일" : "PMI 업로드"}
          uploadLabel="파일 업로드"
          emptyDescription="PMI 자료를 바로 업로드하세요."
          emptyHint="최대 50MB · PDF, DOCX, XLSX, PPTX, HWP 등"
          embeddedSeparator={Boolean(pmiTasks?.length)}
        />
      </Card>

      {/* PMI 태스크 추가 모달 */}
      <Modal
        open={showPMIModal}
        onClose={() => setShowPMIModal(false)}
        title="PMI 태스크 추가"
      >
        <form
          onSubmit={(e) => {
            e.preventDefault();
            createPMITask.mutate(pmiForm, {
              onSuccess: () => {
                setShowPMIModal(false);
                setPmiForm({ category: "INTEGRATION_PLAN", title: "" });
              },
            });
          }}
          className="space-y-4"
        >
          <Select
            label="카테고리"
            options={PMI_CATEGORY_OPTIONS}
            value={pmiForm.category}
            onChange={(e) =>
              setPmiForm({
                ...pmiForm,
                category: e.target.value as PMICategory,
              })
            }
          />
          <Input
            label="태스크명"
            required
            value={pmiForm.title}
            onChange={(e) => setPmiForm({ ...pmiForm, title: e.target.value })}
            placeholder="예: IT 시스템 통합 계획 수립"
          />
          <Input
            label="설명"
            value={pmiForm.description ?? ""}
            onChange={(e) =>
              setPmiForm({
                ...pmiForm,
                description: e.target.value || undefined,
              })
            }
          />
          <Select
            label="우선순위"
            options={PMI_PRIORITY_OPTIONS}
            value={pmiForm.priority ?? "MEDIUM"}
            onChange={(e) =>
              setPmiForm({
                ...pmiForm,
                priority: e.target.value as PMIPriority,
              })
            }
          />
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="담당자"
              value={pmiForm.assignee_name ?? ""}
              onChange={(e) =>
                setPmiForm({
                  ...pmiForm,
                  assignee_name: e.target.value || undefined,
                })
              }
            />
            <Input
              label="담당자 이메일"
              type="email"
              value={pmiForm.assignee_email ?? ""}
              onChange={(e) =>
                setPmiForm({
                  ...pmiForm,
                  assignee_email: e.target.value || undefined,
                })
              }
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="시작일"
              type="date"
              value={pmiForm.start_date ?? ""}
              onChange={(e) =>
                setPmiForm({
                  ...pmiForm,
                  start_date: e.target.value || undefined,
                })
              }
            />
            <Input
              label="마감일"
              type="date"
              value={pmiForm.due_date ?? ""}
              onChange={(e) =>
                setPmiForm({
                  ...pmiForm,
                  due_date: e.target.value || undefined,
                })
              }
            />
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <Button
              variant="ghost"
              type="button"
              onClick={() => setShowPMIModal(false)}
            >
              취소
            </Button>
            <Button type="submit" loading={createPMITask.isPending}>
              추가
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}

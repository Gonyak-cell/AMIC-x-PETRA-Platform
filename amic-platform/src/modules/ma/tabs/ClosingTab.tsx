import { useState } from "react";
import { Plus, Trash2, Flag } from "lucide-react";
import {
  useClosingChecklist,
  useClosingSummary,
  useCreateClosingItem,
  useUpdateClosingItem,
  useDeleteClosingItem,
} from "@/modules/ma/hooks/useClosing";
import type {
  ClosingChecklistCreate,
  ClosingCategory,
  ClosingConditionStatus,
} from "@/modules/ma/types/closing";
import {
  CLOSING_CATEGORY_OPTIONS,
  CLOSING_CONDITION_STATUS_OPTIONS,
} from "@/modules/ma/constants";
import FileUploadZone from "@/modules/ma/components/FileUploadZone";

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
  Select,
} from "@/components/ui";
import type { Column } from "@/components/ui";

interface ClosingTabProps {
  txnId: string;
  canWrite: boolean;
}

export default function ClosingTab({ txnId, canWrite }: ClosingTabProps) {
  const { data: closingItems } = useClosingChecklist(txnId);
  const { data: closingSummary } = useClosingSummary(txnId);
  const createClosingItem = useCreateClosingItem(txnId);
  const updateClosingItem = useUpdateClosingItem(txnId);
  const deleteClosingItem = useDeleteClosingItem(txnId);

  const [showClosingModal, setShowClosingModal] = useState(false);
  const [closingCategoryFilter, setClosingCategoryFilter] =
    useState<string>("ALL");
  const [closingForm, setClosingForm] = useState<ClosingChecklistCreate>({
    category: "REGULATORY" as ClosingCategory,
    title: "",
  });

  const filteredClosingItems =
    closingCategoryFilter === "ALL"
      ? closingItems
      : closingItems?.filter((item) => item.category === closingCategoryFilter);

  return (
    <div className="space-y-4">
      {/* Closing 요약 KPI */}
      {closingSummary && closingSummary.total > 0 && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <KpiCard label="전체 항목" value={String(closingSummary.total)} />
          <KpiCard
            label="완료율"
            value={`${Math.round(closingSummary.completion_rate * 100)}%`}
            variant={
              closingSummary.completion_rate >= 0.8 ? "positive" : "default"
            }
          />
          <KpiCard
            label="진행 중"
            value={String(closingSummary.by_status["IN_PROGRESS"] ?? 0)}
          />
          <KpiCard
            label="대기"
            value={String(closingSummary.by_status["PENDING"] ?? 0)}
            variant={
              (closingSummary.by_status["PENDING"] ?? 0) > 0
                ? "caution"
                : "default"
            }
          />
        </div>
      )}

      {/* 카테고리 필터 */}
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs font-medium text-text-muted">카테고리:</span>
        {[{ value: "ALL", label: "전체" }, ...CLOSING_CATEGORY_OPTIONS].map(
          (opt) => (
            <button
              key={opt.value}
              type="button"
              className={`px-3 py-1 text-xs font-medium rounded-dr-sm transition-colors ${
                closingCategoryFilter === opt.value
                  ? "bg-accent text-white"
                  : "bg-bg-cool text-text-muted hover:bg-gray-border"
              }`}
              onClick={() => setClosingCategoryFilter(opt.value)}
            >
              {opt.label}
            </button>
          ),
        )}
      </div>

      {/* 체크리스트 */}
      <Card
        title="Closing 체크리스트"
        headerBar
        padding="none"
        actions={
          canWrite ? (
            <Button
              icon={Plus}
              onClick={() => setShowClosingModal(true)}
              variant="ghost"
            >
              항목 추가
            </Button>
          ) : undefined
        }
      >
        {!closingItems?.length ? (
          <EmptyState
            icon={Flag}
            title="Closing 항목 없음"
            description="선행조건, 인허가 등 Closing 체크리스트를 추가하세요."
            actionLabel={canWrite ? "항목 추가" : undefined}
            onAction={canWrite ? () => setShowClosingModal(true) : undefined}
          />
        ) : !filteredClosingItems?.length ? (
          <div className="p-8 text-center text-text-muted text-sm">
            선택한 카테고리에 해당하는 항목이 없습니다.
          </div>
        ) : (
          <DataTable
            columns={
              [
                {
                  key: "category",
                  header: "카테고리",
                  render: (r) => (
                    <Badge variant="neutral">
                      {CLOSING_CATEGORY_OPTIONS.find(
                        (o) => o.value === r.category,
                      )?.label ?? r.category}
                    </Badge>
                  ),
                },
                { key: "title", header: "항목" },
                {
                  key: "status",
                  header: "상태",
                  render: (r) => (
                    <InlineSelect
                      options={CLOSING_CONDITION_STATUS_OPTIONS}
                      value={r.status}
                      onChange={(v) =>
                        updateClosingItem.mutate({
                          itemId: r.id,
                          body: { status: v as ClosingConditionStatus },
                        })
                      }
                      disabled={!canWrite}
                    />
                  ),
                },
                {
                  key: "responsible_party",
                  header: "담당",
                  render: (r) => (
                    <input
                      key={`${r.id}-resp-${r.responsible_party}`}
                      type="text"
                      className={`${INLINE_INPUT_CLS} w-28`}
                      defaultValue={r.responsible_party ?? ""}
                      placeholder="담당자"
                      onBlur={(e) => {
                        const v = e.target.value || undefined;
                        if (v !== (r.responsible_party ?? undefined)) {
                          updateClosingItem.mutate({
                            itemId: r.id,
                            body: { responsible_party: v },
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
                        updateClosingItem.mutate({
                          itemId: r.id,
                          body: { due_date: e.target.value || undefined },
                        })
                      }
                      disabled={!canWrite}
                    />
                  ),
                },
                {
                  key: "completed_date",
                  header: "완료일",
                  render: (r) => (
                    <input
                      key={`${r.id}-comp-${r.completed_date}`}
                      type="date"
                      className={`${INLINE_INPUT_CLS} w-32`}
                      defaultValue={r.completed_date ?? ""}
                      onChange={(e) =>
                        updateClosingItem.mutate({
                          itemId: r.id,
                          body: {
                            completed_date: e.target.value || undefined,
                          },
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
                          if (
                            confirm("이 체크리스트 항목을 삭제하시겠습니까?")
                          ) {
                            deleteClosingItem.mutate(r.id);
                          }
                        }}
                      >
                        <Trash2 size={14} />
                      </button>
                    ) : null,
                },
              ] as Column<(typeof closingItems)[number]>[]
            }
            data={filteredClosingItems ?? []}
            keyField="id"
          />
        )}
        <FileUploadZone txnId={txnId} entityType="CLOSING" embedded />
      </Card>

      {/* Closing 체크리스트 추가 모달 */}
      <Modal
        open={showClosingModal}
        onClose={() => setShowClosingModal(false)}
        title="Closing 체크리스트 항목 추가"
      >
        <form
          onSubmit={(e) => {
            e.preventDefault();
            createClosingItem.mutate(closingForm, {
              onSuccess: () => {
                setShowClosingModal(false);
                setClosingForm({ category: "REGULATORY", title: "" });
              },
            });
          }}
          className="space-y-4"
        >
          <Select
            label="카테고리"
            options={CLOSING_CATEGORY_OPTIONS}
            value={closingForm.category}
            onChange={(e) =>
              setClosingForm({
                ...closingForm,
                category: e.target.value as ClosingCategory,
              })
            }
          />
          <Input
            label="항목명"
            required
            value={closingForm.title}
            onChange={(e) =>
              setClosingForm({ ...closingForm, title: e.target.value })
            }
            placeholder="예: 공정거래위원회 기업결합신고"
          />
          <Input
            label="설명"
            value={closingForm.description ?? ""}
            onChange={(e) =>
              setClosingForm({
                ...closingForm,
                description: e.target.value || undefined,
              })
            }
          />
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="담당자"
              value={closingForm.responsible_party ?? ""}
              onChange={(e) =>
                setClosingForm({
                  ...closingForm,
                  responsible_party: e.target.value || undefined,
                })
              }
            />
            <Input
              label="담당자 이메일"
              type="email"
              value={closingForm.responsible_email ?? ""}
              onChange={(e) =>
                setClosingForm({
                  ...closingForm,
                  responsible_email: e.target.value || undefined,
                })
              }
            />
          </div>
          <Input
            label="기한"
            type="date"
            value={closingForm.due_date ?? ""}
            onChange={(e) =>
              setClosingForm({
                ...closingForm,
                due_date: e.target.value || undefined,
              })
            }
          />
          <div className="flex justify-end gap-2 pt-2">
            <Button
              variant="ghost"
              type="button"
              onClick={() => setShowClosingModal(false)}
            >
              취소
            </Button>
            <Button type="submit" loading={createClosingItem.isPending}>
              추가
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}

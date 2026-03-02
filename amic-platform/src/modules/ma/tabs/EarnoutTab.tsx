import { useState } from "react";
import { Plus, Trash2, DollarSign } from "lucide-react";
import {
  useEarnoutMilestones,
  useEarnoutSummary,
  useCreateEarnout,
  useUpdateEarnout,
  useDeleteEarnout,
} from "@/modules/ma/hooks/useEarnout";
import type {
  EarnoutCreate,
  EarnoutStatus,
  EarnoutMetric,
} from "@/modules/ma/types/earnout";
import {
  EARNOUT_STATUS_OPTIONS,
  EARNOUT_METRIC_OPTIONS,
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
} from "@/components/ui";
import type { Column } from "@/components/ui";

import { formatKRW as formatAmount } from "@/modules/ma/utils/format";

interface EarnoutTabProps {
  txnId: string;
  canWrite: boolean;
}

export default function EarnoutTab({ txnId, canWrite }: EarnoutTabProps) {
  const { data: earnoutMilestones } = useEarnoutMilestones(txnId);
  const { data: earnoutSummary } = useEarnoutSummary(txnId);
  const createEarnout = useCreateEarnout(txnId);
  const updateEarnout = useUpdateEarnout(txnId);
  const deleteEarnout = useDeleteEarnout(txnId);

  const [showEarnoutModal, setShowEarnoutModal] = useState(false);
  const [earnoutForm, setEarnoutForm] = useState<EarnoutCreate>({
    title: "",
    metric: "REVENUE" as EarnoutMetric,
    target_value: 0,
  });

  return (
    <div className="space-y-4">
      {/* KPI 요약 */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <KpiCard
          label="총 마일스톤"
          value={String(earnoutSummary?.total ?? 0)}
        />
        <KpiCard
          label="목표 합계"
          value={formatAmount(earnoutSummary?.total_target ?? 0)}
        />
        <KpiCard
          label="실적 합계"
          value={formatAmount(earnoutSummary?.total_actual ?? 0)}
          variant={
            (earnoutSummary?.total_actual ?? 0) >=
            (earnoutSummary?.total_target ?? 1)
              ? "positive"
              : "caution"
          }
        />
        <KpiCard
          label="지급 합계"
          value={formatAmount(earnoutSummary?.total_payment ?? 0)}
        />
      </div>

      <Card
        title="어닝아웃 마일스톤"
        headerBar
        actions={
          canWrite ? (
            <Button
              size="sm"
              icon={Plus}
              onClick={() => setShowEarnoutModal(true)}
            >
              마일스톤 추가
            </Button>
          ) : undefined
        }
      >
        {!earnoutMilestones?.length ? (
          <EmptyState
            icon={DollarSign}
            title="어닝아웃 없음"
            description="어닝아웃 마일스톤을 추가하세요."
          />
        ) : (
          <DataTable
            columns={
              [
                { key: "title", header: "마일스톤" },
                {
                  key: "metric",
                  header: "지표",
                  render: (m) =>
                    EARNOUT_METRIC_OPTIONS.find((o) => o.value === m.metric)
                      ?.label ?? m.metric,
                },
                {
                  key: "target_value",
                  header: "목표",
                  render: (m) =>
                    `${formatAmount(m.target_value)} ${m.currency}`,
                },
                {
                  key: "actual_value",
                  header: "실적",
                  render: (m) => (
                    <input
                      key={`${m.id}-actual`}
                      type="number"
                      className={`${INLINE_INPUT_CLS} w-24 text-right`}
                      defaultValue={m.actual_value ?? ""}
                      placeholder="-"
                      onBlur={(e) => {
                        const v =
                          e.target.value === ""
                            ? undefined
                            : Number(e.target.value);
                        const current =
                          m.actual_value != null
                            ? Number(m.actual_value)
                            : undefined;
                        if (v !== current)
                          updateEarnout.mutate({
                            milestoneId: m.id,
                            body: { actual_value: v },
                          });
                      }}
                      disabled={!canWrite}
                    />
                  ),
                },
                {
                  key: "status",
                  header: "상태",
                  render: (m) => (
                    <InlineSelect
                      options={EARNOUT_STATUS_OPTIONS}
                      value={m.status}
                      onChange={(v) =>
                        updateEarnout.mutate({
                          milestoneId: m.id,
                          body: { status: v as EarnoutStatus },
                        })
                      }
                      disabled={!canWrite}
                    />
                  ),
                },
                {
                  key: "period",
                  header: "측정 기간",
                  render: (m) =>
                    m.measurement_start && m.measurement_end
                      ? `${m.measurement_start} ~ ${m.measurement_end}`
                      : "-",
                },
                {
                  key: "payment_amount",
                  header: "지급액",
                  render: (m) => (
                    <input
                      key={`${m.id}-payment`}
                      type="number"
                      className={`${INLINE_INPUT_CLS} w-24 text-right`}
                      defaultValue={m.payment_amount ?? ""}
                      placeholder="-"
                      onBlur={(e) => {
                        const v =
                          e.target.value === ""
                            ? undefined
                            : Number(e.target.value);
                        const current =
                          m.payment_amount != null
                            ? Number(m.payment_amount)
                            : undefined;
                        if (v !== current)
                          updateEarnout.mutate({
                            milestoneId: m.id,
                            body: { payment_amount: v },
                          });
                      }}
                      disabled={!canWrite}
                    />
                  ),
                },
                {
                  key: "actions",
                  header: "",
                  render: (m) =>
                    canWrite ? (
                      <button
                        className="text-text-muted hover:text-negative p-1 rounded transition-colors"
                        onClick={() => {
                          if (confirm("삭제하시겠습니까?"))
                            deleteEarnout.mutate(m.id);
                        }}
                      >
                        <Trash2 size={14} />
                      </button>
                    ) : null,
                },
              ] as Column<(typeof earnoutMilestones)[number]>[]
            }
            data={earnoutMilestones ?? []}
            keyField="id"
          />
        )}
        <FileUploadZone txnId={txnId} entityType="EARNOUT" embedded />
      </Card>

      {/* 어닝아웃 마일스톤 추가 모달 */}
      <Modal
        open={showEarnoutModal}
        onClose={() => setShowEarnoutModal(false)}
        title="어닝아웃 마일스톤 추가"
      >
        <form
          onSubmit={(e) => {
            e.preventDefault();
            createEarnout.mutate(earnoutForm, {
              onSuccess: () => {
                setShowEarnoutModal(false);
                setEarnoutForm({
                  title: "",
                  metric: "REVENUE",
                  target_value: 0,
                });
              },
            });
          }}
          className="space-y-4"
        >
          <Input
            label="마일스톤명"
            required
            value={earnoutForm.title}
            onChange={(e) =>
              setEarnoutForm({ ...earnoutForm, title: e.target.value })
            }
            placeholder="예: 2026년 매출 달성 조건"
          />
          <Input
            label="설명"
            value={earnoutForm.description ?? ""}
            onChange={(e) =>
              setEarnoutForm({
                ...earnoutForm,
                description: e.target.value || undefined,
              })
            }
          />
          <Select
            label="지표"
            options={EARNOUT_METRIC_OPTIONS}
            value={earnoutForm.metric}
            onChange={(e) =>
              setEarnoutForm({
                ...earnoutForm,
                metric: e.target.value as EarnoutMetric,
              })
            }
          />
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="목표 금액"
              type="number"
              required
              value={earnoutForm.target_value.toString()}
              onChange={(e) =>
                setEarnoutForm({
                  ...earnoutForm,
                  target_value: Number(e.target.value) || 0,
                })
              }
            />
            <Select
              label="통화"
              options={[
                { value: "KRW", label: "KRW (원)" },
                { value: "USD", label: "USD ($)" },
                { value: "EUR", label: "EUR (유로)" },
              ]}
              value={earnoutForm.currency ?? "KRW"}
              onChange={(e) =>
                setEarnoutForm({ ...earnoutForm, currency: e.target.value })
              }
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="측정 시작일"
              type="date"
              value={earnoutForm.measurement_start ?? ""}
              onChange={(e) =>
                setEarnoutForm({
                  ...earnoutForm,
                  measurement_start: e.target.value || undefined,
                })
              }
            />
            <Input
              label="측정 종료일"
              type="date"
              value={earnoutForm.measurement_end ?? ""}
              onChange={(e) =>
                setEarnoutForm({
                  ...earnoutForm,
                  measurement_end: e.target.value || undefined,
                })
              }
            />
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <Button
              variant="ghost"
              type="button"
              onClick={() => setShowEarnoutModal(false)}
            >
              취소
            </Button>
            <Button type="submit" loading={createEarnout.isPending}>
              추가
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}

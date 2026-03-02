import { useState } from "react";
import { Plus, Trash2 } from "lucide-react";
import {
  useRisks,
  useRiskSummary,
  useCreateRisk,
  useUpdateRisk,
  useDeleteRisk,
} from "@/modules/ma/hooks/useRisks";
import type {
  RiskItemCreate,
  RiskCategory,
  RiskSeverity,
  RiskLikelihood,
  RiskStatus,
} from "@/modules/ma/types/risk";
import {
  RISK_CATEGORY_OPTIONS,
  RISK_SEVERITY_OPTIONS,
  RISK_LIKELIHOOD_OPTIONS,
  RISK_STATUS_OPTIONS,
} from "@/modules/ma/constants";

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

interface RisksTabProps {
  txnId: string;
  canWrite: boolean;
}

export default function RisksTab({ txnId, canWrite }: RisksTabProps) {
  const { data: risks } = useRisks(txnId);
  const { data: riskSummary } = useRiskSummary(txnId);
  const createRisk = useCreateRisk(txnId);
  const updateRisk = useUpdateRisk(txnId);
  const deleteRisk = useDeleteRisk(txnId);

  const [showRiskModal, setShowRiskModal] = useState(false);
  const [riskCategoryFilter, setRiskCategoryFilter] = useState<string>("ALL");
  const [riskForm, setRiskForm] = useState<RiskItemCreate>({
    category: "REGULATORY" as RiskCategory,
    title: "",
    severity: "MEDIUM" as RiskSeverity,
    likelihood: "MEDIUM" as RiskLikelihood,
  });

  const filteredRisks =
    riskCategoryFilter === "ALL"
      ? risks
      : risks?.filter((r) => r.category === riskCategoryFilter);

  return (
    <div className="space-y-4">
      {/* KPI 요약 */}
      {riskSummary && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <KpiCard label="총 리스크" value={String(riskSummary.total)} />
          <KpiCard
            label="미완화 Critical"
            value={String(riskSummary.unmitigated_critical)}
            variant={
              riskSummary.unmitigated_critical > 0 ? "danger" : "default"
            }
          />
          <KpiCard
            label="평균 점수"
            value={String(riskSummary.avg_risk_score)}
            subtitle="/20"
          />
          <KpiCard
            label="카테고리"
            value={String(riskSummary.by_category.length)}
          />
        </div>
      )}

      <Card
        title="리스크 레지스터"
        headerBar
        actions={
          canWrite ? (
            <Button size="sm" onClick={() => setShowRiskModal(true)}>
              <Plus size={14} className="mr-1" />
              리스크 추가
            </Button>
          ) : undefined
        }
      >
        {/* 카테고리 필터 */}
        <div className="flex flex-wrap items-center gap-2 mb-4">
          <span className="text-xs font-medium text-text-muted">카테고리:</span>
          {[{ value: "ALL", label: "전체" }, ...RISK_CATEGORY_OPTIONS].map(
            (opt) => (
              <button
                key={opt.value}
                type="button"
                className={`px-3 py-1 text-xs font-medium rounded-dr-sm transition-colors ${
                  riskCategoryFilter === opt.value
                    ? "bg-accent text-white"
                    : "bg-bg-cool text-text-muted hover:bg-gray-border"
                }`}
                onClick={() => setRiskCategoryFilter(opt.value)}
              >
                {opt.label}
              </button>
            ),
          )}
        </div>

        {!filteredRisks?.length ? (
          <EmptyState
            title="리스크 없음"
            description="리스크 항목을 추가하세요."
          />
        ) : (
          <DataTable
            columns={
              [
                {
                  key: "title",
                  header: "제목",
                  render: (risk) => (
                    <span className="font-medium">{risk.title}</span>
                  ),
                },
                {
                  key: "category",
                  header: "카테고리",
                  render: (risk) => (
                    <Badge variant="neutral">
                      {RISK_CATEGORY_OPTIONS.find(
                        (o) => o.value === risk.category,
                      )?.label ?? risk.category}
                    </Badge>
                  ),
                },
                {
                  key: "severity",
                  header: "심각도",
                  render: (risk) => (
                    <InlineSelect
                      options={RISK_SEVERITY_OPTIONS}
                      value={risk.severity}
                      onChange={(v) =>
                        updateRisk.mutate({
                          itemId: risk.id,
                          body: { severity: v as RiskSeverity },
                        })
                      }
                      disabled={!canWrite}
                    />
                  ),
                },
                {
                  key: "likelihood",
                  header: "발생확률",
                  render: (risk) => (
                    <InlineSelect
                      options={RISK_LIKELIHOOD_OPTIONS}
                      value={risk.likelihood}
                      onChange={(v) =>
                        updateRisk.mutate({
                          itemId: risk.id,
                          body: { likelihood: v as RiskLikelihood },
                        })
                      }
                      disabled={!canWrite}
                    />
                  ),
                },
                {
                  key: "risk_score",
                  header: "점수",
                  render: (risk) => (
                    <span
                      className={`font-mono font-bold ${(risk.risk_score ?? 0) >= 12 ? "text-negative" : (risk.risk_score ?? 0) >= 6 ? "text-caution" : "text-positive"}`}
                    >
                      {risk.risk_score ?? "-"}
                    </span>
                  ),
                },
                {
                  key: "status",
                  header: "상태",
                  render: (risk) => (
                    <InlineSelect
                      options={RISK_STATUS_OPTIONS}
                      value={risk.status}
                      onChange={(v) =>
                        updateRisk.mutate({
                          itemId: risk.id,
                          body: { status: v as RiskStatus },
                        })
                      }
                      disabled={!canWrite}
                    />
                  ),
                },
                {
                  key: "owner_email",
                  header: "담당",
                  render: (risk) => (
                    <input
                      key={`${risk.id}-owner`}
                      type="text"
                      className={`${INLINE_INPUT_CLS} w-36`}
                      defaultValue={risk.owner_email ?? ""}
                      placeholder="-"
                      onBlur={(e) => {
                        if (e.target.value.trim() !== (risk.owner_email ?? ""))
                          updateRisk.mutate({
                            itemId: risk.id,
                            body: {
                              owner_email: e.target.value.trim() || undefined,
                            },
                          });
                      }}
                      disabled={!canWrite}
                    />
                  ),
                },
                {
                  key: "actions",
                  header: "",
                  width: "40px",
                  render: (risk) =>
                    canWrite ? (
                      <button
                        className="text-text-muted hover:text-negative p-1 rounded transition-colors"
                        onClick={() => {
                          if (confirm("삭제하시겠습니까?"))
                            deleteRisk.mutate(risk.id);
                        }}
                      >
                        <Trash2 size={14} />
                      </button>
                    ) : null,
                },
              ] as Column<(typeof filteredRisks)[number]>[]
            }
            data={filteredRisks ?? []}
            keyField="id"
          />
        )}
      </Card>

      {/* 리스크 추가 모달 */}
      <Modal
        open={showRiskModal}
        onClose={() => setShowRiskModal(false)}
        title="리스크 추가"
      >
        <div className="space-y-3">
          <Select
            label="카테고리"
            options={RISK_CATEGORY_OPTIONS}
            value={riskForm.category}
            onChange={(e) =>
              setRiskForm((f) => ({
                ...f,
                category: e.target.value as RiskCategory,
              }))
            }
          />
          <Input
            label="제목"
            value={riskForm.title}
            onChange={(e) =>
              setRiskForm((f) => ({ ...f, title: e.target.value }))
            }
            required
          />
          <Input
            label="설명"
            value={riskForm.description ?? ""}
            onChange={(e) =>
              setRiskForm((f) => ({ ...f, description: e.target.value }))
            }
          />
          <div className="grid grid-cols-2 gap-3">
            <Select
              label="심각도"
              options={RISK_SEVERITY_OPTIONS}
              value={riskForm.severity ?? "MEDIUM"}
              onChange={(e) =>
                setRiskForm((f) => ({
                  ...f,
                  severity: e.target.value as RiskSeverity,
                }))
              }
            />
            <Select
              label="발생확률"
              options={RISK_LIKELIHOOD_OPTIONS}
              value={riskForm.likelihood ?? "MEDIUM"}
              onChange={(e) =>
                setRiskForm((f) => ({
                  ...f,
                  likelihood: e.target.value as RiskLikelihood,
                }))
              }
            />
          </div>
          <Input
            label="완화 전략"
            value={riskForm.mitigation_strategy ?? ""}
            onChange={(e) =>
              setRiskForm((f) => ({
                ...f,
                mitigation_strategy: e.target.value,
              }))
            }
          />
          <Input
            label="담당자 이메일"
            value={riskForm.owner_email ?? ""}
            onChange={(e) =>
              setRiskForm((f) => ({ ...f, owner_email: e.target.value }))
            }
          />
          <Input
            label="기한"
            type="date"
            value={riskForm.due_date ?? ""}
            onChange={(e) =>
              setRiskForm((f) => ({ ...f, due_date: e.target.value }))
            }
          />
          <Button
            disabled={!riskForm.title}
            onClick={() => {
              createRisk.mutate(riskForm);
              setShowRiskModal(false);
              setRiskForm({
                category: "REGULATORY",
                title: "",
                severity: "MEDIUM",
                likelihood: "MEDIUM",
              });
            }}
          >
            추가
          </Button>
        </div>
      </Modal>
    </div>
  );
}

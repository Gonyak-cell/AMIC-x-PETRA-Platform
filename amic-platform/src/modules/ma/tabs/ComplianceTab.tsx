import { useState } from "react";
import { Plus, Trash2 } from "lucide-react";
import {
  useCompliance,
  useComplianceSummary,
  useCreateCompliance,
  useUpdateCompliance,
  useDeleteCompliance,
} from "@/modules/ma/hooks/useCompliance";
import type {
  ComplianceItemCreate,
  ComplianceCategory as CompCat,
  ComplianceStatus,
} from "@/modules/ma/types/compliance";
import {
  COMPLIANCE_CATEGORY_OPTIONS,
  COMPLIANCE_STATUS_OPTIONS,
} from "@/modules/ma/constants";
import PermitAnalysisPanel from "@/modules/ma/components/PermitAnalysisPanel";

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

interface ComplianceTabProps {
  txnId: string;
  canWrite: boolean;
}

export default function ComplianceTab({ txnId, canWrite }: ComplianceTabProps) {
  const { data: complianceItems } = useCompliance(txnId);
  const { data: complianceSummary } = useComplianceSummary(txnId);
  const createCompliance = useCreateCompliance(txnId);
  const updateCompliance = useUpdateCompliance(txnId);
  const deleteCompliance = useDeleteCompliance(txnId);

  const [showComplianceModal, setShowComplianceModal] = useState(false);
  const [complianceCategoryFilter, setComplianceCategoryFilter] =
    useState<string>("ALL");
  const [complianceForm, setComplianceForm] = useState<ComplianceItemCreate>({
    category: "ANTITRUST" as CompCat,
    requirement: "",
  });

  const filteredComplianceItems =
    complianceCategoryFilter === "ALL"
      ? complianceItems
      : complianceItems?.filter((c) => c.category === complianceCategoryFilter);

  return (
    <div className="space-y-4">
      {/* KPI 요약 */}
      {complianceSummary && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <KpiCard label="총 항목" value={String(complianceSummary.total)} />
          <KpiCard
            label="준수율"
            value={`${complianceSummary.compliance_rate}%`}
          />
          <KpiCard
            label="주의/미준수"
            value={String(complianceSummary.flagged_count)}
            variant={complianceSummary.flagged_count > 0 ? "danger" : "default"}
          />
          <KpiCard
            label="기한 초과"
            value={String(complianceSummary.overdue_count)}
            variant={complianceSummary.overdue_count > 0 ? "danger" : "default"}
          />
        </div>
      )}

      <Card
        title="컴플라이언스 체크리스트"
        headerBar
        actions={
          canWrite ? (
            <Button size="sm" onClick={() => setShowComplianceModal(true)}>
              <Plus size={14} className="mr-1" />
              항목 추가
            </Button>
          ) : undefined
        }
      >
        {/* 카테고리 필터 */}
        <div className="flex flex-wrap items-center gap-2 mb-4">
          <span className="text-xs font-medium text-text-muted">카테고리:</span>
          {[
            { value: "ALL", label: "전체" },
            ...COMPLIANCE_CATEGORY_OPTIONS,
          ].map((opt) => (
            <button
              key={opt.value}
              type="button"
              className={`px-3 py-1 text-xs font-medium rounded-dr-sm transition-colors ${
                complianceCategoryFilter === opt.value
                  ? "bg-accent text-white"
                  : "bg-bg-cool text-text-muted hover:bg-gray-border"
              }`}
              onClick={() => setComplianceCategoryFilter(opt.value)}
            >
              {opt.label}
            </button>
          ))}
        </div>

        {!filteredComplianceItems?.length ? (
          <EmptyState
            title="컴플라이언스 항목 없음"
            description="규제 요건을 추가하세요."
          />
        ) : (
          <DataTable
            columns={
              [
                {
                  key: "requirement",
                  header: "요건",
                  render: (item) => (
                    <span className="font-medium">{item.requirement}</span>
                  ),
                },
                {
                  key: "category",
                  header: "카테고리",
                  render: (item) => (
                    <Badge variant="neutral">
                      {COMPLIANCE_CATEGORY_OPTIONS.find(
                        (o) => o.value === item.category,
                      )?.label ?? item.category}
                    </Badge>
                  ),
                },
                {
                  key: "jurisdiction",
                  header: "관할",
                  render: (item) => (
                    <span className="text-xs">{item.jurisdiction ?? "-"}</span>
                  ),
                },
                {
                  key: "regulatory_body",
                  header: "규제 기관",
                  render: (item) => (
                    <span className="text-xs">
                      {item.regulatory_body ?? "-"}
                    </span>
                  ),
                },
                {
                  key: "status",
                  header: "상태",
                  render: (item) => (
                    <InlineSelect
                      options={COMPLIANCE_STATUS_OPTIONS}
                      value={item.status}
                      onChange={(v) =>
                        updateCompliance.mutate({
                          itemId: item.id,
                          body: { status: v as ComplianceStatus },
                        })
                      }
                      disabled={!canWrite}
                    />
                  ),
                },
                {
                  key: "due_date",
                  header: "기한",
                  render: (item) => (
                    <input
                      type="date"
                      className={`${INLINE_INPUT_CLS} w-32`}
                      defaultValue={item.due_date ?? ""}
                      onChange={(e) =>
                        updateCompliance.mutate({
                          itemId: item.id,
                          body: { due_date: e.target.value || undefined },
                        })
                      }
                      disabled={!canWrite}
                    />
                  ),
                },
                {
                  key: "assignee_email",
                  header: "담당",
                  render: (item) => (
                    <input
                      key={`${item.id}-assignee`}
                      type="text"
                      className={`${INLINE_INPUT_CLS} w-36`}
                      defaultValue={item.assignee_email ?? ""}
                      placeholder="-"
                      onBlur={(e) => {
                        if (
                          e.target.value.trim() !== (item.assignee_email ?? "")
                        )
                          updateCompliance.mutate({
                            itemId: item.id,
                            body: {
                              assignee_email:
                                e.target.value.trim() || undefined,
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
                  render: (item) =>
                    canWrite ? (
                      <button
                        className="text-text-muted hover:text-negative p-1 rounded transition-colors"
                        onClick={() => {
                          if (confirm("삭제하시겠습니까?"))
                            deleteCompliance.mutate(item.id);
                        }}
                      >
                        <Trash2 size={14} />
                      </button>
                    ) : null,
                },
              ] as Column<(typeof filteredComplianceItems)[number]>[]
            }
            data={filteredComplianceItems ?? []}
            keyField="id"
          />
        )}
      </Card>

      {/* 컴플라이언스 추가 모달 */}
      <Modal
        open={showComplianceModal}
        onClose={() => setShowComplianceModal(false)}
        title="컴플라이언스 항목 추가"
      >
        <div className="space-y-3">
          <Select
            label="카테고리"
            options={COMPLIANCE_CATEGORY_OPTIONS}
            value={complianceForm.category}
            onChange={(e) =>
              setComplianceForm((f) => ({
                ...f,
                category: e.target.value as CompCat,
              }))
            }
          />
          <Input
            label="규제 요건"
            value={complianceForm.requirement}
            onChange={(e) =>
              setComplianceForm((f) => ({
                ...f,
                requirement: e.target.value,
              }))
            }
            required
          />
          <Input
            label="설명"
            value={complianceForm.description ?? ""}
            onChange={(e) =>
              setComplianceForm((f) => ({
                ...f,
                description: e.target.value,
              }))
            }
          />
          <div className="grid grid-cols-2 gap-3">
            <Input
              label="관할권"
              value={complianceForm.jurisdiction ?? ""}
              onChange={(e) =>
                setComplianceForm((f) => ({
                  ...f,
                  jurisdiction: e.target.value,
                }))
              }
              placeholder="예: 대한민국"
            />
            <Input
              label="규제 기관"
              value={complianceForm.regulatory_body ?? ""}
              onChange={(e) =>
                setComplianceForm((f) => ({
                  ...f,
                  regulatory_body: e.target.value,
                }))
              }
              placeholder="예: 공정거래위원회"
            />
          </div>
          <Input
            label="담당자 이메일"
            value={complianceForm.assignee_email ?? ""}
            onChange={(e) =>
              setComplianceForm((f) => ({
                ...f,
                assignee_email: e.target.value,
              }))
            }
          />
          <Input
            label="기한"
            type="date"
            value={complianceForm.due_date ?? ""}
            onChange={(e) =>
              setComplianceForm((f) => ({ ...f, due_date: e.target.value }))
            }
          />
          <Button
            disabled={!complianceForm.requirement}
            onClick={() => {
              createCompliance.mutate(complianceForm);
              setShowComplianceModal(false);
              setComplianceForm({ category: "ANTITRUST", requirement: "" });
            }}
          >
            추가
          </Button>
        </div>
      </Modal>

      {/* 인허가 분석 패널 */}
      <PermitAnalysisPanel txnId={txnId} canWrite={canWrite} />
    </div>
  );
}

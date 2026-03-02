import { useState } from "react";
import { Plus, Trash2, Sparkles } from "lucide-react";
import {
  useContracts,
  useContractSummary,
  useCreateContract,
  useUpdateContract,
  useDeleteContract,
  useAnalyzeContract,
} from "@/modules/ma/hooks/useContracts";
import type {
  ContractCreate,
  ContractStatus,
  SignatureStatus as SigStatus,
} from "@/modules/ma/types/contract";
import {
  CONTRACT_TYPE_OPTIONS,
  CONTRACT_STATUS_OPTIONS,
  SIGNATURE_STATUS_OPTIONS,
} from "@/modules/ma/constants";
import FileUploadZone from "@/modules/ma/components/FileUploadZone";
import { ContractNegotiationWorkspace } from "@/modules/ma/components/negotiation/ContractNegotiationWorkspace";
import LegalDocumentsTab from "@/modules/docs/components/LegalDocumentsTab";

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
  Tabs,
} from "@/components/ui";
import type { Column } from "@/components/ui";

interface ContractsTabProps {
  txnId: string;
  canWrite: boolean;
}

export default function ContractsTab({ txnId, canWrite }: ContractsTabProps) {
  const { data: contracts } = useContracts(txnId);
  const { data: contractSummary } = useContractSummary(txnId);
  const createContract = useCreateContract(txnId);
  const updateContract = useUpdateContract(txnId);
  const deleteContract = useDeleteContract(txnId);
  const analyzeContract = useAnalyzeContract(txnId);
  const [contractSubTab, setContractSubTab] = useState<
    "negotiation-workspace" | "contracts" | "legal-docs"
  >("negotiation-workspace");

  const [showContractModal, setShowContractModal] = useState(false);
  const [contractForm, setContractForm] = useState<ContractCreate>({
    title: "",
  });

  return (
    <div className="space-y-4">
      {/* 서브탭: 계약 / 법률 문서 */}
      <Tabs
        tabs={[
          { id: "negotiation-workspace", label: "협상 워크스페이스" },
          { id: "contracts", label: "계약 목록" },
          { id: "legal-docs", label: "법률 문서" },
        ]}
        activeTab={contractSubTab}
        onTabChange={(tab) =>
          setContractSubTab(
            tab as "negotiation-workspace" | "contracts" | "legal-docs",
          )
        }
        variant="pill"
        size="sm"
      />

      {/* 협상 워크스페이스 서브탭 */}
      {contractSubTab === "negotiation-workspace" && (
        <ContractNegotiationWorkspace txnId={txnId} />
      )}

      {/* 법률 문서 서브탭 */}
      {contractSubTab === "legal-docs" && <LegalDocumentsTab txnId={txnId} />}

      {/* 계약 서브탭 */}
      {contractSubTab === "contracts" && (
        <>
          {/* 계약 요약 KPI */}
          {contractSummary && contractSummary.total > 0 && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <KpiCard
                label="전체 계약"
                value={String(contractSummary.total)}
              />
              <KpiCard
                label="서명 대기"
                value={String(contractSummary.pending_signatures)}
                variant={
                  contractSummary.pending_signatures > 0 ? "caution" : "default"
                }
              />
              <KpiCard
                label="체결 완료"
                value={String(contractSummary.fully_executed)}
                variant="positive"
              />
              <KpiCard
                label="유형별"
                value={String(Object.keys(contractSummary.by_type).length)}
              />
            </div>
          )}

          {/* 계약 목록 */}
          <Card title="계약서 목록" headerBar padding="none">
            {!contracts?.length ? (
              <EmptyState
                icon={Sparkles}
                title="계약서 없음"
                description="SPA, SHA 등 계약서를 등록하세요."
                actionLabel={canWrite ? "계약서 추가" : undefined}
                onAction={
                  canWrite ? () => setShowContractModal(true) : undefined
                }
              />
            ) : (
              <DataTable
                columns={
                  [
                    { key: "title", header: "제목" },
                    {
                      key: "contract_type",
                      header: "유형",
                      render: (r) => (
                        <Badge variant="neutral">
                          {CONTRACT_TYPE_OPTIONS.find(
                            (o) => o.value === r.contract_type,
                          )?.label ?? r.contract_type}
                        </Badge>
                      ),
                    },
                    {
                      key: "status",
                      header: "상태",
                      render: (r) => (
                        <InlineSelect
                          options={CONTRACT_STATUS_OPTIONS}
                          value={r.status}
                          onChange={(v) =>
                            updateContract.mutate({
                              contractId: r.id,
                              body: { status: v as ContractStatus },
                            })
                          }
                          disabled={!canWrite}
                        />
                      ),
                    },
                    {
                      key: "counterparty_name",
                      header: "상대방",
                      render: (r) => r.counterparty_name ?? "-",
                    },
                    {
                      key: "current_version",
                      header: "버전",
                      align: "right",
                      render: (r) => `v${r.current_version}`,
                    },
                    {
                      key: "seller_signature",
                      header: "매도측 서명",
                      render: (r) => (
                        <InlineSelect
                          options={SIGNATURE_STATUS_OPTIONS}
                          value={r.seller_signature}
                          onChange={(v) =>
                            updateContract.mutate({
                              contractId: r.id,
                              body: { seller_signature: v as SigStatus },
                            })
                          }
                          disabled={!canWrite}
                        />
                      ),
                    },
                    {
                      key: "buyer_signature",
                      header: "매수측 서명",
                      render: (r) => (
                        <InlineSelect
                          options={SIGNATURE_STATUS_OPTIONS}
                          value={r.buyer_signature}
                          onChange={(v) =>
                            updateContract.mutate({
                              contractId: r.id,
                              body: { buyer_signature: v as SigStatus },
                            })
                          }
                          disabled={!canWrite}
                        />
                      ),
                    },
                    {
                      key: "effective_date",
                      header: "효력일",
                      render: (r) => (
                        <input
                          key={`${r.id}-eff-${r.effective_date}`}
                          type="date"
                          className={`${INLINE_INPUT_CLS} w-32`}
                          defaultValue={r.effective_date ?? ""}
                          onChange={(e) =>
                            updateContract.mutate({
                              contractId: r.id,
                              body: {
                                effective_date: e.target.value || undefined,
                              },
                            })
                          }
                          disabled={!canWrite}
                        />
                      ),
                    },
                    {
                      key: "ai_actions",
                      header: "",
                      width: "70px",
                      render: (r) =>
                        canWrite ? (
                          <div className="flex items-center gap-1">
                            <button
                              className="text-text-muted hover:text-accent p-1 rounded transition-colors"
                              title="AI 분석"
                              onClick={() => analyzeContract.mutate(r.id)}
                            >
                              <Sparkles size={14} />
                            </button>
                            <button
                              className="text-text-muted hover:text-negative p-1 rounded transition-colors"
                              title="삭제"
                              onClick={() => {
                                if (confirm("이 계약서를 삭제하시겠습니까?")) {
                                  deleteContract.mutate(r.id);
                                }
                              }}
                            >
                              <Trash2 size={14} />
                            </button>
                          </div>
                        ) : null,
                    },
                  ] as Column<(typeof contracts)[number]>[]
                }
                data={contracts}
                keyField="id"
              />
            )}
            <FileUploadZone txnId={txnId} entityType="CONTRACT" embedded />
          </Card>
        </>
      )}

      {/* 계약서 추가 모달 */}
      <Modal
        open={showContractModal}
        onClose={() => setShowContractModal(false)}
        title="계약서 추가"
      >
        <form
          onSubmit={(e) => {
            e.preventDefault();
            createContract.mutate(contractForm, {
              onSuccess: () => {
                setShowContractModal(false);
                setContractForm({ title: "" });
              },
            });
          }}
          className="space-y-4"
        >
          <Input
            label="제목"
            required
            value={contractForm.title}
            onChange={(e) =>
              setContractForm({ ...contractForm, title: e.target.value })
            }
            placeholder="예: 주식매매계약(SPA)"
          />
          <Select
            label="계약 유형"
            options={CONTRACT_TYPE_OPTIONS.filter((o) => o.value !== "")}
            value={contractForm.contract_type ?? "SPA"}
            onChange={(e) =>
              setContractForm({
                ...contractForm,
                contract_type: (e.target.value ||
                  undefined) as ContractCreate["contract_type"],
              })
            }
          />
          <Input
            label="상대방"
            value={contractForm.counterparty_name ?? ""}
            onChange={(e) =>
              setContractForm({
                ...contractForm,
                counterparty_name: e.target.value || undefined,
              })
            }
            placeholder="계약 상대방"
          />
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="효력일"
              type="date"
              value={contractForm.effective_date ?? ""}
              onChange={(e) =>
                setContractForm({
                  ...contractForm,
                  effective_date: e.target.value || undefined,
                })
              }
            />
            <Input
              label="만료일"
              type="date"
              value={contractForm.expiry_date ?? ""}
              onChange={(e) =>
                setContractForm({
                  ...contractForm,
                  expiry_date: e.target.value || undefined,
                })
              }
            />
          </div>
          <Input
            label="설명 / 비고"
            value={contractForm.description ?? ""}
            onChange={(e) =>
              setContractForm({
                ...contractForm,
                description: e.target.value || undefined,
              })
            }
          />
          <div className="flex justify-end gap-2 pt-2">
            <Button
              variant="ghost"
              type="button"
              onClick={() => setShowContractModal(false)}
            >
              취소
            </Button>
            <Button type="submit" loading={createContract.isPending}>
              등록
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}

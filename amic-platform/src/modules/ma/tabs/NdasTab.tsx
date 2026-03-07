import { useState } from "react";
import { Plus, Trash2, Shield, FileText } from "lucide-react";
import NdaVersionPanel from "@/modules/ma/components/NdaVersionPanel";
import {
  useNdas,
  useNdaSummary,
  useCreateNda,
  useUpdateNda,
  useDeleteNda,
} from "@/modules/ma/hooks/useNdas";
import { useBuyers } from "@/modules/ma/hooks/useTransactions";
import type { NDACreate, NdaStatus } from "@/modules/ma/types/nda";
import { NDA_TYPE_OPTIONS, NDA_STATUS_OPTIONS } from "@/modules/ma/constants";
import FileUploadZone from "@/modules/ma/components/FileUploadZone";

import {
  Badge,
  Button,
  Card,
  DataTable,
  EmptyState,
  INLINE_INPUT_CLS,
  Input,
  KpiCard,
  Modal,
  Select,
} from "@/components/ui";

interface NdasTabProps {
  txnId: string;
  canWrite: boolean;
}

export default function NdasTab({ txnId, canWrite }: NdasTabProps) {
  const { data: ndas } = useNdas(txnId);
  const { data: ndaSummary } = useNdaSummary(txnId);
  const { data: buyers } = useBuyers(txnId);
  const createNda = useCreateNda(txnId);
  const updateNda = useUpdateNda(txnId);
  const deleteNda = useDeleteNda(txnId);

  const [showNdaModal, setShowNdaModal] = useState(false);
  const [versionPanelNdaId, setVersionPanelNdaId] = useState<string | null>(
    null,
  );
  const [ndaForm, setNdaForm] = useState<NDACreate>({
    buyer_candidate_id: "",
    nda_type: "MUTUAL",
  });

  return (
    <div className="space-y-4">
      {/* NDA 요약 */}
      {ndaSummary && ndaSummary.total > 0 && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <KpiCard label="전체" value={String(ndaSummary.total)} />
          <KpiCard
            label="체결 완료"
            value={String(ndaSummary.signed_count)}
            variant="positive"
          />
          <KpiCard
            label="대기 중"
            value={String(ndaSummary.pending_count)}
            variant="default"
          />
          <KpiCard
            label="체결률"
            value={
              ndaSummary.total > 0
                ? `${Math.round((ndaSummary.signed_count / ndaSummary.total) * 100)}%`
                : "-"
            }
          />
        </div>
      )}
      <Card
        title="NDA 목록"
        headerBar
        padding="none"
        actions={
          canWrite ? (
            <Button
              icon={Plus}
              onClick={() => setShowNdaModal(true)}
              variant="ghost"
            >
              NDA 추가
            </Button>
          ) : undefined
        }
      >
        {!ndas?.length ? (
          <EmptyState
            icon={Shield}
            title="NDA 없음"
            description="매수 후보와의 NDA를 등록하세요."
            actionLabel={canWrite ? "NDA 추가" : undefined}
            onAction={canWrite ? () => setShowNdaModal(true) : undefined}
          />
        ) : (
          <DataTable
            columns={[
              {
                key: "buyer_candidate_id",
                header: "매수자",
                render: (r) => {
                  const buyer = buyers?.find(
                    (b) => b.id === r.buyer_candidate_id,
                  );
                  return (
                    buyer?.company_name ?? r.buyer_candidate_id.slice(0, 8)
                  );
                },
              },
              {
                key: "nda_type",
                header: "유형",
                render: (r) => (
                  <Badge variant="neutral">
                    {NDA_TYPE_OPTIONS.find((o) => o.value === r.nda_type)
                      ?.label ?? r.nda_type}
                  </Badge>
                ),
              },
              {
                key: "status",
                header: "상태",
                render: (r) => (
                  <Select
                    options={NDA_STATUS_OPTIONS}
                    value={r.status}
                    onChange={(e) =>
                      updateNda.mutate({
                        ndaId: r.id,
                        body: { status: e.target.value as NdaStatus },
                      })
                    }
                    className="!py-0.5 !px-1.5 !text-xs"
                    disabled={!canWrite}
                  />
                ),
              },
              {
                key: "sent_at",
                header: "발송일",
                render: (r) => (
                  <input
                    key={`${r.id}-sent-${r.sent_at}`}
                    type="date"
                    className={`${INLINE_INPUT_CLS} w-32`}
                    defaultValue={r.sent_at ?? ""}
                    onChange={(e) =>
                      updateNda.mutate({
                        ndaId: r.id,
                        body: { sent_at: e.target.value || undefined },
                      })
                    }
                    disabled={!canWrite}
                  />
                ),
              },
              {
                key: "signed_at",
                header: "체결일",
                render: (r) => (
                  <input
                    key={`${r.id}-signed-${r.signed_at}`}
                    type="date"
                    className={`${INLINE_INPUT_CLS} w-32`}
                    defaultValue={r.signed_at ?? ""}
                    onChange={(e) =>
                      updateNda.mutate({
                        ndaId: r.id,
                        body: { signed_at: e.target.value || undefined },
                      })
                    }
                    disabled={!canWrite}
                  />
                ),
              },
              {
                key: "expires_at",
                header: "만료일",
                render: (r) => (
                  <input
                    key={`${r.id}-expires-${r.expires_at}`}
                    type="date"
                    className={`${INLINE_INPUT_CLS} w-32`}
                    defaultValue={r.expires_at ?? ""}
                    onChange={(e) =>
                      updateNda.mutate({
                        ndaId: r.id,
                        body: { expires_at: e.target.value || undefined },
                      })
                    }
                    disabled={!canWrite}
                  />
                ),
              },
              {
                key: "markups",
                header: "버전",
                width: "80px",
                render: (r) => (
                  <Button
                    variant="ghost"
                    size="sm"
                    icon={FileText}
                    onClick={() => setVersionPanelNdaId(r.id)}
                    className="!px-2 !py-0.5 text-xs"
                  >
                    버전
                  </Button>
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
                        if (confirm("이 NDA를 삭제하시겠습니까?")) {
                          deleteNda.mutate(r.id);
                        }
                      }}
                    >
                      <Trash2 size={14} />
                    </button>
                  ) : null,
              },
            ]}
            data={ndas}
            keyField="id"
          />
        )}
        <FileUploadZone txnId={txnId} entityType="NDA" embedded />
      </Card>

      {/* NDA 추가 모달 */}
      <Modal
        open={showNdaModal}
        onClose={() => setShowNdaModal(false)}
        title="NDA 추가"
      >
        <form
          onSubmit={(e) => {
            e.preventDefault();
            createNda.mutate(ndaForm, {
              onSuccess: () => {
                setShowNdaModal(false);
                setNdaForm({ buyer_candidate_id: "", nda_type: "MUTUAL" });
              },
            });
          }}
          className="space-y-4"
        >
          <Select
            label="매수자"
            options={(buyers ?? []).map((b) => ({
              value: b.id,
              label: b.company_name,
            }))}
            value={ndaForm.buyer_candidate_id}
            onChange={(e) =>
              setNdaForm({ ...ndaForm, buyer_candidate_id: e.target.value })
            }
          />
          <Select
            label="NDA 유형"
            options={NDA_TYPE_OPTIONS}
            value={ndaForm.nda_type ?? "MUTUAL"}
            onChange={(e) =>
              setNdaForm({
                ...ndaForm,
                nda_type: e.target.value as NDACreate["nda_type"],
              })
            }
          />
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="발송일"
              type="date"
              value={ndaForm.sent_at ?? ""}
              onChange={(e) =>
                setNdaForm({ ...ndaForm, sent_at: e.target.value || undefined })
              }
            />
            <Input
              label="만료일"
              type="date"
              value={ndaForm.expires_at ?? ""}
              onChange={(e) =>
                setNdaForm({
                  ...ndaForm,
                  expires_at: e.target.value || undefined,
                })
              }
            />
          </div>
          <Input
            label="비고"
            value={ndaForm.notes ?? ""}
            onChange={(e) =>
              setNdaForm({ ...ndaForm, notes: e.target.value || undefined })
            }
          />
          <div className="flex justify-end gap-2 pt-2">
            <Button
              variant="ghost"
              type="button"
              onClick={() => {
                setShowNdaModal(false);
                setNdaForm({ buyer_candidate_id: "", nda_type: "MUTUAL" });
              }}
            >
              취소
            </Button>
            <Button type="submit" loading={createNda.isPending}>
              등록
            </Button>
          </div>
        </form>
      </Modal>

      {/* NDA 버전 관리 패널 */}
      {versionPanelNdaId && (
        <NdaVersionPanel
          open={!!versionPanelNdaId}
          onClose={() => setVersionPanelNdaId(null)}
          txnId={txnId}
          ndaId={versionPanelNdaId}
          ndaLabel={
            buyers?.find(
              (b) =>
                b.id ===
                ndas?.find((n) => n.id === versionPanelNdaId)
                  ?.buyer_candidate_id,
            )?.company_name ?? "NDA"
          }
          canWrite={canWrite}
        />
      )}
    </div>
  );
}

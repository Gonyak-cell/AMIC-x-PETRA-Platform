import { Plus, Trash2 } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/Button";
import type { BuyerCandidate } from "@/modules/ma/types/buyer";
import type { ConsortiumStatus } from "@/modules/ma/types/consortium";
import {
  CONSORTIUM_STATUS_LABELS,
  CONSORTIUM_STATUS_OPTIONS,
} from "@/modules/ma/constants";
import {
  useConsortiumMappings,
  useCreateConsortiumMapping,
  useUpdateConsortiumMapping,
  useDeleteConsortiumMapping,
} from "@/modules/ma/hooks/useConsortiumMappings";

const STATUS_COLORS: Record<string, string> = {
  TAPPING: "bg-amber-50 text-amber-700",
  CONFIRMED: "bg-emerald-50 text-emerald-700",
  DROPPED: "bg-gray-100 text-gray-500",
};

interface Props {
  txnId: string;
  buyers: BuyerCandidate[];
  canWrite: boolean;
}

export default function ConsortiumPanel({ txnId, buyers, canWrite }: Props) {
  const {
    data: mappings = [],
    isLoading,
    isError,
  } = useConsortiumMappings(txnId);
  const createMapping = useCreateConsortiumMapping(txnId);
  const updateMapping = useUpdateConsortiumMapping(txnId);
  const deleteMapping = useDeleteConsortiumMapping(txnId);

  const [showForm, setShowForm] = useState(false);
  const [leadId, setLeadId] = useState("");
  const [coId, setCoId] = useState("");
  const [equityPct, setEquityPct] = useState("");
  const [notes, setNotes] = useState("");

  const handleCreate = () => {
    if (!leadId || !coId) {
      toast.error("Lead와 Co-investor를 모두 선택하세요.");
      return;
    }
    if (leadId === coId) {
      toast.error("Lead와 Co-investor는 동일할 수 없습니다.");
      return;
    }
    createMapping.mutate(
      {
        lead_buyer_id: leadId,
        co_investor_buyer_id: coId,
        equity_share_pct: equityPct ? Number(equityPct) : undefined,
        notes: notes || undefined,
      },
      {
        onSuccess: () => {
          setShowForm(false);
          setLeadId("");
          setCoId("");
          setEquityPct("");
          setNotes("");
        },
      },
    );
  };

  return (
    <div className="rounded-lg border border-border bg-white">
      <div className="flex items-center justify-between border-b border-border px-4 py-3">
        <h3 className="text-sm font-semibold text-text-primary">
          컨소시엄 / 공동투자 매핑
        </h3>
        {canWrite && (
          <Button
            variant="secondary"
            size="sm"
            onClick={() => setShowForm((v) => !v)}
          >
            <Plus className="mr-1 h-3.5 w-3.5" />
            매핑 추가
          </Button>
        )}
      </div>

      {/* 생성 폼 */}
      {showForm && (
        <div className="border-b border-border bg-bg-cool px-4 py-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label
                htmlFor="consortium-lead"
                className="mb-1 block text-xs font-medium text-text-secondary"
              >
                Lead 매수자
              </label>
              <select
                id="consortium-lead"
                className="w-full rounded border border-border px-2 py-1.5 text-sm"
                value={leadId}
                onChange={(e) => setLeadId(e.target.value)}
              >
                <option value="">선택</option>
                {buyers.map((b) => (
                  <option key={b.id} value={b.id}>
                    {b.company_name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label
                htmlFor="consortium-co"
                className="mb-1 block text-xs font-medium text-text-secondary"
              >
                Co-investor
              </label>
              <select
                id="consortium-co"
                className="w-full rounded border border-border px-2 py-1.5 text-sm"
                value={coId}
                onChange={(e) => setCoId(e.target.value)}
              >
                <option value="">선택</option>
                {buyers.map((b) => (
                  <option key={b.id} value={b.id}>
                    {b.company_name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label
                htmlFor="consortium-equity"
                className="mb-1 block text-xs font-medium text-text-secondary"
              >
                지분율 (%)
              </label>
              <input
                id="consortium-equity"
                type="number"
                className="w-full rounded border border-border px-2 py-1.5 text-sm"
                value={equityPct}
                onChange={(e) => setEquityPct(e.target.value)}
                min={0}
                max={100}
                step={0.01}
                placeholder="0~100"
              />
            </div>
            <div>
              <label
                htmlFor="consortium-notes"
                className="mb-1 block text-xs font-medium text-text-secondary"
              >
                비고
              </label>
              <input
                id="consortium-notes"
                type="text"
                className="w-full rounded border border-border px-2 py-1.5 text-sm"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="선택사항"
              />
            </div>
          </div>
          <div className="mt-3 flex justify-end gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowForm(false)}
            >
              취소
            </Button>
            <Button
              variant="primary"
              size="sm"
              onClick={handleCreate}
              disabled={createMapping.isPending}
            >
              추가
            </Button>
          </div>
        </div>
      )}

      {/* 테이블 */}
      <div className="overflow-x-auto">
        {isLoading ? (
          <div className="flex h-24 items-center justify-center text-sm text-text-muted">
            불러오는 중...
          </div>
        ) : isError ? (
          <div className="flex h-24 items-center justify-center text-sm text-negative">
            컨소시엄 매핑을 불러오지 못했습니다.
          </div>
        ) : mappings.length === 0 ? (
          <div className="flex h-24 items-center justify-center text-sm text-text-muted">
            등록된 컨소시엄 매핑이 없습니다.
          </div>
        ) : (
          <table className="w-full text-sm" aria-label="컨소시엄 매핑 목록">
            <thead className="border-b border-border bg-bg-cool text-left text-xs text-text-muted">
              <tr>
                <th scope="col" className="px-4 py-2 font-medium">
                  Lead
                </th>
                <th scope="col" className="px-4 py-2 font-medium">
                  Co-investor
                </th>
                <th scope="col" className="px-4 py-2 font-medium">
                  상태
                </th>
                <th scope="col" className="px-4 py-2 font-medium">
                  지분율
                </th>
                <th scope="col" className="px-4 py-2 font-medium">
                  비고
                </th>
                {canWrite && (
                  <th scope="col" className="px-4 py-2 font-medium" />
                )}
              </tr>
            </thead>
            <tbody>
              {mappings.map((m) => (
                <tr
                  key={m.id}
                  className="border-b border-border/50 hover:bg-bg-cool/50"
                >
                  <td className="px-4 py-2 font-medium text-text-primary">
                    {m.lead_buyer_name}
                  </td>
                  <td className="px-4 py-2 text-text-secondary">
                    {m.co_investor_buyer_name}
                  </td>
                  <td className="px-4 py-2">
                    {canWrite ? (
                      <select
                        aria-label={`${m.lead_buyer_name} ↔ ${m.co_investor_buyer_name} 상태`}
                        className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_COLORS[m.status] ?? ""}`}
                        value={m.status}
                        disabled={updateMapping.isPending}
                        onChange={(e) =>
                          updateMapping.mutate({
                            mappingId: m.id,
                            body: {
                              status: e.target.value as ConsortiumStatus,
                            },
                          })
                        }
                      >
                        {CONSORTIUM_STATUS_OPTIONS.map((opt) => (
                          <option key={opt.value} value={opt.value}>
                            {opt.label}
                          </option>
                        ))}
                      </select>
                    ) : (
                      <span
                        className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_COLORS[m.status] ?? ""}`}
                      >
                        {CONSORTIUM_STATUS_LABELS[m.status] ?? m.status}
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-2 text-text-muted">
                    {m.equity_share_pct != null
                      ? `${m.equity_share_pct}%`
                      : "—"}
                  </td>
                  <td className="px-4 py-2 text-text-muted">
                    {m.notes ?? "—"}
                  </td>
                  {canWrite && (
                    <td className="px-4 py-2">
                      <button
                        type="button"
                        className="rounded p-1 text-text-muted hover:bg-bg-cool hover:text-negative"
                        title="삭제"
                        onClick={() => {
                          if (
                            window.confirm("컨소시엄 매핑을 삭제하시겠습니까?")
                          )
                            deleteMapping.mutate(m.id);
                        }}
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

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
  const { data: mappings = [], isLoading } = useConsortiumMappings(txnId);
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
    <div className="rounded-lg border border-slate-200 bg-white">
      <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
        <h3 className="text-sm font-semibold text-slate-700">
          컨소시엄 / 공동투자 매핑
        </h3>
        {canWrite && (
          <Button
            variant="outline"
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
        <div className="border-b border-slate-100 bg-slate-50 px-4 py-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-600">
                Lead 매수자
              </label>
              <select
                className="w-full rounded border border-slate-300 px-2 py-1.5 text-sm"
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
              <label className="mb-1 block text-xs font-medium text-slate-600">
                Co-investor
              </label>
              <select
                className="w-full rounded border border-slate-300 px-2 py-1.5 text-sm"
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
              <label className="mb-1 block text-xs font-medium text-slate-600">
                지분율 (%)
              </label>
              <input
                type="number"
                className="w-full rounded border border-slate-300 px-2 py-1.5 text-sm"
                value={equityPct}
                onChange={(e) => setEquityPct(e.target.value)}
                min={0}
                max={100}
                step={0.01}
                placeholder="0~100"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-600">
                비고
              </label>
              <input
                type="text"
                className="w-full rounded border border-slate-300 px-2 py-1.5 text-sm"
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
          <div className="flex h-24 items-center justify-center text-sm text-slate-400">
            불러오는 중...
          </div>
        ) : mappings.length === 0 ? (
          <div className="flex h-24 items-center justify-center text-sm text-slate-400">
            등록된 컨소시엄 매핑이 없습니다.
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead className="border-b border-slate-100 bg-slate-50 text-left text-xs text-slate-500">
              <tr>
                <th className="px-4 py-2 font-medium">Lead</th>
                <th className="px-4 py-2 font-medium">Co-investor</th>
                <th className="px-4 py-2 font-medium">상태</th>
                <th className="px-4 py-2 font-medium">지분율</th>
                <th className="px-4 py-2 font-medium">비고</th>
                {canWrite && <th className="px-4 py-2 font-medium" />}
              </tr>
            </thead>
            <tbody>
              {mappings.map((m) => (
                <tr
                  key={m.id}
                  className="border-b border-slate-50 hover:bg-slate-50"
                >
                  <td className="px-4 py-2 font-medium text-slate-700">
                    {m.lead_buyer_name}
                  </td>
                  <td className="px-4 py-2 text-slate-600">
                    {m.co_investor_buyer_name}
                  </td>
                  <td className="px-4 py-2">
                    {canWrite ? (
                      <select
                        className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_COLORS[m.status] ?? ""}`}
                        value={m.status}
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
                  <td className="px-4 py-2 text-slate-500">
                    {m.equity_share_pct != null
                      ? `${m.equity_share_pct}%`
                      : "—"}
                  </td>
                  <td className="px-4 py-2 text-slate-500">{m.notes ?? "—"}</td>
                  {canWrite && (
                    <td className="px-4 py-2">
                      <button
                        type="button"
                        className="rounded p-1 text-slate-400 hover:bg-slate-100 hover:text-negative"
                        title="삭제"
                        onClick={() => deleteMapping.mutate(m.id)}
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

import { useState, useRef } from "react";
import { Upload, Download, Trash2, Check } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { CONTRACT_TYPE_OPTIONS, MARKUP_TYPE_OPTIONS } from "@/modules/ma/constants";
import type { Contract } from "@/modules/ma/types/contract";
import type { ContractMarkup } from "@/modules/ma/types/contract_markup";

interface NegotiationVersionTimelineProps {
  txnId: string;
  contractId: string;
  contract: Contract;
  markups: ContractMarkup[];
  selectedVersions: number[];
  onSelectVersion: (versionNumber: number) => void;
  canWrite: boolean;
  onUpload: (formData: FormData) => void;
  onDelete: (markupId: string) => void;
  isUploading?: boolean;
}

function formatDate(iso: string) {
  const d = new Date(iso);
  return `${d.getFullYear()}.${String(d.getMonth() + 1).padStart(2, "0")}.${String(d.getDate()).padStart(2, "0")}`;
}

function buildVersionLabel(markup: ContractMarkup, contractType: string) {
  const typeLabel = CONTRACT_TYPE_OPTIONS.find((o) => o.value === contractType)?.label?.split(" ")[0] ?? contractType;
  const party = markup.source_party ?? "Unknown";
  const mType = markup.markup_type ?? `v${markup.version_number}`;
  const summary = markup.changes_summary ? ` : ${markup.changes_summary.slice(0, 60)}` : "";
  return `[${formatDate(markup.created_at)}] [${typeLabel}] [${party}] [${mType}]${summary}`;
}

export function NegotiationVersionTimeline({
  txnId,
  contractId,
  contract,
  markups,
  selectedVersions,
  onSelectVersion,
  canWrite,
  onUpload,
  onDelete,
  isUploading,
}: NegotiationVersionTimelineProps) {
  const [showUpload, setShowUpload] = useState(false);
  const [versionLabel, setVersionLabel] = useState("");
  const [sourceParty, setSourceParty] = useState("AMIC");
  const [markupType, setMarkupType] = useState("draft");
  const [changesSummary, setChangesSummary] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);

  const handleUpload = () => {
    const file = fileRef.current?.files?.[0];
    if (!file || !versionLabel.trim()) return;
    const fd = new FormData();
    fd.append("file", file);
    fd.append("version_label", versionLabel);
    fd.append("source_party", sourceParty);
    fd.append("markup_type", markupType);
    if (changesSummary.trim()) fd.append("changes_summary", changesSummary);
    onUpload(fd);
    setVersionLabel("");
    setChangesSummary("");
    setShowUpload(false);
  };

  const downloadUrl = (markupId: string) =>
    `/api/v1/transactions/${txnId}/contracts/${contractId}/markups/${markupId}/download`;

  return (
    <div className="flex h-full flex-col">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-heading font-semibold text-text-dark">버전 히스토리</h3>
        {canWrite && (
          <Button size="sm" variant="secondary" onClick={() => setShowUpload(!showUpload)}>
            <Upload className="mr-1 h-3.5 w-3.5" /> 업로드
          </Button>
        )}
      </div>

      {/* 업로드 폼 */}
      {showUpload && canWrite && (
        <div className="mb-3 space-y-2 rounded-lg border border-blue-200 bg-blue-50 p-3">
          <input
            type="text"
            placeholder="버전 라벨 (예: v1 - 매도측 초안)"
            value={versionLabel}
            onChange={(e) => setVersionLabel(e.target.value)}
            className="w-full rounded border px-2 py-1 text-xs"
          />
          <div className="grid grid-cols-2 gap-2">
            <select
              value={sourceParty}
              onChange={(e) => setSourceParty(e.target.value)}
              className="rounded border px-2 py-1 text-xs"
            >
              <option value="AMIC">AMIC</option>
              <option value="Counterparty">Counterparty</option>
              <option value="Legal">Legal</option>
            </select>
            <select
              value={markupType}
              onChange={(e) => setMarkupType(e.target.value)}
              className="rounded border px-2 py-1 text-xs"
            >
              {MARKUP_TYPE_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
          </div>
          <textarea
            placeholder="변경 요약 (선택)"
            value={changesSummary}
            onChange={(e) => setChangesSummary(e.target.value)}
            className="w-full rounded border px-2 py-1 text-xs"
            rows={2}
          />
          <input ref={fileRef} type="file" className="w-full text-xs" />
          <Button size="sm" onClick={handleUpload} disabled={isUploading || !versionLabel.trim()}>
            {isUploading ? "업로드 중..." : "마크업 등록"}
          </Button>
        </div>
      )}

      {/* 타임라인 */}
      <div className="flex-1 space-y-0 overflow-y-auto">
        {markups.length === 0 ? (
          <p className="py-8 text-center text-xs text-text-muted">등록된 마크업이 없습니다.</p>
        ) : (
          markups.map((m, i) => {
            const isSelected = selectedVersions.includes(m.version_number);
            return (
              <div key={m.id} className="relative flex gap-3 pb-4">
                {/* 수직선 */}
                <div className="flex flex-col items-center">
                  <button
                    onClick={() => onSelectVersion(m.version_number)}
                    className={`z-10 flex h-7 w-7 shrink-0 items-center justify-center rounded-full border-2 text-[10px] font-bold transition-colors ${
                      isSelected
                        ? "border-primary-600 bg-primary-600 text-white"
                        : "border-gray-300 bg-white text-text-secondary hover:border-primary-400"
                    }`}
                  >
                    {isSelected ? <Check className="h-3.5 w-3.5" /> : `v${m.version_number}`}
                  </button>
                  {i < markups.length - 1 && <div className="mt-1 h-full w-px bg-gray-200" />}
                </div>

                {/* 카드 */}
                <div
                  className={`flex-1 rounded-lg border p-2.5 text-xs transition-colors cursor-pointer ${
                    isSelected ? "border-primary-300 bg-primary-50" : "border-gray-border bg-white hover:bg-gray-50"
                  }`}
                  onClick={() => onSelectVersion(m.version_number)}
                >
                  <p className="font-medium text-text-dark leading-snug">
                    {buildVersionLabel(m, contract.contract_type)}
                  </p>
                  {m.key_changes && m.key_changes.length > 0 && (
                    <ul className="mt-1 space-y-0.5 text-text-secondary">
                      {m.key_changes.slice(0, 3).map((kc, ki) => (
                        <li key={ki} className="flex items-start gap-1">
                          <span className="mt-0.5 inline-block h-1.5 w-1.5 shrink-0 rounded-full bg-primary-400" />
                          {kc}
                        </li>
                      ))}
                      {m.key_changes.length > 3 && (
                        <li className="text-text-muted">+{m.key_changes.length - 3}건 더</li>
                      )}
                    </ul>
                  )}
                  <div className="mt-1.5 flex items-center gap-2">
                    {m.source_party && <Badge variant="neutral">{m.source_party}</Badge>}
                    {m.file_name && (
                      <a
                        href={downloadUrl(m.id)}
                        onClick={(e) => e.stopPropagation()}
                        className="flex items-center gap-0.5 text-primary-600 hover:underline"
                      >
                        <Download className="h-3 w-3" /> {m.file_name}
                      </a>
                    )}
                    {canWrite && (
                      <button
                        onClick={(e) => { e.stopPropagation(); onDelete(m.id); }}
                        className="ml-auto text-text-muted hover:text-red-500"
                      >
                        <Trash2 className="h-3 w-3" />
                      </button>
                    )}
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>

      {selectedVersions.length > 0 && (
        <div className="mt-2 rounded bg-blue-50 px-2 py-1 text-[10px] text-blue-700">
          {selectedVersions.length === 1
            ? `v${selectedVersions[0]} 선택됨 — 하나 더 선택하면 비교합니다`
            : `v${selectedVersions[0]} vs v${selectedVersions[1]} 비교 중`}
        </div>
      )}
    </div>
  );
}

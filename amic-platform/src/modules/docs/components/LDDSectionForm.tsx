import { useState } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";
import type { LDDItem, LDDIssueLevel, LDDItemStatus, LDDSection } from "@/modules/docs/types/ldd_report";
import {
  LDD_ITEM_STATUS_LABELS,
  LDD_ITEM_STATUS_COLORS,
  LDD_ISSUE_LEVEL_LABELS,
  LDD_ISSUE_LEVEL_COLORS,
} from "@/modules/docs/types/ldd_report";

interface LDDSectionFormProps {
  sections: LDDSection[];
  onChange: (sections: LDDSection[]) => void;
  readOnly?: boolean;
}

const ITEM_STATUSES: LDDItemStatus[] = ["OK", "ISSUE", "NA", "PENDING"];
const ISSUE_LEVELS: LDDIssueLevel[]  = ["CRITICAL", "HIGH", "MEDIUM", "LOW"];

export function LDDSectionForm({ sections, onChange, readOnly = false }: LDDSectionFormProps) {
  const [openSections, setOpenSections] = useState<Set<number>>(() => new Set([0]));

  const toggleSection = (idx: number) => {
    setOpenSections((prev) => {
      const next = new Set(prev);
      if (next.has(idx)) next.delete(idx);
      else next.add(idx);
      return next;
    });
  };

  const updateItem = (sIdx: number, iIdx: number, patch: Partial<LDDItem>) => {
    const next = sections.map((sec, si) => {
      if (si !== sIdx) return sec;
      return {
        ...sec,
        items: sec.items.map((item, ii) => {
          if (ii !== iIdx) return item;
          const updated = { ...item, ...patch };
          // issue_level 클리어: ISSUE가 아닌 경우
          if (patch.status && patch.status !== "ISSUE") {
            updated.issue_level = null;
            updated.risk_color  = "";
          }
          // risk_color 자동 계산
          if (updated.status === "ISSUE" && updated.issue_level) {
            const colorMap: Record<LDDIssueLevel, string> = {
              CRITICAL: "RED",
              HIGH:     "AMBER",
              MEDIUM:   "AMBER",
              LOW:      "GREEN",
            };
            updated.risk_color = colorMap[updated.issue_level as LDDIssueLevel] ?? "";
          }
          return updated;
        }),
      };
    });
    onChange(next);
  };

  // 섹션별 이슈 카운트
  const getIssueCounts = (sec: LDDSection) => ({
    total:   sec.items.length,
    issue:   sec.items.filter((i) => i.status === "ISSUE").length,
    pending: sec.items.filter((i) => i.status === "PENDING").length,
  });

  return (
    <div className="space-y-3">
      {sections.map((section, sIdx) => {
        const counts   = getIssueCounts(section);
        const isOpen   = openSections.has(sIdx);

        return (
          <div key={section.section_type} className="border border-border rounded-lg overflow-hidden">
            {/* 섹션 헤더 */}
            <button
              type="button"
              onClick={() => toggleSection(sIdx)}
              className="w-full flex items-center justify-between px-4 py-3 bg-muted/40 hover:bg-muted/60 transition-colors text-left"
            >
              <div className="flex items-center gap-3">
                <span className="font-medium text-sm">{section.title}</span>
                <div className="flex gap-1.5">
                  {counts.issue > 0 && (
                    <span className="text-xs px-2 py-0.5 rounded-full bg-negative-light text-negative font-medium">
                      이슈 {counts.issue}
                    </span>
                  )}
                  {counts.pending > 0 && (
                    <span className="text-xs px-2 py-0.5 rounded-full bg-yellow-100 text-yellow-700">
                      미검토 {counts.pending}
                    </span>
                  )}
                  {counts.issue === 0 && counts.pending === 0 && (
                    <span className="text-xs px-2 py-0.5 rounded-full bg-positive-light text-positive">
                      이상없음
                    </span>
                  )}
                </div>
              </div>
              {isOpen ? (
                <ChevronUp className="h-4 w-4 text-muted-foreground" />
              ) : (
                <ChevronDown className="h-4 w-4 text-muted-foreground" />
              )}
            </button>

            {/* 항목 목록 */}
            {isOpen && (
              <div className="divide-y divide-border">
                {section.items.map((item, iIdx) => (
                  <div key={item.item_id} className="px-4 py-3 space-y-2">
                    {/* 항목명 + 상태 선택 */}
                    <div className="flex items-start gap-3">
                      <span className="text-xs text-muted-foreground font-mono w-20 shrink-0 pt-0.5">
                        {item.item_id}
                      </span>
                      <div className="flex-1 space-y-2">
                        <p className="text-sm font-medium">{item.name}</p>

                        {/* 상태 선택 버튼 */}
                        <div className="flex flex-wrap gap-1.5">
                          {ITEM_STATUSES.map((s) => (
                            <button
                              key={s}
                              type="button"
                              disabled={readOnly}
                              onClick={() => !readOnly && updateItem(sIdx, iIdx, { status: s })}
                              className={`text-xs px-2.5 py-1 rounded-full border transition-all ${
                                item.status === s
                                  ? LDD_ITEM_STATUS_COLORS[s] + " border-transparent font-semibold"
                                  : "border-border text-muted-foreground hover:border-foreground/40"
                              } ${readOnly ? "cursor-default" : "cursor-pointer"}`}
                            >
                              {LDD_ITEM_STATUS_LABELS[s]}
                            </button>
                          ))}
                        </div>

                        {/* ISSUE인 경우: 이슈레벨 선택 */}
                        {item.status === "ISSUE" && (
                          <div className="space-y-2 pl-1 border-l-2 border-negative/30">
                            <div>
                              <p className="text-xs text-muted-foreground mb-1">이슈 등급 *</p>
                              <div className="flex flex-wrap gap-1.5">
                                {ISSUE_LEVELS.map((level) => (
                                  <button
                                    key={level}
                                    type="button"
                                    disabled={readOnly}
                                    onClick={() =>
                                      !readOnly && updateItem(sIdx, iIdx, { issue_level: level })
                                    }
                                    className={`text-xs px-2.5 py-1 rounded-full transition-all ${
                                      item.issue_level === level
                                        ? LDD_ISSUE_LEVEL_COLORS[level] + " font-semibold"
                                        : "bg-muted text-muted-foreground hover:bg-muted/80"
                                    } ${readOnly ? "cursor-default" : "cursor-pointer"}`}
                                  >
                                    {LDD_ISSUE_LEVEL_LABELS[level]}
                                  </button>
                                ))}
                              </div>
                            </div>

                            {/* 발견사항 */}
                            <div>
                              <p className="text-xs text-muted-foreground mb-1">발견사항</p>
                              <textarea
                                rows={2}
                                disabled={readOnly}
                                value={item.description}
                                onChange={(e) =>
                                  updateItem(sIdx, iIdx, { description: e.target.value })
                                }
                                placeholder="발견된 사실관계 및 관련 문서를 기재하세요."
                                className="w-full text-sm border border-border rounded-md px-3 py-1.5 resize-none focus:outline-none focus:ring-2 focus:ring-ring disabled:bg-muted"
                              />
                            </div>

                            {/* 거래영향 */}
                            <div>
                              <p className="text-xs text-muted-foreground mb-1">거래영향</p>
                              <textarea
                                rows={2}
                                disabled={readOnly}
                                value={item.deal_impact}
                                onChange={(e) =>
                                  updateItem(sIdx, iIdx, { deal_impact: e.target.value })
                                }
                                placeholder="거래 가격·구조·일정에 미치는 영향을 기재하세요."
                                className="w-full text-sm border border-border rounded-md px-3 py-1.5 resize-none focus:outline-none focus:ring-2 focus:ring-ring disabled:bg-muted"
                              />
                            </div>

                            {/* 권고사항 */}
                            <div>
                              <p className="text-xs text-muted-foreground mb-1">권고사항</p>
                              <textarea
                                rows={2}
                                disabled={readOnly}
                                value={item.recommendation}
                                onChange={(e) =>
                                  updateItem(sIdx, iIdx, { recommendation: e.target.value })
                                }
                                placeholder="계약 반영, 추가 실사, 시정 요구 등 권고사항을 기재하세요."
                                className="w-full text-sm border border-border rounded-md px-3 py-1.5 resize-none focus:outline-none focus:ring-2 focus:ring-ring disabled:bg-muted"
                              />
                            </div>

                            {/* RFI */}
                            <div className="flex items-center gap-3">
                              <label className="flex items-center gap-2 cursor-pointer">
                                <input
                                  type="checkbox"
                                  disabled={readOnly}
                                  checked={item.rfi_required}
                                  onChange={(e) =>
                                    updateItem(sIdx, iIdx, { rfi_required: e.target.checked })
                                  }
                                  className="h-4 w-4 rounded border-border"
                                />
                                <span className="text-xs text-muted-foreground">RFI 요청</span>
                              </label>
                              {item.rfi_required && (
                                <input
                                  type="text"
                                  disabled={readOnly}
                                  value={item.rfi_number}
                                  onChange={(e) =>
                                    updateItem(sIdx, iIdx, { rfi_number: e.target.value })
                                  }
                                  placeholder="예: CORP-001"
                                  className="text-xs border border-border rounded-md px-2.5 py-1 w-36 focus:outline-none focus:ring-2 focus:ring-ring disabled:bg-muted font-mono"
                                />
                              )}
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

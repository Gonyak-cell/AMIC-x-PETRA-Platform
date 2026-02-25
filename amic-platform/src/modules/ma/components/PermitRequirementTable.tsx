import { FileText, Clock, ChevronDown, ChevronRight } from "lucide-react";
import { useState } from "react";
import { Badge, InlineSelect } from "@/components/ui";
import type { BadgeVariant } from "@/components/ui";
import type {
  PermitRequirement,
  PermitRequirementStatus,
} from "@/modules/ma/types/permit";
import {
  PERMIT_FILING_TYPE_OPTIONS,
  PERMIT_TIMING_TYPE_OPTIONS,
  PERMIT_REQUIREMENT_STATUS_OPTIONS,
} from "@/modules/ma/constants";

interface PermitRequirementTableProps {
  requirements: PermitRequirement[];
  onUpdateStatus: (
    reqId: string,
    body: { status: PermitRequirementStatus; notes?: string },
  ) => void;
  disabled?: boolean;
}

function filingTypeBadge(type: string): {
  variant: BadgeVariant;
  label: string;
} {
  const opt = PERMIT_FILING_TYPE_OPTIONS.find((o) => o.value === type);
  const label = opt?.label ?? type;
  switch (type) {
    case "CHANGE_NOTIFICATION":
      return { variant: "info", label };
    case "CHANGE_APPROVAL":
      return { variant: "warning", label };
    case "NEW_REGISTRATION":
      return { variant: "error", label };
    case "RENEWAL":
      return { variant: "neutral", label };
    default:
      return { variant: "neutral", label };
  }
}

function timingBadge(type: string): { variant: BadgeVariant; label: string } {
  const opt = PERMIT_TIMING_TYPE_OPTIONS.find((o) => o.value === type);
  const label = opt?.label ?? type;
  switch (type) {
    case "PRE_FILING":
      return { variant: "error", label };
    case "POST_FILING":
      return { variant: "success", label };
    case "BOTH":
      return { variant: "warning", label };
    default:
      return { variant: "neutral", label };
  }
}

function dDayLabel(deadline: string | null): string | null {
  if (!deadline) return null;
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const dl = new Date(deadline);
  dl.setHours(0, 0, 0, 0);
  const diff = Math.ceil((dl.getTime() - today.getTime()) / 86400000);
  if (diff < 0) return `D+${Math.abs(diff)}`;
  if (diff === 0) return "D-Day";
  return `D-${diff}`;
}

function dDayColor(deadline: string | null): string {
  if (!deadline) return "";
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const dl = new Date(deadline);
  dl.setHours(0, 0, 0, 0);
  const diff = Math.ceil((dl.getTime() - today.getTime()) / 86400000);
  if (diff < 0) return "text-negative font-semibold";
  if (diff <= 7) return "text-amber-600 font-semibold";
  if (diff <= 30) return "text-text-body";
  return "text-text-muted";
}

export default function PermitRequirementTable({
  requirements,
  onUpdateStatus,
  disabled = false,
}: PermitRequirementTableProps) {
  const [expandedId, setExpandedId] = useState<string | null>(null);

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-border text-left text-xs text-text-muted uppercase tracking-wide">
            <th className="w-8 py-2 px-1" />
            <th className="py-2 px-2">인허가</th>
            <th className="py-2 px-2 w-[100px]">유형</th>
            <th className="py-2 px-2 w-[80px]">시기</th>
            <th className="py-2 px-2 w-[120px]">기한</th>
            <th className="py-2 px-2 w-[60px]">출처</th>
            <th className="py-2 px-2 w-[130px]">상태</th>
          </tr>
        </thead>
        <tbody>
          {requirements.map((item) => {
            const fBadge = filingTypeBadge(item.filing_type);
            const tBadge = timingBadge(item.timing_type);
            const dDay = dDayLabel(item.calculated_deadline);
            const dColor = dDayColor(item.calculated_deadline);
            const hasDetails =
              (item.required_documents && item.required_documents.length > 0) ||
              item.legal_basis ||
              item.notes;
            const isExpanded = expandedId === item.id;

            return (
              <tr key={item.id} className="border-b border-gray-border/50 hover:bg-bg-cool/30 transition-colors">
                {/* Expand */}
                <td className="py-2 px-1">
                  {hasDetails ? (
                    <button
                      onClick={() =>
                        setExpandedId(isExpanded ? null : item.id)
                      }
                      aria-expanded={isExpanded}
                      aria-label={`${item.permit_name} 상세 정보 ${isExpanded ? "접기" : "펼치기"}`}
                      className="p-0.5 text-text-muted hover:text-text-body rounded transition-colors"
                    >
                      {isExpanded ? (
                        <ChevronDown size={14} />
                      ) : (
                        <ChevronRight size={14} />
                      )}
                    </button>
                  ) : null}
                </td>

                {/* Name + regulatory body + expanded detail */}
                <td className="py-2 px-2" colSpan={isExpanded ? 1 : 1}>
                  <div>
                    <span className="font-medium block truncate">
                      {item.permit_name}
                    </span>
                    <span className="text-xs text-text-muted">
                      {item.regulatory_body}
                    </span>
                  </div>
                  {/* Inline expanded detail */}
                  {isExpanded && (
                    <div className="mt-2 pl-1 py-2 border-t border-gray-border/30 space-y-1.5">
                      {item.legal_basis && (
                        <div className="text-xs">
                          <span className="font-medium text-text-body">
                            근거법령:
                          </span>{" "}
                          <span className="text-text-muted">
                            {item.legal_basis}
                          </span>
                        </div>
                      )}
                      {item.pre_filing_deadline_days != null && (
                        <div className="text-xs text-text-muted">
                          사전: 거래 {item.pre_filing_deadline_days}일 전
                        </div>
                      )}
                      {item.post_filing_deadline_days != null && (
                        <div className="text-xs text-text-muted">
                          사후: 거래 후 {item.post_filing_deadline_days}일 이내
                        </div>
                      )}
                      {item.required_documents &&
                        item.required_documents.length > 0 && (
                          <div>
                            <span className="font-medium text-text-body text-xs flex items-center gap-1">
                              <FileText size={11} />
                              필요 서류
                            </span>
                            <ul className="mt-0.5 ml-4 list-disc text-text-muted text-xs space-y-0.5">
                              {item.required_documents.map((doc, i) => (
                                <li key={i}>
                                  {doc.name}
                                  {doc.description && (
                                    <span className="text-text-muted/70">
                                      {" "}
                                      — {doc.description}
                                    </span>
                                  )}
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}
                      {item.notes && (
                        <div className="text-xs text-text-muted italic">
                          {item.notes}
                        </div>
                      )}
                    </div>
                  )}
                </td>

                {/* Filing type */}
                <td className="py-2 px-2 align-top">
                  <Badge variant={fBadge.variant}>{fBadge.label}</Badge>
                </td>

                {/* Timing */}
                <td className="py-2 px-2 align-top">
                  <Badge variant={tBadge.variant}>{tBadge.label}</Badge>
                </td>

                {/* Deadline */}
                <td className="py-2 px-2 align-top">
                  <div className="text-xs">
                    {item.calculated_deadline ? (
                      <>
                        <div className="text-text-body">
                          {item.calculated_deadline}
                        </div>
                        {dDay && (
                          <div className={dColor}>
                            <Clock size={10} className="inline mr-0.5" />
                            {dDay}
                          </div>
                        )}
                      </>
                    ) : (
                      <span className="text-text-muted">—</span>
                    )}
                  </div>
                </td>

                {/* Source */}
                <td className="py-2 px-2 align-top">
                  {item.source === "KB" ? (
                    <span
                      className="text-xs text-emerald-600 font-medium"
                      title="지식베이스"
                    >
                      KB
                    </span>
                  ) : (
                    <span className="text-xs text-text-muted">
                      {item.source}
                    </span>
                  )}
                </td>

                {/* Status */}
                <td className="py-2 px-2 align-top">
                  <InlineSelect
                    options={PERMIT_REQUIREMENT_STATUS_OPTIONS}
                    value={item.status}
                    onChange={(v) =>
                      onUpdateStatus(item.id, {
                        status: v as PermitRequirementStatus,
                      })
                    }
                    disabled={disabled}
                  />
                </td>
              </tr>
            );
          })}
          {requirements.length === 0 && (
            <tr>
              <td
                colSpan={7}
                className="py-8 text-center text-sm text-text-muted"
              >
                인허가 분석 결과가 없습니다.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

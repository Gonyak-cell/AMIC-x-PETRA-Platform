import type { SelectOption } from "@/components/ui";
import type {
  PermitFilingType,
  PermitRequirementStatus,
  PermitTimingType,
} from "@/modules/ma/types/permit";

type PermitOption<T extends string> = SelectOption & { value: T };

export const PERMIT_FILING_TYPE_OPTIONS: PermitOption<PermitFilingType>[] = [
  { value: "CHANGE_NOTIFICATION", label: "변경신고" },
  { value: "CHANGE_APPROVAL", label: "변경인가" },
  { value: "NEW_REGISTRATION", label: "신규등록" },
  { value: "RENEWAL", label: "갱신" },
];

export const PERMIT_TIMING_TYPE_OPTIONS: PermitOption<PermitTimingType>[] = [
  { value: "PRE_FILING", label: "사전" },
  { value: "POST_FILING", label: "사후" },
  { value: "BOTH", label: "사전/사후" },
];

export const PERMIT_REQUIREMENT_STATUS_OPTIONS: PermitOption<PermitRequirementStatus>[] =
  [
    { value: "IDENTIFIED", label: "식별" },
    { value: "DOCUMENTS_PREPARING", label: "서류 준비중" },
    { value: "FILED", label: "제출 완료" },
    { value: "APPROVED", label: "승인 완료" },
    { value: "NOT_APPLICABLE", label: "해당 없음" },
  ];

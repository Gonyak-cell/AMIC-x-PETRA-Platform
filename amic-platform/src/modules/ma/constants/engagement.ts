import type { SelectOption } from "@/components/ui";

// ── Engagement Type ───────────────────────────────────
export const ENGAGEMENT_TYPE_OPTIONS: SelectOption[] = [
  { value: "EXCLUSIVE", label: "전속 (Exclusive)" },
  { value: "NON_EXCLUSIVE", label: "비전속 (Non-Exclusive)" },
  { value: "CO_ADVISORY", label: "공동자문 (Co-Advisory)" },
];

// ── Working Group Role ────────────────────────────────
export const WORKING_GROUP_ROLE_OPTIONS: SelectOption[] = [
  { value: "LEAD_ADVISOR", label: "리드 어드바이저" },
  { value: "LEGAL_COUNSEL", label: "법률 자문" },
  { value: "ACCOUNTING_ADVISOR", label: "회계 자문" },
  { value: "TAX_ADVISOR", label: "세무 자문" },
  { value: "INDUSTRY_EXPERT", label: "산업 전문가" },
  { value: "VALUATION_ADVISOR", label: "밸류에이션 자문" },
  { value: "OTHER", label: "기타" },
];

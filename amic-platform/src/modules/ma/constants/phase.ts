import type { TransactionPhase } from "../types/transaction";

// ── 8단계 Phase 설정 (MOU_SIGNED -> 마일스톤으로 전환) ──────
export interface PhaseConfigItem {
  phase: TransactionPhase;
  label: string;
  description: string;
  icon: string;
  order: number;
}

export const PHASE_CONFIG: PhaseConfigItem[] = [
  {
    phase: "ENGAGEMENT",
    label: "수임",
    description: "클라이언트 수임계약 체결 및 이해충돌 검토",
    icon: "Handshake",
    order: 1,
  },
  {
    phase: "PREPARATION",
    label: "준비",
    description: "대상기업 분석, CIM 작성, 바이어 롱리스트 구성",
    icon: "ClipboardList",
    order: 2,
  },
  {
    phase: "MARKETING",
    label: "마케팅",
    description: "잠재 매수자 접촉, NDA 체결, CIM 배포",
    icon: "Megaphone",
    order: 3,
  },
  {
    phase: "BIDDING",
    label: "입찰",
    description: "IOI/LOI 접수, 매수자 입찰 결과 추적",
    icon: "Gavel",
    order: 4,
  },
  {
    phase: "MAIN_DUE_DILIGENCE",
    label: "본실사",
    description: "FDD/LDD/TDD 본실사 진행",
    icon: "Search",
    order: 5,
  },
  {
    phase: "NEGOTIATION",
    label: "협상",
    description: "최종 후보 선정, SPA 협상, 가격 조정",
    icon: "Scale",
    order: 6,
  },
  {
    phase: "CLOSING",
    label: "Closing",
    description: "계약 체결(Signing), 선행조건 충족, 거래 완결",
    icon: "CheckCircle",
    order: 7,
  },
  {
    phase: "POST_CLOSING",
    label: "Post-Closing",
    description: "가격조정 정산, PMI 지원, 프로젝트 종결",
    icon: "Archive",
    order: 8,
  },
];

// ── Phase <-> Tab 매핑 ────────────────────────────────
export const PHASE_TAB_MAP: Record<TransactionPhase, string> = {
  ENGAGEMENT: "overview",
  PREPARATION: "marketing-materials",
  MARKETING: "buyers",
  BIDDING: "bids",
  MOU_SIGNED: "contracts", // deprecated -- 호환성 유지
  MAIN_DUE_DILIGENCE: "dd-checklist",
  NEGOTIATION: "contracts",
  CLOSING: "closing",
  POST_CLOSING: "pmi",
};

// ── 단계별 표시 탭 (전 단계 공통 + 단계별) ────────────
export const ALWAYS_VISIBLE_TABS = ["overview"] as const;

export const PHASE_VISIBLE_TABS: Record<TransactionPhase, readonly string[]> = {
  ENGAGEMENT: [...ALWAYS_VISIBLE_TABS, "engagement", "rfi"],
  PREPARATION: [
    ...ALWAYS_VISIBLE_TABS,
    "marketing-materials",
    "models",
    "ndas",
    "vdr",
  ],
  MARKETING: [...ALWAYS_VISIBLE_TABS, "buyers", "marketing-logs", "vdr"],
  BIDDING: [...ALWAYS_VISIBLE_TABS, "bids", "buyers", "vdr"],
  MOU_SIGNED: [...ALWAYS_VISIBLE_TABS, "contracts", "vdr"], // deprecated -- 호환성 유지
  MAIN_DUE_DILIGENCE: [...ALWAYS_VISIBLE_TABS, "dd-checklist", "rfi", "vdr"],
  NEGOTIATION: [...ALWAYS_VISIBLE_TABS, "contracts", "negotiation-logs", "vdr"],
  CLOSING: [...ALWAYS_VISIBLE_TABS, "closing", "vdr"],
  POST_CLOSING: [...ALWAYS_VISIBLE_TABS, "pmi", "earnout", "vdr"],
};

// ── 파이프라인 마일스톤 ─────────────────────────────
export interface UploadableMilestone {
  afterPhase: TransactionPhase;
  label: string;
  uploadable: true;
  documentLabel: string;
  milestoneKey: string;
}

interface DisplayOnlyMilestone {
  afterPhase: TransactionPhase;
  label: string;
  uploadable?: false;
  documentLabel?: undefined;
  milestoneKey?: undefined;
}

export type PhaseMilestone = UploadableMilestone | DisplayOnlyMilestone;

export const PHASE_MILESTONES: PhaseMilestone[] = [
  {
    afterPhase: "BIDDING",
    label: "MOU Signed",
    uploadable: true,
    documentLabel: "Executed MOU",
    milestoneKey: "MOU_SIGNED",
  },
  {
    afterPhase: "NEGOTIATION",
    label: "Signing",
    uploadable: true,
    documentLabel: "Executed SPA",
    milestoneKey: "SIGNING",
  },
  { afterPhase: "CLOSING", label: "Closing" },
];

export interface OnboardingStep {
  id: string;
  targetSelector: string;
  title: string;
  description: string;
  placement: "top" | "bottom" | "left" | "right";
}

export const CLIENT_OVERVIEW_STEPS: OnboardingStep[] = [
  {
    id: "pipeline-flow",
    targetSelector: "[data-onboarding='pipeline-flow']",
    title: "거래 진행 단계",
    description:
      "현재 거래가 어느 단계에 있는지 한눈에 확인할 수 있습니다. 각 단계를 클릭하면 해당 시점의 업무 현황으로 이동합니다.",
    placement: "bottom",
  },
  {
    id: "deal-info",
    targetSelector: "[data-onboarding='deal-info']",
    title: "거래 정보",
    description:
      "거래의 기본 정보를 확인할 수 있습니다. 거래명, 대상기업, 딜 구조, 예상 금액 등이 표시됩니다.",
    placement: "bottom",
  },
  {
    id: "company-info",
    targetSelector: "[data-onboarding='company-info']",
    title: "회사 정보",
    description:
      "대상 기업의 법인등기부, 사업자등록증, 임원 정보를 확인합니다.",
    placement: "bottom",
  },
  {
    id: "workspace-tabs",
    targetSelector: "[data-onboarding='workspace-tabs']",
    title: "업무 영역 탭",
    description:
      "상단 탭을 통해 매수자 현황, NDA, 마케팅 자료, 입찰 등 각 업무 영역을 조회할 수 있습니다.",
    placement: "bottom",
  },
];

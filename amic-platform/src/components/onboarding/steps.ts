export interface OnboardingStep {
  id: string;
  targetSelector: string;
  title: string;
  description: string;
  placement: "top" | "bottom" | "left" | "right";
}

export const CLIENT_OVERVIEW_STEPS: OnboardingStep[] = [
  {
    id: "project-summary",
    targetSelector: "[data-onboarding='project-summary']",
    title: "프로젝트 요약",
    description: "현재 거래의 기본 정보와 담당 팀을 확인할 수 있습니다.",
    placement: "bottom",
  },
  {
    id: "doc-distribution",
    targetSelector: "[data-onboarding='doc-distribution']",
    title: "문서 배포 현황",
    description: "TM, DM, IM 등 마케팅 문서의 배포 상태를 확인합니다.",
    placement: "bottom",
  },
  {
    id: "buyer-status",
    targetSelector: "[data-onboarding='buyer-status']",
    title: "매수자 진행상황",
    description:
      "각 매수자의 반응도, 조건 일치도, 다음 미팅 일정을 한눈에 봅니다.",
    placement: "top",
  },
  {
    id: "upcoming-meetings",
    targetSelector: "[data-onboarding='upcoming-meetings']",
    title: "예정된 미팅",
    description: "다음 미팅의 일시, 장소, 참석자 정보를 확인합니다.",
    placement: "top",
  },
  {
    id: "recent-activity",
    targetSelector: "[data-onboarding='recent-activity']",
    title: "최근 활동",
    description: "미팅 완료, 문서 배포 등 최근 진행 사항이 여기에 표시됩니다.",
    placement: "top",
  },
];

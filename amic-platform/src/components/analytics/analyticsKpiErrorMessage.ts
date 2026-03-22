import type { AnalyticsKpiErrorState } from "@/hooks/useAnalytics";

export function getModuleErrorMessage(
  moduleLabel: string,
  error: AnalyticsKpiErrorState | null | undefined,
): string {
  switch (error?.kind) {
    case "unauthorized":
      return `${moduleLabel} 데이터는 현재 세션에서는 조회할 수 없습니다. 개발 로그인 중이거나 세션 권한이 연결되지 않은 상태일 수 있습니다.`;
    case "forbidden":
      return `${moduleLabel} 데이터 조회 권한이 없습니다.`;
    case "unavailable":
      return `${moduleLabel} 데이터를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.`;
    case "unreachable":
    default:
      return `${moduleLabel} backend is unreachable. Data may be unavailable.`;
  }
}

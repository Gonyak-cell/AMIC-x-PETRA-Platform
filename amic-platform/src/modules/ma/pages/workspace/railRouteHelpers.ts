import type { RailToolId } from "@/modules/ma/constants";

/**
 * Rail tool 열기 시 navigate 경로를 생성한다.
 * 기존 search params를 모두 보존하고 baseTab만 upsert한다.
 */
export function buildRailOpenPath(
  txnId: string,
  toolId: RailToolId,
  currentBaseTab: string,
  currentSearchParams: URLSearchParams,
): string {
  const params = new URLSearchParams(currentSearchParams);
  params.set("baseTab", currentBaseTab);
  return `/ma/transactions/${txnId}/${toolId}?${params.toString()}`;
}

/**
 * Rail tool 닫기 시 navigate 경로를 생성한다.
 * baseTab만 제거하고 나머지 query는 그대로 유지한다.
 */
export function buildRailClosePath(
  txnId: string,
  primaryTab: string,
  currentSearchParams: URLSearchParams,
): string {
  const params = new URLSearchParams(currentSearchParams);
  params.delete("baseTab");

  const tabSegment = primaryTab === "overview" ? "" : `/${primaryTab}`;
  const qs = params.toString();
  return `/ma/transactions/${txnId}${tabSegment}${qs ? `?${qs}` : ""}`;
}

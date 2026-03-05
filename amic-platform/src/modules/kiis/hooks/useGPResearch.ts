import { useQuery } from "@tanstack/react-query";
import { maApi } from "@/api/maClient";
import type {
  GpProfileFromMA,
  GPResearchItem,
} from "@/modules/kiis/types/gpResearch";
import { adaptGpProfileToResearchItem } from "@/modules/kiis/types/gpResearch";

const STALE_TIME = 5 * 60_000; // 5분

/**
 * GP Research 전수 목록 — 개발 환경은 Mock, 프로덕션은 deal-mgmt GP 프로필 API.
 *
 * `import.meta.env.DEV` + dynamic `import()` 조합으로
 * Vite 프로덕션 빌드 시 gpMockData.ts가 번들에서 완전 제거된다.
 */
export function useGPResearchList() {
  return useQuery<GPResearchItem[]>({
    queryKey: ["kiis", "gp-research"],
    queryFn: async () => {
      if (import.meta.env.DEV) {
        const { GP_MOCK_DATA } = await import("@/modules/kiis/data/gpMockData");
        return GP_MOCK_DATA;
      }
      const { data } = await maApi.get<GpProfileFromMA[]>(
        "/pef-registry/gp-profiles",
      );
      return data.map(adaptGpProfileToResearchItem);
    },
    staleTime: STALE_TIME,
  });
}

/**
 * GP Research 단건 조회 — 목록 캐시에서 ID로 검색 (별도 API 요청 없음).
 */
export function useGPResearchDetail(id: string | null) {
  const { data: list } = useGPResearchList();
  return useQuery<GPResearchItem | null>({
    queryKey: ["kiis", "gp-research", id],
    queryFn: () => list?.find((gp) => gp.id === id) ?? null,
    enabled: !!id,
    staleTime: STALE_TIME,
  });
}

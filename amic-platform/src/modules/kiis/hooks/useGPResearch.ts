import { useQuery } from "@tanstack/react-query";
import type { GPResearchItem } from "@/modules/kiis/types/gpResearch";

const STALE_TIME = 5 * 60_000; // 5분

/**
 * GP Research 전수 목록 — 개발 환경에서만 Mock 데이터 로딩.
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
      // 프로덕션: 빈 배열 (향후 백엔드 API로 교체)
      // TODO: const { data } = await kiisApi.get("/kofia/gp/research");
      return [];
    },
    staleTime: STALE_TIME,
  });
}

/**
 * GP Research 단건 조회 — ID로 Mock 데이터에서 검색.
 */
export function useGPResearchDetail(id: string | null) {
  return useQuery<GPResearchItem | null>({
    queryKey: ["kiis", "gp-research", id],
    queryFn: async () => {
      if (!id) return null;
      if (import.meta.env.DEV) {
        const { GP_MOCK_DATA } = await import("@/modules/kiis/data/gpMockData");
        return GP_MOCK_DATA.find((gp) => gp.id === id) ?? null;
      }
      return null;
    },
    enabled: !!id,
    staleTime: STALE_TIME,
  });
}

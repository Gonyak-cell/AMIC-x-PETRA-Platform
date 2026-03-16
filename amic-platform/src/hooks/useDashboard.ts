import { useQuery } from "@tanstack/react-query";
import api from "@/api/client";
import { kiisApi } from "@/api/kiisClient";
import { imApi } from "@/api/imClient";
import { maApi } from "@/api/maClient";
import type { ModuleHealth } from "@/types/dashboard";

export function useModuleHealth() {
  return useQuery<ModuleHealth[]>({
    queryKey: ["portal", "health"],
    queryFn: async () => {
      const checks = [
        {
          module: "fdd" as const,
          label: "FDD Engine",
          fn: () => api.get("/health"),
        },
        {
          module: "kiis" as const,
          label: "KIIS",
          fn: () => kiisApi.get("/health"),
        },
        { module: "im" as const, label: "IM", fn: () => imApi.get("/health") },
        {
          module: "ma" as const,
          label: "M&A Deals",
          fn: () => maApi.get("/health"),
        },
      ];

      const results = await Promise.allSettled(
        checks.map((c) =>
          Promise.race([
            c.fn(),
            new Promise((_, reject) =>
              setTimeout(() => reject(new Error("timeout")), 3000),
            ),
          ]),
        ),
      );

      return checks.map((c, i) => ({
        module: c.module,
        label: c.label,
        healthy: results[i].status === "fulfilled",
      }));
    },
    staleTime: 60_000,
    refetchInterval: 60_000,
  });
}

import { useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import * as Sentry from "@sentry/react";
import type { AxiosInstance } from "axios";
import api from "@/api/client";
import { kiisApi } from "@/api/kiisClient";
import { imApi } from "@/api/imClient";
import { maApi } from "@/api/maClient";

export type ServiceStatus = "healthy" | "degraded" | "down" | "unknown";

export interface HealthStatus {
  fdd: ServiceStatus;
  kiis: ServiceStatus;
  im: ServiceStatus;
  ma: ServiceStatus;
}

const SERVICES = ["fdd", "kiis", "im", "ma"] as const;

const SERVICE_CLIENTS: Record<(typeof SERVICES)[number], AxiosInstance> = {
  fdd: api,
  kiis: kiisApi,
  im: imApi,
  ma: maApi,
};

async function checkService(
  service: (typeof SERVICES)[number],
): Promise<ServiceStatus> {
  try {
    const { status } = await SERVICE_CLIENTS[service].get("/health", {
      timeout: 5000,
    });
    return status === 200 ? "healthy" : "degraded";
  } catch {
    return "down";
  }
}

export function useHealthCheck(enabled = true) {
  const prevStatusRef = useRef<HealthStatus | null>(null);

  return useQuery<HealthStatus>({
    queryKey: ["health-check"],
    queryFn: async () => {
      const results = await Promise.allSettled(
        SERVICES.map((s) => checkService(s)),
      );

      const status: HealthStatus = {
        fdd: results[0].status === "fulfilled" ? results[0].value : "down",
        kiis: results[1].status === "fulfilled" ? results[1].value : "down",
        im: results[2].status === "fulfilled" ? results[2].value : "down",
        ma: results[3].status === "fulfilled" ? results[3].value : "down",
      };

      const prev = prevStatusRef.current;
      for (const service of SERVICES) {
        if (status[service] === "down" && prev?.[service] !== "down") {
          Sentry.captureMessage(`Backend ${service} health check failed`, {
            level: "warning",
            tags: { service, category: "health-check" },
          });
        }
      }
      prevStatusRef.current = status;

      return status;
    },
    refetchInterval: 60_000,
    staleTime: 30_000,
    enabled,
  });
}

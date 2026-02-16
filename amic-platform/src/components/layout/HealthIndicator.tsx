import { useState } from "react";
import { cn } from "@/lib/cn";
import { useHealthCheck, type ServiceStatus } from "@/hooks/useHealthCheck";
import { useAuth } from "@/hooks/useAuth";

const STATUS_COLORS: Record<ServiceStatus, string> = {
  healthy: "bg-positive",
  degraded: "bg-caution",
  down: "bg-negative",
  unknown: "bg-text-tertiary",
};

const STATUS_LABELS: Record<ServiceStatus, string> = {
  healthy: "Healthy",
  degraded: "Degraded",
  down: "Down",
  unknown: "Unknown",
};

const SERVICE_NAMES = { fdd: "FDD", kiis: "KIIS", im: "IM" } as const;

export function HealthIndicator() {
  const { hasPermission } = useAuth();
  const [showDetail, setShowDetail] = useState(false);
  const { data: health, isLoading } = useHealthCheck(
    hasPermission("audit:view"),
  );

  if (!hasPermission("audit:view")) return null;

  const allHealthy =
    health &&
    health.fdd === "healthy" &&
    health.kiis === "healthy" &&
    health.im === "healthy";

  return (
    <div className="relative px-4 py-2 border-t border-white/10">
      <button
        onClick={() => setShowDetail((prev) => !prev)}
        className="flex items-center gap-2 text-xs text-white/60 hover:text-white/90 transition-colors w-full"
        aria-label="Toggle service health details"
      >
        <span className="flex gap-1">
          {isLoading ? (
            <>
              <span className="w-2 h-2 rounded-full bg-text-tertiary animate-pulse" />
              <span className="w-2 h-2 rounded-full bg-text-tertiary animate-pulse" />
              <span className="w-2 h-2 rounded-full bg-text-tertiary animate-pulse" />
            </>
          ) : health ? (
            (
              Object.entries(SERVICE_NAMES) as [
                keyof typeof SERVICE_NAMES,
                string,
              ][]
            ).map(([key]) => (
              <span
                key={key}
                className={cn("w-2 h-2 rounded-full", STATUS_COLORS[health[key]])}
                title={`${SERVICE_NAMES[key]}: ${STATUS_LABELS[health[key]]}`}
              />
            ))
          ) : (
            <span className="w-2 h-2 rounded-full bg-text-tertiary" />
          )}
        </span>
        <span>{allHealthy ? "All systems OK" : isLoading ? "Checking..." : "Service status"}</span>
      </button>

      {showDetail && health && (
        <div className="mt-2 space-y-1 text-xs">
          {(
            Object.entries(SERVICE_NAMES) as [
              keyof typeof SERVICE_NAMES,
              string,
            ][]
          ).map(([key, label]) => (
            <div key={key} className="flex items-center justify-between text-white/70">
              <span>{label}</span>
              <span className="flex items-center gap-1.5">
                <span
                  className={cn("w-1.5 h-1.5 rounded-full", STATUS_COLORS[health[key]])}
                />
                <span>{STATUS_LABELS[health[key]]}</span>
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

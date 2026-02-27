import { useCallback } from "react";
import type { LicenseType } from "@/modules/kiis/types/gpResearch";
import { LICENSE_LABELS } from "@/modules/kiis/types/gpResearch";

interface GPSegmentControlProps {
  selected: Set<LicenseType>;
  onChange: (selected: Set<LicenseType>) => void;
}

const LICENSE_OPTIONS: LicenseType[] = ["pef", "vc", "nta"];

export function GPSegmentControl({
  selected,
  onChange,
}: GPSegmentControlProps) {
  const toggle = useCallback(
    (license: LicenseType) => {
      const next = new Set(selected);
      if (next.has(license)) {
        next.delete(license);
      } else {
        next.add(license);
      }
      onChange(next);
    },
    [selected, onChange],
  );

  return (
    <div className="flex gap-2" role="group" aria-label="라이선스 유형 필터">
      {LICENSE_OPTIONS.map((license) => {
        const isActive = selected.has(license);
        return (
          <button
            key={license}
            type="button"
            onClick={() => toggle(license)}
            aria-pressed={isActive}
            className={`px-4 py-2 rounded-dr-sm text-sm font-medium transition-colors ${
              isActive
                ? "bg-accent text-white shadow-sm"
                : "bg-white text-text-secondary border border-border hover:border-accent/50"
            }`}
          >
            {LICENSE_LABELS[license]}
          </button>
        );
      })}
    </div>
  );
}

import { Badge } from "@/components/ui";
import { RELEASE_NOTES } from "@/lib/releaseNotes";
import type { BadgeVariant } from "@/components/ui";

const CHANGE_TYPE_VARIANT: Record<string, BadgeVariant> = {
  feature: "info",
  fix: "success",
  improvement: "neutral",
};

const CHANGE_TYPE_LABEL: Record<string, string> = {
  feature: "Feature",
  fix: "Fix",
  improvement: "Improvement",
};

export function ReleaseNotes() {
  return (
    <div className="space-y-6">
      {RELEASE_NOTES.map((release) => (
        <div
          key={release.version}
          className="border border-gray-border rounded-lg overflow-hidden"
        >
          {/* Version header */}
          <div className="bg-bg-cool px-5 py-3 border-b border-gray-border flex items-center gap-3">
            <span className="font-heading font-semibold text-text-dark">
              v{release.version}
            </span>
            <span className="text-sm text-text-secondary">{release.date}</span>
          </div>

          <div className="px-5 py-4 space-y-3">
            {/* Highlights */}
            {release.highlights.length > 0 && (
              <div>
                <h4 className="text-xs font-semibold text-text-secondary uppercase tracking-wider mb-1.5">
                  Highlights
                </h4>
                <ul className="list-disc list-inside text-sm text-text-dark space-y-0.5">
                  {release.highlights.map((h) => (
                    <li key={h}>{h}</li>
                  ))}
                </ul>
              </div>
            )}

            {/* Changes */}
            <div>
              <h4 className="text-xs font-semibold text-text-secondary uppercase tracking-wider mb-1.5">
                Changes
              </h4>
              <div className="space-y-1.5">
                {release.changes.map((c, i) => (
                  <div key={i} className="flex items-start gap-2">
                    <Badge
                      variant={CHANGE_TYPE_VARIANT[c.type]}
                      className="mt-0.5 text-xs shrink-0"
                    >
                      {CHANGE_TYPE_LABEL[c.type]}
                    </Badge>
                    <span className="text-sm text-text-dark">
                      {c.description}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

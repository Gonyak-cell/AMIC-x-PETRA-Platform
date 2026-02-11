import { useState, useMemo } from "react";
import { Input, Badge, Button, Card } from "@/components/ui";
import { GLOSSARY } from "@/lib/glossary";
import type { GlossaryTerm } from "@/types/help";

const MODULE_FILTERS = [
  { value: "all", label: "All" },
  { value: "fdd", label: "FDD" },
  { value: "kiis", label: "KIIS" },
  { value: "im", label: "IM" },
  { value: "general", label: "General" },
] as const;

const MODULE_BADGE_VARIANT: Record<string, "success" | "info" | "warning" | "neutral"> = {
  fdd: "info",
  kiis: "success",
  im: "warning",
  general: "neutral",
};

export function GlossaryList() {
  const [search, setSearch] = useState("");
  const [moduleFilter, setModuleFilter] = useState<string>("all");

  const filtered = useMemo(() => {
    let terms: GlossaryTerm[] = [...GLOSSARY];

    if (moduleFilter !== "all") {
      terms = terms.filter((t) => t.module === moduleFilter);
    }

    if (search.trim()) {
      const q = search.toLowerCase();
      terms = terms.filter(
        (t) =>
          t.term.toLowerCase().includes(q) ||
          (t.abbreviation && t.abbreviation.toLowerCase().includes(q)) ||
          t.definition.toLowerCase().includes(q),
      );
    }

    return terms.sort((a, b) => a.term.localeCompare(b.term));
  }, [search, moduleFilter]);

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex flex-wrap items-end gap-4">
        <div className="w-64">
          <Input
            label="Search terms"
            placeholder="Type to filter..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <div className="flex gap-1">
          {MODULE_FILTERS.map((m) => (
            <Button
              key={m.value}
              variant={moduleFilter === m.value ? "primary" : "ghost"}
              size="sm"
              onClick={() => setModuleFilter(m.value)}
            >
              {m.label}
            </Button>
          ))}
        </div>
      </div>

      {/* Term list */}
      <div className="space-y-3">
        {filtered.length === 0 ? (
          <p className="text-sm text-text-secondary py-8 text-center">
            No matching terms found.
          </p>
        ) : (
          filtered.map((term) => (
            <Card key={term.term} variant="forest-lift">
              <div className="p-4">
                <div className="flex items-center gap-2 mb-1">
                  <span className="font-medium text-text-dark">{term.term}</span>
                  {term.abbreviation && (
                    <span className="text-xs font-mono text-text-secondary bg-bg-cool px-1.5 py-0.5 rounded">
                      {term.abbreviation}
                    </span>
                  )}
                  <Badge variant={MODULE_BADGE_VARIANT[term.module]}>
                    {term.module.toUpperCase()}
                  </Badge>
                </div>
                <p className="text-sm text-text-secondary">{term.definition}</p>
              </div>
            </Card>
          ))
        )}
      </div>
    </div>
  );
}

import { useState } from "react";
import { Button, Card, PageHero } from "@/components/ui";
import { GlossaryList } from "@/components/help/GlossaryList";
import { ReleaseNotes } from "@/components/help/ReleaseNotes";
import { KeyboardShortcutsModal } from "@/components/help/KeyboardShortcutsModal";
import { KEYBOARD_SHORTCUTS } from "@/lib/shortcuts";

type HelpTab = "getting-started" | "glossary" | "shortcuts" | "releases";

const TABS: Array<{ id: HelpTab; label: string }> = [
  { id: "getting-started", label: "Getting Started" },
  { id: "glossary", label: "Glossary" },
  { id: "shortcuts", label: "Shortcuts" },
  { id: "releases", label: "Release Notes" },
];

const CONTEXT_LABELS: Record<string, string> = {
  global: "Global",
  fdd: "FDD",
  kiis: "KIIS",
  im: "IM",
};

export default function HelpPage() {
  const [activeTab, setActiveTab] = useState<HelpTab>("getting-started");
  const [shortcutsOpen, setShortcutsOpen] = useState(false);

  return (
    <div className="space-y-6">
      {/* Hero Section */}
      <PageHero
        title="Help Center"
        subtitle="Guides, glossary, keyboard shortcuts, and release notes"
        compact
      />

      {/* Tab bar */}
      <div className="flex gap-1 border-b border-gray-border">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px ${
              activeTab === tab.id
                ? "border-amic text-amic"
                : "border-transparent text-text-secondary hover:text-text-dark"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {activeTab === "getting-started" && (
        <div className="space-y-6">
          <div className="bg-bg-cool rounded-lg p-6">
            <h2 className="text-lg font-heading font-semibold text-text-dark mb-2">
              Welcome to AMIC x PETRA Platform
            </h2>
            <p className="text-sm text-text-secondary mb-4">
              This platform integrates three modules for investment analysis:
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <Card variant="forest-lift">
                <div className="p-4">
                  <div className="font-medium text-text-dark mb-1">Auto FDD</div>
                  <p className="text-xs text-text-secondary">
                    Automated Financial Due Diligence — upload financial data, map
                    accounts, and generate QoE/NWC/Net Debt analysis.
                  </p>
                </div>
              </Card>
              <Card variant="forest-lift">
                <div className="p-4">
                  <div className="font-medium text-text-dark mb-1">KIIS</div>
                  <p className="text-xs text-text-secondary">
                    Korea Investment Intelligence System — monitor companies,
                    funds, REITs, news, and deal sourcing from DART/KOFIA.
                  </p>
                </div>
              </Card>
              <Card variant="forest-lift">
                <div className="p-4">
                  <div className="font-medium text-text-dark mb-1">
                    IM Generator
                  </div>
                  <p className="text-xs text-text-secondary">
                    Investment Memorandum Generator — auto-generate PPTX/PDF
                    investment memos from corporate data.
                  </p>
                </div>
              </Card>
            </div>
          </div>

          <div>
            <h3 className="text-base font-heading font-semibold text-text-dark mb-3">
              Quick Tips
            </h3>
            <ul className="space-y-2 text-sm text-text-secondary">
              <li className="flex items-start gap-2">
                <kbd className="px-1.5 py-0.5 bg-bg-cool border border-gray-border rounded text-xs font-mono shrink-0">
                  Ctrl+K
                </kbd>
                <span>Open global search to find deals, companies, or documents across all modules</span>
              </li>
              <li className="flex items-start gap-2">
                <kbd className="px-1.5 py-0.5 bg-bg-cool border border-gray-border rounded text-xs font-mono shrink-0">
                  ?
                </kbd>
                <span>View all keyboard shortcuts at any time</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-amic shrink-0">★</span>
                <span>Star items to add them to your favorites in the sidebar for quick access</span>
              </li>
            </ul>
          </div>
        </div>
      )}

      {activeTab === "glossary" && <GlossaryList />}

      {activeTab === "shortcuts" && (
        <div className="space-y-5">
          {Object.entries(
            KEYBOARD_SHORTCUTS.reduce<
              Record<string, typeof KEYBOARD_SHORTCUTS>
            >((acc, s) => {
              if (!acc[s.context]) acc[s.context] = [];
              acc[s.context].push(s);
              return acc;
            }, {}),
          ).map(([context, shortcuts]) => (
            <div key={context}>
              <h3 className="text-xs font-semibold text-text-secondary uppercase tracking-wider mb-2">
                {CONTEXT_LABELS[context] ?? context}
              </h3>
              <div className="space-y-2">
                {shortcuts.map((s) => (
                  <div
                    key={s.description}
                    className="flex items-center justify-between p-3 bg-bg-cool rounded-lg"
                  >
                    <span className="text-sm text-text-dark">
                      {s.description}
                    </span>
                    <div className="flex gap-1">
                      {s.keys.map((key) => (
                        <kbd
                          key={key}
                          className="px-2 py-0.5 bg-white border border-gray-border rounded text-xs font-mono text-text-secondary"
                        >
                          {key}
                        </kbd>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}

          <Button
            variant="ghost"
            size="sm"
            onClick={() => setShortcutsOpen(true)}
          >
            Open as Modal
          </Button>
          <KeyboardShortcutsModal
            open={shortcutsOpen}
            onClose={() => setShortcutsOpen(false)}
          />
        </div>
      )}

      {activeTab === "releases" && <ReleaseNotes />}
    </div>
  );
}

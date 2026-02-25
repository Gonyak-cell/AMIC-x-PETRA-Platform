import { Modal } from "@/components/ui";
import { KEYBOARD_SHORTCUTS } from "@/lib/shortcuts";

interface KeyboardShortcutsModalProps {
  open: boolean;
  onClose: () => void;
}

const CONTEXT_LABELS: Record<string, string> = {
  global: "Global",
  ma: "M&A Deals",
  docs: "Deal Doc Studio",
  fdd: "FDD",
  kiis: "KIIS",
  im: "IM",
};

export function KeyboardShortcutsModal({
  open,
  onClose,
}: KeyboardShortcutsModalProps) {
  const grouped = KEYBOARD_SHORTCUTS.reduce<
    Record<string, typeof KEYBOARD_SHORTCUTS>
  >((acc, s) => {
    const key = s.context;
    if (!acc[key]) acc[key] = [];
    acc[key].push(s);
    return acc;
  }, {});

  return (
    <Modal open={open} onClose={onClose} title="Keyboard Shortcuts" size="md">
      <div className="space-y-5">
        {Object.entries(grouped).map(([context, shortcuts]) => (
          <div key={context}>
            <h3 className="text-xs font-semibold text-text-secondary uppercase tracking-wider mb-2">
              {CONTEXT_LABELS[context] ?? context}
            </h3>
            <div className="space-y-2">
              {shortcuts.map((s) => (
                <div
                  key={s.description}
                  className="flex items-center justify-between"
                >
                  <span className="text-sm text-text-dark">
                    {s.description}
                  </span>
                  <div className="flex gap-1">
                    {s.keys.map((key) => (
                      <kbd
                        key={key}
                        className="px-2 py-0.5 bg-bg-cool border border-gray-border rounded text-xs font-mono text-text-secondary"
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
      </div>
    </Modal>
  );
}

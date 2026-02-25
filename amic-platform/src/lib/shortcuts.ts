import type { KeyboardShortcut } from "@/types/help";

export const KEYBOARD_SHORTCUTS: KeyboardShortcut[] = [
  // Global
  {
    keys: ["Ctrl", "K"],
    description: "Open global search (Command Palette)",
    context: "global",
  },
  {
    keys: ["Escape"],
    description: "Close modal, sidebar, or search palette",
    context: "global",
  },
  {
    keys: ["?"],
    description: "Open keyboard shortcuts help",
    context: "global",
  },
  {
    keys: ["Ctrl", "Shift", "C"],
    description: "Open Calendar view",
    context: "global",
  },
  {
    keys: ["Ctrl", "Shift", "A"],
    description: "Open Analytics dashboard",
    context: "global",
  },

  // M&A Deals
  {
    keys: ["Ctrl", "Shift", "T"],
    description: "Create new M&A transaction",
    context: "ma",
  },
  {
    keys: ["Ctrl", "Shift", "W"],
    description: "Go to transaction workspace overview",
    context: "ma",
  },
  {
    keys: ["Ctrl", "Shift", "P"],
    description: "Open pipeline view (transaction list)",
    context: "ma",
  },

  // Deal Doc Studio
  {
    keys: ["Ctrl", "Shift", "D"],
    description: "Open Deal Doc Studio home",
    context: "docs",
  },
  {
    keys: ["Ctrl", "Shift", "M"],
    description: "Create new marketing document (TM/IM)",
    context: "docs",
  },

  // FDD
  {
    keys: ["Ctrl", "Shift", "N"],
    description: "Create new deal",
    context: "fdd",
  },

  // KIIS
  {
    keys: ["Ctrl", "Shift", "S"],
    description: "Search companies",
    context: "kiis",
  },

  // IM
  {
    keys: ["Ctrl", "Shift", "G"],
    description: "Generate new Investment Memorandum",
    context: "im",
  },
];

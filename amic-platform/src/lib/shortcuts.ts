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

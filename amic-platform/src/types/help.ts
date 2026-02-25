export interface GlossaryTerm {
  term: string;
  abbreviation: string | null;
  definition: string;
  module: "fdd" | "kiis" | "im" | "ma" | "docs" | "general";
}

export interface KeyboardShortcut {
  keys: string[];
  description: string;
  context: "global" | "fdd" | "kiis" | "im" | "ma" | "docs";
}

export interface ReleaseNote {
  version: string;
  date: string;
  highlights: string[];
  changes: Array<{
    type: "feature" | "fix" | "improvement";
    description: string;
  }>;
}

export type SearchModule = "fdd" | "kiis" | "im";

export interface GlobalSearchResult {
  id: string;
  module: SearchModule;
  type: string;
  title: string;
  subtitle: string | null;
  path: string;
}

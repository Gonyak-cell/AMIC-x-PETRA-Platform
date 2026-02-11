export type FavoriteType = "deal" | "company" | "im-project";

export interface FavoriteItem {
  id: string;
  type: FavoriteType;
  name: string;
  path: string;
  addedAt: string;
}

export interface RecentItem {
  id: string;
  type: FavoriteType;
  name: string;
  path: string;
  visitedAt: string;
}

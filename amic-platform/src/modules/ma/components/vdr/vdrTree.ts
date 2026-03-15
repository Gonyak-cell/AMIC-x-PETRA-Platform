/**
 * VDR 폴더 트리 인덱스 유틸리티
 *
 * useVdrFolders 훅이 반환하는 평탄 배열(parent_id 참조)을
 * O(1) Map 인덱스로 변환하고, 브레드크럼 경로를 계산한다.
 */

import type { VdrFolder } from "@/modules/ma/types/vdr";

export interface FolderIndex {
  /** id → 폴더 Map */
  folderById: Map<string, VdrFolder>;
  /** parent_id → 직계 자식 목록 Map (루트는 null 키) */
  childrenByParentId: Map<string | null, VdrFolder[]>;
}

export interface Breadcrumb {
  id: string | null;
  name: string;
}

/**
 * 평탄 폴더 배열로 O(1) 조회 인덱스를 구축한다.
 *
 * - 입력: useVdrFolders 훅이 반환하는 flat VdrFolder[]
 * - 출력: folderById + childrenByParentId 두 Map
 *
 * @param folders useVdrFolders 훅의 반환값 (flat 배열)
 */
export function buildFolderIndex(folders: VdrFolder[]): FolderIndex {
  const folderById = new Map<string, VdrFolder>();
  const childrenByParentId = new Map<string | null, VdrFolder[]>();

  for (const folder of folders) {
    folderById.set(folder.id, folder);
    const siblings = childrenByParentId.get(folder.parent_id) ?? [];
    siblings.push(folder);
    childrenByParentId.set(folder.parent_id, siblings);
  }

  return { folderById, childrenByParentId };
}

/**
 * 대상 폴더까지의 브레드크럼 경로를 반환한다.
 *
 * - null → VDR 루트 단일 항목
 * - 존재하는 folderId → 루트(null) + 조상 경로 + 대상 폴더
 *
 * @param folderById buildFolderIndex 결과의 folderById Map
 * @param targetId 현재 위치 폴더 id (null = VDR 루트)
 */
export function buildBreadcrumbs(
  folderById: Map<string, VdrFolder>,
  targetId: string | null,
): Breadcrumb[] {
  if (targetId === null) return [{ id: null, name: "VDR" }];

  const path: Breadcrumb[] = [];
  let current: VdrFolder | undefined = folderById.get(targetId);
  while (current) {
    path.unshift({ id: current.id, name: current.name });
    current =
      current.parent_id != null ? folderById.get(current.parent_id) : undefined;
  }
  return [{ id: null, name: "VDR" }, ...path];
}

/**
 * vdrTree.ts 순수 유틸 단위 테스트
 *
 * 입력: useVdrFolders 훅 반환값과 동일한 평탄 배열
 * 검증: buildFolderIndex / buildBreadcrumbs 동작 정확성
 */

import { describe, expect, it } from "vitest";
import type { VdrFolder } from "@/modules/ma/types/vdr";
import { buildBreadcrumbs, buildFolderIndex } from "../vdrTree";

// ── 테스트 픽스처 ──────────────────────────────────────

function makeFolder(partial: Partial<VdrFolder> & { id: string }): VdrFolder {
  return {
    transaction_id: "txn-1",
    parent_id: null,
    name: partial.id,
    category: "FINANCIAL",
    order_index: 0,
    is_required: false,
    description: null,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    children: [],
    document_count: 0,
    ...partial,
  };
}

/** 2단계: root → child */
const twoLevelFlat: VdrFolder[] = [
  makeFolder({ id: "root", parent_id: null, name: "재무자료" }),
  makeFolder({ id: "child", parent_id: "root", name: "감사보고서" }),
];

/** 3단계: root → child → grandchild */
const threeLevelFlat: VdrFolder[] = [
  makeFolder({ id: "root", parent_id: null, name: "재무자료" }),
  makeFolder({ id: "child", parent_id: "root", name: "감사보고서" }),
  makeFolder({ id: "grandchild", parent_id: "child", name: "2023년도" }),
];

// ── buildFolderIndex 테스트 ────────────────────────────

describe("buildFolderIndex", () => {
  it("빈 배열은 빈 Map을 반환한다", () => {
    const { folderById, childrenByParentId } = buildFolderIndex([]);
    expect(folderById.size).toBe(0);
    expect(childrenByParentId.size).toBe(0);
  });

  it("2단계 트리: folderById에 모든 폴더가 포함된다", () => {
    const { folderById } = buildFolderIndex(twoLevelFlat);
    expect(folderById.has("root")).toBe(true);
    expect(folderById.has("child")).toBe(true);
    expect(folderById.get("root")!.name).toBe("재무자료");
    expect(folderById.get("child")!.name).toBe("감사보고서");
  });

  it("2단계 트리: childrenByParentId가 각 깊이에서 올바르다", () => {
    const { childrenByParentId } = buildFolderIndex(twoLevelFlat);
    // 루트 자식 (parent_id = null)
    expect(childrenByParentId.get(null)).toHaveLength(1);
    expect(childrenByParentId.get(null)![0].id).toBe("root");
    // root의 자식
    expect(childrenByParentId.get("root")).toHaveLength(1);
    expect(childrenByParentId.get("root")![0].id).toBe("child");
    // child의 자식 없음
    expect(childrenByParentId.get("child")).toBeUndefined();
  });

  it("3단계 트리: grandchild까지 folderById에 포함된다", () => {
    const { folderById } = buildFolderIndex(threeLevelFlat);
    expect(folderById.has("grandchild")).toBe(true);
    expect(folderById.get("grandchild")!.name).toBe("2023년도");
  });

  it("3단계 트리: childrenByParentId가 각 깊이에서 올바르다", () => {
    const { childrenByParentId } = buildFolderIndex(threeLevelFlat);
    expect(childrenByParentId.get(null)).toHaveLength(1);
    expect(childrenByParentId.get("root")).toHaveLength(1);
    expect(childrenByParentId.get("child")).toHaveLength(1);
    expect(childrenByParentId.get("child")![0].id).toBe("grandchild");
    // grandchild의 자식 없음
    expect(childrenByParentId.get("grandchild")).toBeUndefined();
  });

  it("같은 부모를 가진 형제 폴더가 모두 포함된다", () => {
    const siblings: VdrFolder[] = [
      makeFolder({ id: "p", parent_id: null, name: "부모" }),
      makeFolder({ id: "s1", parent_id: "p", name: "형제1" }),
      makeFolder({ id: "s2", parent_id: "p", name: "형제2" }),
    ];
    const { childrenByParentId } = buildFolderIndex(siblings);
    expect(childrenByParentId.get("p")).toHaveLength(2);
  });
});

// ── buildBreadcrumbs 테스트 ───────────────────────────

describe("buildBreadcrumbs", () => {
  it("targetId=null이면 VDR 루트 단일 항목을 반환한다", () => {
    const { folderById } = buildFolderIndex(twoLevelFlat);
    const crumbs = buildBreadcrumbs(folderById, null);
    expect(crumbs).toEqual([{ id: null, name: "VDR" }]);
  });

  it("2단계: root 폴더의 경로가 [VDR, root]이다", () => {
    const { folderById } = buildFolderIndex(twoLevelFlat);
    const crumbs = buildBreadcrumbs(folderById, "root");
    expect(crumbs).toEqual([
      { id: null, name: "VDR" },
      { id: "root", name: "재무자료" },
    ]);
  });

  it("2단계: child 폴더의 경로가 [VDR, root, child]이다", () => {
    const { folderById } = buildFolderIndex(twoLevelFlat);
    const crumbs = buildBreadcrumbs(folderById, "child");
    expect(crumbs).toEqual([
      { id: null, name: "VDR" },
      { id: "root", name: "재무자료" },
      { id: "child", name: "감사보고서" },
    ]);
  });

  it("3단계: grandchild 경로가 [VDR, root, child, grandchild]이다", () => {
    const { folderById } = buildFolderIndex(threeLevelFlat);
    const crumbs = buildBreadcrumbs(folderById, "grandchild");
    expect(crumbs).toEqual([
      { id: null, name: "VDR" },
      { id: "root", name: "재무자료" },
      { id: "child", name: "감사보고서" },
      { id: "grandchild", name: "2023년도" },
    ]);
  });

  it("존재하지 않는 folderId는 VDR 루트 단일 항목을 반환한다", () => {
    const { folderById } = buildFolderIndex(twoLevelFlat);
    const crumbs = buildBreadcrumbs(folderById, "nonexistent");
    expect(crumbs).toEqual([{ id: null, name: "VDR" }]);
  });
});

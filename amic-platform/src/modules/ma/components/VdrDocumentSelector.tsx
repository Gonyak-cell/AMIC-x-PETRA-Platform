/**
 * VDR 문서 선택기 — Q&A 참조 문서 범위 지정 UI.
 *
 * 폴더별 그룹핑 + 체크박스로 개별/폴더 단위 선택.
 */
import { useMemo, useState } from "react";
import { ChevronDown, ChevronRight, FileText, Folder } from "lucide-react";

import { useVdrFolders, useVdrAllDocuments } from "@/modules/ma/hooks/useVdr";
import type { VdrDocument, VdrFolder } from "@/modules/ma/types/vdr";

interface VdrDocumentSelectorProps {
  txnId: string;
  selectedDocumentIds: string[];
  onSelectionChange: (docIds: string[]) => void;
}

interface FolderGroup {
  folder: VdrFolder;
  documents: VdrDocument[];
}

function groupDocumentsByFolder(
  folders: VdrFolder[],
  documents: VdrDocument[],
): FolderGroup[] {
  const flatFolders = flattenFolders(folders);
  const folderMap = new Map<string, VdrFolder>();
  for (const f of flatFolders) folderMap.set(f.id, f);

  const grouped = new Map<string, VdrDocument[]>();
  for (const doc of documents) {
    const list = grouped.get(doc.folder_id) ?? [];
    list.push(doc);
    grouped.set(doc.folder_id, list);
  }

  const result: FolderGroup[] = [];
  for (const [folderId, docs] of grouped) {
    const folder = folderMap.get(folderId);
    if (folder) result.push({ folder, documents: docs });
  }

  return result.sort((a, b) => a.folder.name.localeCompare(b.folder.name));
}

function flattenFolders(folders: VdrFolder[]): VdrFolder[] {
  const result: VdrFolder[] = [];
  for (const f of folders) {
    result.push(f);
    if (f.children?.length) result.push(...flattenFolders(f.children));
  }
  return result;
}

export default function VdrDocumentSelector({
  txnId,
  selectedDocumentIds,
  onSelectionChange,
}: VdrDocumentSelectorProps) {
  const { data: folders = [] } = useVdrFolders(txnId);
  const { data: documents = [] } = useVdrAllDocuments(txnId);
  const [expandedFolders, setExpandedFolders] = useState<Set<string>>(new Set());

  const groups = useMemo(
    () => groupDocumentsByFolder(folders, documents),
    [folders, documents],
  );

  const totalDocs = documents.length;
  const selectedSet = useMemo(() => new Set(selectedDocumentIds), [selectedDocumentIds]);
  const allSelected = selectedDocumentIds.length === 0; // 빈 배열 = 전체 선택

  const toggleFolder = (folderId: string) => {
    setExpandedFolders((prev) => {
      const next = new Set(prev);
      if (next.has(folderId)) next.delete(folderId);
      else next.add(folderId);
      return next;
    });
  };

  const toggleSelectAll = () => {
    if (allSelected) {
      // 전체 선택 → 명시적 선택 모드 전환 (전체 문서 ID 전달)
      onSelectionChange(documents.map((d) => d.id));
    } else {
      // 부분 선택 → 전체 선택 (빈 배열 = BE에서 전체 문서 대상)
      onSelectionChange([]);
    }
  };

  const toggleFolderSelect = (group: FolderGroup) => {
    const folderDocIds = group.documents.map((d) => d.id);
    const allInFolder = folderDocIds.every((id) => selectedSet.has(id));

    if (allSelected) {
      // 전체 → 이 폴더만 해제 = 나머지 모두 선택
      const otherIds = documents
        .filter((d) => !folderDocIds.includes(d.id))
        .map((d) => d.id);
      onSelectionChange(otherIds);
    } else if (allInFolder) {
      // 이 폴더 해제 (최소 1개 유지)
      const remaining = selectedDocumentIds.filter((id) => !folderDocIds.includes(id));
      if (remaining.length === 0) return;
      onSelectionChange(remaining);
    } else {
      // 이 폴더 전체 선택
      const merged = new Set([...selectedDocumentIds, ...folderDocIds]);
      onSelectionChange([...merged]);
    }
  };

  const toggleDocSelect = (docId: string) => {
    if (allSelected) {
      // 전체 → 이 문서만 해제
      const otherIds = documents.filter((d) => d.id !== docId).map((d) => d.id);
      onSelectionChange(otherIds);
    } else if (selectedSet.has(docId)) {
      const filtered = selectedDocumentIds.filter((id) => id !== docId);
      if (filtered.length === 0) return; // 최소 1개 선택 유지
      onSelectionChange(filtered);
    } else {
      onSelectionChange([...selectedDocumentIds, docId]);
    }
  };

  const isDocSelected = (docId: string) => allSelected || selectedSet.has(docId);
  const isFolderAllSelected = (group: FolderGroup) =>
    allSelected || group.documents.every((d) => selectedSet.has(d.id));
  const isFolderPartial = (group: FolderGroup) =>
    !allSelected &&
    group.documents.some((d) => selectedSet.has(d.id)) &&
    !group.documents.every((d) => selectedSet.has(d.id));

  const selectedCount = allSelected ? totalDocs : selectedDocumentIds.length;

  return (
    <div className="text-xs">
      {/* 헤더 */}
      <div className="flex items-center justify-between mb-2">
        <span className="font-medium text-text-dark">
          참조 문서 ({selectedCount}/{totalDocs})
        </span>
        <button
          type="button"
          onClick={toggleSelectAll}
          className="text-accent hover:underline text-[10px]"
        >
          {allSelected ? "선택 해제" : "전체 선택"}
        </button>
      </div>

      {/* 폴더 목록 */}
      <div className="max-h-48 overflow-y-auto space-y-0.5">
        {groups.map((group) => (
          <div key={group.folder.id}>
            {/* 폴더 헤더 */}
            <div className="flex items-center gap-1 py-1 px-1 rounded hover:bg-surface-secondary cursor-pointer">
              <button
                type="button"
                onClick={() => toggleFolder(group.folder.id)}
                className="p-0.5"
                aria-label={`${group.folder.name} 폴더 ${expandedFolders.has(group.folder.id) ? "접기" : "펼치기"}`}
              >
                {expandedFolders.has(group.folder.id) ? (
                  <ChevronDown className="h-3 w-3 text-text-muted" />
                ) : (
                  <ChevronRight className="h-3 w-3 text-text-muted" />
                )}
              </button>

              <input
                type="checkbox"
                checked={isFolderAllSelected(group)}
                ref={(el) => {
                  if (el) el.indeterminate = isFolderPartial(group);
                }}
                onChange={() => toggleFolderSelect(group)}
                className="h-3 w-3 rounded border-border accent-accent"
                aria-label={`${group.folder.name} 폴더 전체 선택`}
              />

              <Folder className="h-3 w-3 text-text-muted" />
              <span className="truncate flex-1 text-text-dark">
                {group.folder.name}
              </span>
              <span className="text-text-muted">({group.documents.length})</span>
            </div>

            {/* 문서 목록 */}
            {expandedFolders.has(group.folder.id) && (
              <div className="pl-7 space-y-0.5">
                {group.documents.map((doc) => (
                  <label
                    key={doc.id}
                    className="flex items-center gap-1.5 py-0.5 px-1 rounded hover:bg-surface-secondary cursor-pointer"
                  >
                    <input
                      type="checkbox"
                      checked={isDocSelected(doc.id)}
                      onChange={() => toggleDocSelect(doc.id)}
                      aria-label={doc.original_name}
                      className="h-3 w-3 rounded border-border accent-accent"
                    />
                    <FileText className="h-3 w-3 text-text-muted flex-shrink-0" />
                    <span className="truncate text-text-dark">{doc.original_name}</span>
                  </label>
                ))}
              </div>
            )}
          </div>
        ))}

        {groups.length === 0 && (
          <p className="text-center text-text-muted py-3">문서가 없습니다</p>
        )}
      </div>
    </div>
  );
}

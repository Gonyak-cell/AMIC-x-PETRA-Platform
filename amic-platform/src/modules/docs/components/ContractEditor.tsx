/** Step 2: TipTap 기반 계약서 에디터 + 툴바 */

import { useEditor, EditorContent } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import { Table } from "@tiptap/extension-table";
import { TableRow } from "@tiptap/extension-table-row";
import { TableCell } from "@tiptap/extension-table-cell";
import { TableHeader } from "@tiptap/extension-table-header";
import { Placeholder } from "@tiptap/extension-placeholder";
import {
  Bold,
  Italic,
  List,
  ListOrdered,
  Heading2,
  Heading3,
  Undo,
  Redo,
  Download,
  Save,
  RefreshCw,
  AlertCircle,
} from "lucide-react";

interface ContractEditorProps {
  html: string;
  onHtmlChange: (html: string) => void;
  onExportDocx: () => void;
  onSave: () => void;
  isExporting: boolean;
  isSaving: boolean;
  title: string;
  isDirty?: boolean;
}

export default function ContractEditor({
  html,
  onHtmlChange,
  onExportDocx,
  onSave,
  isExporting,
  isSaving,
  title,
  isDirty,
}: ContractEditorProps) {
  const editor = useEditor({
    extensions: [
      StarterKit.configure({
        heading: { levels: [1, 2, 3] },
      }),
      Table.configure({ resizable: true }),
      TableRow,
      TableCell,
      TableHeader,
      Placeholder.configure({
        placeholder: "계약서 내용이 여기에 표시됩니다...",
      }),
    ],
    content: html,
    onUpdate: ({ editor: e }) => {
      onHtmlChange(e.getHTML());
    },
  });

  if (!editor) return null;

  return (
    <div className="flex flex-col gap-3">
      {/* 상단 액션 바 */}
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-text-primary">
          {title}
          {isDirty && (
            <span className="ml-2 inline-flex items-center gap-1 text-xs font-normal text-orange-500">
              <AlertCircle className="h-3 w-3" aria-hidden="true" />
              미저장
            </span>
          )}
        </h3>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={onSave}
            disabled={isSaving}
            className="flex items-center gap-1.5 rounded-lg border border-border bg-white px-3 py-1.5 text-xs font-medium text-text-primary hover:bg-white-elevated disabled:opacity-40"
          >
            {isSaving ? (
              <RefreshCw className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Save className="h-3.5 w-3.5" />
            )}
            초안 저장
          </button>
          <button
            type="button"
            onClick={onExportDocx}
            disabled={isExporting}
            className="flex items-center gap-1.5 rounded-lg bg-accent-primary px-3 py-1.5 text-xs font-medium text-white hover:bg-accent-primary/90 disabled:opacity-40"
          >
            {isExporting ? (
              <RefreshCw className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Download className="h-3.5 w-3.5" />
            )}
            Word 다운로드
          </button>
        </div>
      </div>

      {/* 에디터 영역 */}
      <div className="rounded-xl border border-border bg-white">
        {/* 툴바 */}
        <div className="flex flex-wrap items-center gap-0.5 border-b border-border px-3 py-1.5">
          <ToolbarButton
            onClick={() => editor.chain().focus().toggleBold().run()}
            active={editor.isActive("bold")}
            title="굵게"
          >
            <Bold className="h-4 w-4" />
          </ToolbarButton>
          <ToolbarButton
            onClick={() => editor.chain().focus().toggleItalic().run()}
            active={editor.isActive("italic")}
            title="기울임"
          >
            <Italic className="h-4 w-4" />
          </ToolbarButton>

          <div className="mx-1 h-4 w-px bg-border" aria-hidden="true" />

          <ToolbarButton
            onClick={() =>
              editor.chain().focus().toggleHeading({ level: 2 }).run()
            }
            active={editor.isActive("heading", { level: 2 })}
            title="제목 2"
          >
            <Heading2 className="h-4 w-4" />
          </ToolbarButton>
          <ToolbarButton
            onClick={() =>
              editor.chain().focus().toggleHeading({ level: 3 }).run()
            }
            active={editor.isActive("heading", { level: 3 })}
            title="제목 3"
          >
            <Heading3 className="h-4 w-4" />
          </ToolbarButton>

          <div className="mx-1 h-4 w-px bg-border" aria-hidden="true" />

          <ToolbarButton
            onClick={() => editor.chain().focus().toggleBulletList().run()}
            active={editor.isActive("bulletList")}
            title="글머리 목록"
          >
            <List className="h-4 w-4" />
          </ToolbarButton>
          <ToolbarButton
            onClick={() => editor.chain().focus().toggleOrderedList().run()}
            active={editor.isActive("orderedList")}
            title="번호 목록"
          >
            <ListOrdered className="h-4 w-4" />
          </ToolbarButton>

          <div className="mx-1 h-4 w-px bg-border" aria-hidden="true" />

          <ToolbarButton
            onClick={() => editor.chain().focus().undo().run()}
            title="실행 취소"
          >
            <Undo className="h-4 w-4" />
          </ToolbarButton>
          <ToolbarButton
            onClick={() => editor.chain().focus().redo().run()}
            title="다시 실행"
          >
            <Redo className="h-4 w-4" />
          </ToolbarButton>
        </div>

        {/* 에디터 본문 */}
        <div
          className="contract-editor-content prose prose-sm max-w-none p-6"
          role="region"
          aria-label="계약서 본문 편집 영역"
        >
          <EditorContent editor={editor} />
        </div>
      </div>
    </div>
  );
}

// ── 툴바 버튼 ──────────────────────────────────────────────────────────

function ToolbarButton({
  onClick,
  active,
  children,
  title: btnTitle,
}: {
  onClick: () => void;
  active?: boolean;
  children: React.ReactNode;
  title: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active ?? undefined}
      aria-label={btnTitle}
      className={`rounded p-1.5 transition-colors ${
        active
          ? "bg-accent-primary/10 text-accent-primary"
          : "text-text-secondary hover:bg-white-elevated hover:text-text-primary"
      }`}
      title={btnTitle}
    >
      {children}
    </button>
  );
}

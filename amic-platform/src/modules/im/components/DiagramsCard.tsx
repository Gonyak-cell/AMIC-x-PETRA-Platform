import { useState, useCallback, useRef } from "react";
import {
  GitFork,
  Network,
  ArrowRightLeft,
  Workflow,
  Plus,
  Pencil,
  Trash2,
  X,
} from "lucide-react";
import { toast } from "sonner";
import { Card, Button } from "@/components/ui";
import {
  ExcalidrawEditor,
  buildShareholdingDiagram,
  buildOrgChartDiagram,
  buildDealStructureDiagram,
  buildValueChainDiagram,
} from "@/components/diagrams";
import type {
  Diagram,
  DiagramListItem,
  DiagramType,
  ExcalidrawData,
} from "@/components/diagrams/types";
import { imApi } from "@/api/imClient";
import {
  useCreateDiagram,
  useUpdateDiagram,
  useDeleteDiagram,
  useExportDiagramPng,
} from "@/modules/im/hooks/useDiagrams";

// ── Diagram type metadata ───────────────────────────────────

interface DiagramTemplate {
  type: DiagramType;
  label: string;
  description: string;
  icon: typeof GitFork;
  buildSample: () => ExcalidrawData;
}

const DIAGRAM_TEMPLATES: DiagramTemplate[] = [
  {
    type: "shareholding",
    label: "주주관계도",
    description: "주주 간 지분 관계 시각화",
    icon: GitFork,
    buildSample: () =>
      buildShareholdingDiagram({
        entities: [
          { id: "holdco", label: "지주회사", type: "company", level: 0 },
          { id: "sub1", label: "자회사 A", type: "company", level: 1 },
          { id: "sub2", label: "자회사 B", type: "company", level: 1 },
          { id: "ceo", label: "대표이사", type: "person", level: 0 },
        ],
        stakes: [
          { from: "holdco", to: "sub1", pct: 80, label: "80%" },
          { from: "holdco", to: "sub2", pct: 51, label: "51%" },
          { from: "ceo", to: "holdco", pct: 35, label: "35%" },
        ],
      }),
  },
  {
    type: "org_chart",
    label: "조직도",
    description: "조직 구조 및 계층 표시",
    icon: Network,
    buildSample: () =>
      buildOrgChartDiagram({
        nodes: [
          { id: "ceo", label: "대표이사", level: 0, title: "CEO" },
          { id: "cfo", label: "재무이사", level: 1, title: "CFO" },
          { id: "coo", label: "운영이사", level: 1, title: "COO" },
          { id: "cto", label: "기술이사", level: 1, title: "CTO" },
        ],
        edges: [
          { from: "ceo", to: "cfo" },
          { from: "ceo", to: "coo" },
          { from: "ceo", to: "cto" },
        ],
      }),
  },
  {
    type: "deal_structure",
    label: "거래구조도",
    description: "거래 참여자 간 자금/지분 흐름",
    icon: ArrowRightLeft,
    buildSample: () =>
      buildDealStructureDiagram({
        title: "거래구조 개요",
        entities: [
          { id: "seller", label: "매도자", type: "seller" },
          { id: "buyer", label: "매수자", type: "buyer" },
          { id: "target", label: "대상회사", type: "target" },
          { id: "spv", label: "SPC", type: "spv" },
        ],
        flows: [
          { from: "buyer", to: "spv", label: "출자", type: "cash" },
          { from: "spv", to: "seller", label: "매매대금", type: "cash" },
          { from: "seller", to: "spv", label: "지분 양도", type: "shares" },
          { from: "spv", to: "target", label: "경영권", type: "info" },
        ],
      }),
  },
  {
    type: "value_chain",
    label: "가치사슬도",
    description: "산업 가치사슬 단계별 분석",
    icon: Workflow,
    buildSample: () =>
      buildValueChainDiagram({
        title: "산업 가치사슬",
        stages: [
          { id: "r1", label: "원재료", activities: ["조달", "품질관리"] },
          { id: "r2", label: "제조", activities: ["생산", "조립", "검수"] },
          { id: "r3", label: "유통", activities: ["물류", "재고관리"] },
          { id: "r4", label: "판매", activities: ["B2B", "B2C", "온라인"] },
        ],
      }),
  },
];

// ── Component ───────────────────────────────────────────────

interface DiagramsCardProps {
  documentId: string;
  diagrams: DiagramListItem[];
  isLoading?: boolean;
}

export function DiagramsCard({
  documentId,
  diagrams,
  isLoading,
}: DiagramsCardProps) {
  const [editingDiagram, setEditingDiagram] = useState<{
    id: string | null;
    type: DiagramType;
    title: string;
    data: ExcalidrawData;
  } | null>(null);

  // #4: Loading state for fetching full diagram data
  const [loadingDiagramId, setLoadingDiagramId] = useState<string | null>(null);

  // #8: Delete confirmation state (inline confirm instead of window.confirm)
  const [deletingId, setDeletingId] = useState<string | null>(null);

  // #5: Guard to prevent duplicate create calls from debounced onChange
  const isCreatingRef = useRef(false);

  const createDiagram = useCreateDiagram(documentId);
  const updateDiagram = useUpdateDiagram(documentId);
  const deleteDiagram = useDeleteDiagram(documentId);
  const exportPng = useExportDiagramPng(documentId);

  const handleCreateFromTemplate = useCallback((template: DiagramTemplate) => {
    const sampleData = template.buildSample();
    setEditingDiagram({
      id: null,
      type: template.type,
      title: template.label,
      data: sampleData,
    });
  }, []);

  // #4: Fetch full diagram (with excalidraw_data) before opening editor
  const handleEditExisting = useCallback(
    async (diagram: DiagramListItem) => {
      setLoadingDiagramId(diagram.id);
      try {
        const { data } = await imApi.get<Diagram>(
          `/documents/${documentId}/diagrams/${diagram.id}`,
        );
        if (!data.excalidraw_data) {
          toast.error("다이어그램 데이터가 없습니다.");
          return;
        }
        setEditingDiagram({
          id: data.id,
          type: data.diagram_type,
          title: data.title,
          data: data.excalidraw_data,
        });
      } catch {
        toast.error("다이어그램을 불러오지 못했습니다.");
      } finally {
        setLoadingDiagramId(null);
      }
    },
    [documentId],
  );

  // #5: Guard duplicate create with isCreatingRef
  const handleSave = useCallback(
    async (data: ExcalidrawData) => {
      if (!editingDiagram) return;

      if (editingDiagram.id) {
        await updateDiagram.mutateAsync({
          diagramId: editingDiagram.id,
          excalidraw_data: data,
        });
      } else {
        if (isCreatingRef.current) return;
        isCreatingRef.current = true;
        try {
          const created = await createDiagram.mutateAsync({
            diagram_type: editingDiagram.type,
            title: editingDiagram.title,
            excalidraw_data: data,
          });
          setEditingDiagram((prev) =>
            prev ? { ...prev, id: created.id, data } : null,
          );
        } finally {
          isCreatingRef.current = false;
        }
      }
    },
    [editingDiagram, createDiagram, updateDiagram],
  );

  const handleExportPng = useCallback(
    async (blob: Blob) => {
      if (!editingDiagram?.id) {
        toast.info("PNG 내보내기 전에 다이어그램을 먼저 저장하세요.");
        return;
      }
      try {
        await exportPng.mutateAsync({
          diagramId: editingDiagram.id,
          pngBlob: blob,
        });
      } catch {
        // Error handled by mutation hook onError
      }
    },
    [editingDiagram, exportPng],
  );

  // #8: State-based delete confirmation
  const handleDeleteRequest = useCallback((diagramId: string) => {
    setDeletingId(diagramId);
  }, []);

  const handleDeleteConfirm = useCallback(async () => {
    if (!deletingId) return;
    try {
      await deleteDiagram.mutateAsync(deletingId);
    } catch {
      // Error handled by mutation hook onError
    } finally {
      setDeletingId(null);
    }
  }, [deletingId, deleteDiagram]);

  const handleDeleteCancel = useCallback(() => {
    setDeletingId(null);
  }, []);

  const handleCloseEditor = useCallback(() => {
    setEditingDiagram(null);
  }, []);

  // Available templates that don't already have a diagram
  const existingTypes = new Set(diagrams.map((d) => d.diagram_type));
  const availableTemplates = DIAGRAM_TEMPLATES.filter(
    (t) => !existingTypes.has(t.type),
  );

  if (isLoading) return null;

  return (
    <>
      <Card title="Diagrams" headerBar>
        {/* Existing diagrams */}
        {diagrams.length > 0 && (
          <div className="space-y-2 mb-4">
            {diagrams.map((diagram) => (
              <div
                key={diagram.id}
                className="flex items-center justify-between p-3 rounded-lg bg-bg-cool"
              >
                <div className="flex items-center gap-3">
                  <DiagramIcon type={diagram.diagram_type} />
                  <div>
                    <span className="text-sm font-medium text-text-dark">
                      {diagram.title}
                    </span>
                    <span className="text-xs text-text-secondary ml-2">
                      {DIAGRAM_TYPE_LABEL[diagram.diagram_type] ??
                        diagram.diagram_type}
                    </span>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Button
                    variant="ghost"
                    size="sm"
                    icon={Pencil}
                    onClick={() => handleEditExisting(diagram)}
                    disabled={loadingDiagramId === diagram.id}
                  >
                    {loadingDiagramId === diagram.id ? "Loading..." : "Edit"}
                  </Button>
                  {deletingId === diagram.id ? (
                    <div className="flex items-center gap-1">
                      <Button
                        variant="danger"
                        size="sm"
                        onClick={handleDeleteConfirm}
                      >
                        삭제
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={handleDeleteCancel}
                      >
                        취소
                      </Button>
                    </div>
                  ) : (
                    <Button
                      variant="ghost"
                      size="sm"
                      icon={Trash2}
                      onClick={() => handleDeleteRequest(diagram.id)}
                      className="text-negative hover:text-negative"
                    />
                  )}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Create from template */}
        {availableTemplates.length > 0 && (
          <div>
            <p className="text-xs text-text-secondary mb-2">
              Create from template
            </p>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {availableTemplates.map((template) => (
                <button
                  key={template.type}
                  type="button"
                  aria-label={`${template.label} 다이어그램 생성`}
                  onClick={() => handleCreateFromTemplate(template)}
                  className="flex flex-col items-center gap-2 p-4 rounded-lg border border-gray-border hover:border-accent hover:bg-bg-cool transition-colors text-center group"
                >
                  <template.icon className="h-6 w-6 text-text-secondary group-hover:text-accent transition-colors" />
                  <span className="text-sm font-medium text-text-dark">
                    {template.label}
                  </span>
                  <span className="text-xs text-text-secondary">
                    {template.description}
                  </span>
                  <Plus className="h-4 w-4 text-text-secondary group-hover:text-accent" />
                </button>
              ))}
            </div>
          </div>
        )}

        {diagrams.length === 0 && availableTemplates.length === 0 && (
          <p className="text-sm text-text-secondary text-center py-4">
            No diagram templates available.
          </p>
        )}
      </Card>

      {/* Inline Editor (full-width below diagrams card) */}
      {editingDiagram && (
        <Card title={`Edit: ${editingDiagram.title}`} headerBar>
          <div className="mb-3 flex items-center justify-between">
            <p className="text-xs text-text-secondary">
              Drag, resize, and edit diagram elements. Changes auto-save when
              connected to backend.
            </p>
            <Button
              variant="ghost"
              size="sm"
              icon={X}
              onClick={handleCloseEditor}
            >
              Close Editor
            </Button>
          </div>
          <ExcalidrawEditor
            initialData={editingDiagram.data}
            onChange={handleSave}
            onExportPng={handleExportPng}
            className="min-h-[600px]"
          />
        </Card>
      )}
    </>
  );
}

// ── Helpers ─────────────────────────────────────────────────

const DIAGRAM_TYPE_LABEL: Record<string, string> = {
  shareholding: "주주관계도",
  org_chart: "조직도",
  deal_structure: "거래구조도",
  value_chain: "가치사슬도",
  custom: "커스텀",
};

function DiagramIcon({ type }: { type: DiagramType }) {
  const iconMap: Record<DiagramType, typeof GitFork> = {
    shareholding: GitFork,
    org_chart: Network,
    deal_structure: ArrowRightLeft,
    value_chain: Workflow,
    custom: Workflow,
  };
  const Icon = iconMap[type] ?? Workflow;
  return <Icon className="h-5 w-5 text-accent" />;
}

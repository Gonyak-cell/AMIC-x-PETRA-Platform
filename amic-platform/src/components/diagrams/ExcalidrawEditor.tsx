import { lazy, Suspense, useCallback, useRef, useState } from "react";
import { Download, Save } from "lucide-react";
import { toast } from "sonner";
import { exportToBlob } from "@excalidraw/excalidraw";
import type {
  ExcalidrawImperativeAPI,
  ExcalidrawInitialDataState,
} from "@excalidraw/excalidraw/types";
import { Button, Skeleton } from "@/components/ui";
import { EXCALIDRAW_BG } from "./amic-palette";
import type { ExcalidrawData } from "./types";

const Excalidraw = lazy(() =>
  import("@excalidraw/excalidraw").then((mod) => ({
    default: mod.Excalidraw,
  })),
);

interface ExcalidrawEditorProps {
  initialData?: ExcalidrawData | null;
  readOnly?: boolean;
  onChange?: (data: ExcalidrawData) => void | Promise<void>;
  onExportPng?: (blob: Blob) => void;
  className?: string;
}

export function ExcalidrawEditor({
  initialData,
  readOnly = false,
  onChange,
  onExportPng,
  className = "",
}: ExcalidrawEditorProps) {
  const excalidrawApiRef = useRef<ExcalidrawImperativeAPI | null>(null);
  const debounceTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [isExporting, setIsExporting] = useState(false);

  const handleChange = useCallback(
    (elements: readonly unknown[], appState: unknown) => {
      if (readOnly || !onChange) return;

      const state = appState as Record<string, unknown>;
      if (debounceTimer.current) clearTimeout(debounceTimer.current);
      debounceTimer.current = setTimeout(() => {
        const data: ExcalidrawData = {
          type: "excalidraw",
          version: 2,
          source: "amic-platform",
          elements: elements as unknown as ExcalidrawData["elements"],
          appState: {
            viewBackgroundColor: state.viewBackgroundColor ?? EXCALIDRAW_BG,
            gridSize: state.gridSize ?? null,
          },
          files: {},
        };
        Promise.resolve(onChange(data)).catch(() => {});
      }, 500);
    },
    [onChange, readOnly],
  );

  const handleExportPng = useCallback(async () => {
    const api = excalidrawApiRef.current;
    if (!api) return;

    setIsExporting(true);
    try {
      const elements = api.getSceneElements();
      const appState = api.getAppState();
      const files = api.getFiles();

      const blob = await exportToBlob({
        elements,
        appState: { ...appState, exportWithDarkMode: false },
        files,
        mimeType: "image/png",
        exportPadding: 20,
        getDimensions: () => ({ width: 1920, height: 1080, scale: 2 }),
      });

      if (onExportPng) {
        onExportPng(blob);
        toast.success("PNG exported");
      } else {
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.download = "diagram.png";
        link.click();
        URL.revokeObjectURL(url);
        toast.success("PNG downloaded");
      }
    } catch {
      toast.error("PNG export failed");
    } finally {
      setIsExporting(false);
    }
  }, [onExportPng]);

  const handleManualSave = useCallback(async () => {
    const api = excalidrawApiRef.current;
    if (!api || !onChange) return;

    setIsSaving(true);
    const elements = api.getSceneElements();
    const appState = api.getAppState();

    const data: ExcalidrawData = {
      type: "excalidraw",
      version: 2,
      source: "amic-platform",
      elements: elements as unknown as ExcalidrawData["elements"],
      appState: {
        viewBackgroundColor: appState.viewBackgroundColor ?? EXCALIDRAW_BG,
        gridSize: appState.gridSize ?? null,
      },
      files: {},
    };
    try {
      await onChange(data);
      toast.success("Diagram saved");
    } catch {
      // Error toast is handled by the mutation hook's onError
    } finally {
      setIsSaving(false);
    }
  }, [onChange]);

  return (
    <div className={`flex flex-col ${className}`}>
      {!readOnly && (
        <div className="flex items-center gap-2 mb-2">
          <Button
            variant="primary"
            size="sm"
            icon={Save}
            onClick={handleManualSave}
            loading={isSaving}
            disabled={!onChange}
          >
            Save
          </Button>
          <Button
            variant="secondary"
            size="sm"
            icon={Download}
            onClick={handleExportPng}
            loading={isExporting}
          >
            Export PNG
          </Button>
        </div>
      )}

      <div className="flex-1 min-h-[500px] border border-gray-border rounded-lg overflow-hidden">
        <Suspense
          fallback={
            <div
              className="flex items-center justify-center h-[500px]"
              role="status"
            >
              <div className="space-y-4 w-64">
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-4 w-48" />
                <Skeleton className="h-4 w-56" />
                <p className="text-sm text-text-secondary text-center mt-4">
                  Loading diagram editor...
                </p>
              </div>
            </div>
          }
        >
          <Excalidraw
            initialData={
              (initialData ??
                undefined) as unknown as ExcalidrawInitialDataState
            }
            excalidrawAPI={(api) => {
              excalidrawApiRef.current = api;
            }}
            onChange={handleChange}
            viewModeEnabled={readOnly}
            langCode="ko-KR"
            theme="light"
            UIOptions={{
              canvasActions: {
                saveToActiveFile: false,
                loadScene: false,
                export: false,
              },
            }}
          />
        </Suspense>
      </div>
    </div>
  );
}

import { lazy, Suspense } from "react";
import { Skeleton } from "@/components/ui";
import type { ExcalidrawInitialDataState } from "@excalidraw/excalidraw/types";
import type { ExcalidrawData } from "./types";

const Excalidraw = lazy(() =>
  import("@excalidraw/excalidraw").then((mod) => ({
    default: mod.Excalidraw,
  })),
);

interface ExcalidrawViewerProps {
  data: ExcalidrawData;
  className?: string;
  height?: string;
}

export function ExcalidrawViewer({
  data,
  className = "",
  height = "400px",
}: ExcalidrawViewerProps) {
  return (
    <div
      className={`border border-gray-border rounded-lg overflow-hidden ${className}`}
      style={{ height }}
    >
      <Suspense
        fallback={
          <div
            className="flex items-center justify-center h-full"
            role="status"
          >
            <Skeleton className="h-4 w-48" />
          </div>
        }
      >
        <Excalidraw
          initialData={data as unknown as ExcalidrawInitialDataState}
          viewModeEnabled
          langCode="ko-KR"
          theme="light"
          UIOptions={{
            canvasActions: {
              saveToActiveFile: false,
              loadScene: false,
              export: false,
              changeViewBackgroundColor: false,
            },
          }}
        />
      </Suspense>
    </div>
  );
}

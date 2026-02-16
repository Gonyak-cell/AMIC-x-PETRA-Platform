import { lazy, Suspense } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import { Spinner } from "@/components/ui";
import { ImErrorBoundary } from "@/modules/im/components/ImErrorBoundary";
import DocumentListPage from "@/modules/im/pages/DocumentListPage";

const CreateDocumentPage = lazy(() => import("@/modules/im/pages/CreateDocumentPage"));
const DocumentDetailPage = lazy(() => import("@/modules/im/pages/DocumentDetailPage"));
const TemplatesPage = lazy(() => import("@/modules/im/pages/TemplatesPage"));
const SamplePage = lazy(() => import("@/modules/im/pages/SamplePage"));
const GallerySamplePage = lazy(() => import("@/modules/im/pages/GallerySamplePage"));

export default function ImRoutes() {
  return (
    <ImErrorBoundary>
      <Suspense fallback={<Spinner />}>
        <Routes>
          <Route index element={<DocumentListPage />} />
          <Route path="new" element={<CreateDocumentPage />} />
          <Route path="documents/:documentId" element={<DocumentDetailPage />} />
          <Route path="templates" element={<TemplatesPage />} />
          {import.meta.env.DEV && (
            <>
              <Route path="sample" element={<SamplePage />} />
              <Route path="gallery" element={<GallerySamplePage />} />
            </>
          )}
          <Route path="*" element={<Navigate to="/im" replace />} />
        </Routes>
      </Suspense>
    </ImErrorBoundary>
  );
}

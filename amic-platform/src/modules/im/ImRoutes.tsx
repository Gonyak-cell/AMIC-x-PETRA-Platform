import { Routes, Route, Navigate } from "react-router-dom";
import { ImErrorBoundary } from "@/modules/im/components/ImErrorBoundary";
import DocumentListPage from "@/modules/im/pages/DocumentListPage";
import CreateDocumentPage from "@/modules/im/pages/CreateDocumentPage";
import DocumentDetailPage from "@/modules/im/pages/DocumentDetailPage";
import TemplatesPage from "@/modules/im/pages/TemplatesPage";
import SamplePage from "@/modules/im/pages/SamplePage";
import GallerySamplePage from "@/modules/im/pages/GallerySamplePage";

export default function ImRoutes() {
  return (
    <ImErrorBoundary>
      <Routes>
        <Route index element={<DocumentListPage />} />
        <Route path="new" element={<CreateDocumentPage />} />
        <Route path="documents/:documentId" element={<DocumentDetailPage />} />
        <Route path="templates" element={<TemplatesPage />} />
        <Route path="sample" element={<SamplePage />} />
        <Route path="gallery" element={<GallerySamplePage />} />
        <Route path="*" element={<Navigate to="/im" replace />} />
      </Routes>
    </ImErrorBoundary>
  );
}

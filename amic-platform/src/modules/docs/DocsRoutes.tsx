import { lazy, Suspense } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import { Spinner } from "@/components/ui";
import { DocsErrorBoundary } from "@/modules/docs/components/DocsErrorBoundary";
import StudioHomePage from "@/modules/docs/pages/StudioHomePage";
import CategoryDocumentsPage from "@/modules/docs/pages/CategoryDocumentsPage";

const CreateDocumentPage = lazy(
  () => import("@/modules/docs/pages/CreateDocumentPage"),
);
const CreateLegalDocumentPage = lazy(
  () => import("@/modules/docs/pages/CreateLegalDocumentPage"),
);
const CreateLDDReportPage = lazy(
  () => import("@/modules/docs/pages/CreateLDDReportPage"),
);
const DDReportListPage = lazy(
  () => import("@/modules/docs/pages/DDReportListPage"),
);
const ChecklistDetailPage = lazy(
  () => import("@/modules/docs/pages/ChecklistDetailPage"),
);
const DocumentDetailPage = lazy(
  () => import("@/modules/docs/pages/DocumentDetailPage"),
);
const TemplatesPage = lazy(() => import("@/modules/docs/pages/TemplatesPage"));
const ContractGeneratorPage = lazy(
  () => import("@/modules/docs/pages/ContractGeneratorPage"),
);
const SpaAnalysisPage = lazy(
  () => import("@/modules/docs/pages/SpaAnalysisPage"),
);

export default function DocsRoutes() {
  return (
    <DocsErrorBoundary>
      <Suspense fallback={<Spinner />}>
        <Routes>
          <Route index element={<StudioHomePage />} />
          {/* Category pages */}
          <Route
            path="marketing"
            element={<CategoryDocumentsPage category="marketing" />}
          />
          <Route
            path="legal"
            element={<CategoryDocumentsPage category="legal" />}
          />
          <Route
            path="dd"
            element={<CategoryDocumentsPage category="due_diligence" />}
          />
          <Route path="dd/fdd" element={<DDReportListPage type="fdd" />} />
          <Route path="dd/ldd" element={<DDReportListPage type="ldd" />} />
          <Route
            path="checklists"
            element={<CategoryDocumentsPage category="checklists" />}
          />
          {/* Document creation */}
          <Route path="new" element={<CreateDocumentPage />} />
          <Route
            path="new/teaser"
            element={<CreateDocumentPage defaultType="teaser" />}
          />
          <Route
            path="new/im"
            element={<CreateDocumentPage defaultType="im" />}
          />
          <Route path="legal/new" element={<CreateLegalDocumentPage />} />
          <Route
            path="legal/mou"
            element={<CreateLegalDocumentPage defaultType="MOU" />}
          />
          <Route path="legal/contracts" element={<CreateLegalDocumentPage />} />
          <Route path="legal/generate" element={<ContractGeneratorPage />} />
          <Route path="legal/spa-analysis" element={<SpaAnalysisPage />} />
          <Route path="ldd/new" element={<CreateLDDReportPage />} />
          {/* Checklist detail pages */}
          <Route
            path="checklists/closing"
            element={<ChecklistDetailPage type="closing" />}
          />
          <Route
            path="checklists/timeline"
            element={<ChecklistDetailPage type="timeline" />}
          />
          {/* Document detail */}
          <Route
            path="documents/:documentId"
            element={<DocumentDetailPage />}
          />
          <Route path="templates" element={<TemplatesPage />} />
          <Route path="*" element={<Navigate to="/docs" replace />} />
        </Routes>
      </Suspense>
    </DocsErrorBoundary>
  );
}

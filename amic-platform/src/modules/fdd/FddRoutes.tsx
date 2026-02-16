import { lazy, Suspense } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import { Spinner } from "@/components/ui";
import DealListPage from "./pages/DealListPage";

const DealSetupWizardPage = lazy(() => import("./pages/DealSetupWizardPage"));
const DealWorkspacePage = lazy(() => import("./pages/DealWorkspacePage"));
const SamplePage = lazy(() => import("./pages/SamplePage"));
const GallerySamplePage = lazy(() => import("./pages/GallerySamplePage"));

export default function FddRoutes() {
  return (
    <Suspense fallback={<Spinner />}>
      <Routes>
        <Route path="deals" element={<DealListPage />} />
        <Route path="deals/new" element={<DealSetupWizardPage />} />
        <Route path="deals/:dealId/*" element={<DealWorkspacePage />} />
        <Route path="sample" element={<SamplePage />} />
        <Route path="gallery" element={<GallerySamplePage />} />
        <Route index element={<Navigate to="deals" replace />} />
      </Routes>
    </Suspense>
  );
}

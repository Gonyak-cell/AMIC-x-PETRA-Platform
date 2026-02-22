import { lazy, Suspense } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import { Spinner } from "@/components/ui";
import DealListPage from "./pages/DealListPage";

const DealSetupWizardPage = lazy(() => import("./pages/DealSetupWizardPage"));
const DealWorkspacePage = lazy(() => import("./pages/DealWorkspacePage"));

export default function FddRoutes() {
  return (
    <Suspense fallback={<Spinner />}>
      <Routes>
        <Route path="deals" element={<DealListPage />} />
        <Route path="deals/new" element={<DealSetupWizardPage />} />
        <Route path="deals/:dealId/*" element={<DealWorkspacePage />} />
        <Route index element={<Navigate to="deals" replace />} />
      </Routes>
    </Suspense>
  );
}

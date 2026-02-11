import { Routes, Route, Navigate } from "react-router-dom";
import DealListPage from "./pages/DealListPage";
import DealSetupWizardPage from "./pages/DealSetupWizardPage";
import DealWorkspacePage from "./pages/DealWorkspacePage";
import SamplePage from "./pages/SamplePage";
import GallerySamplePage from "./pages/GallerySamplePage";

export default function FddRoutes() {
  return (
    <Routes>
      <Route path="deals" element={<DealListPage />} />
      <Route path="deals/new" element={<DealSetupWizardPage />} />
      <Route path="deals/:dealId/*" element={<DealWorkspacePage />} />
      <Route path="sample" element={<SamplePage />} />
      <Route path="gallery" element={<GallerySamplePage />} />
      <Route index element={<Navigate to="deals" replace />} />
    </Routes>
  );
}

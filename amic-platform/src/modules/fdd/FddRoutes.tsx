import { Routes, Route, Navigate } from "react-router-dom";
import DealListPage from "./pages/DealListPage";
import DealSetupWizardPage from "./pages/DealSetupWizardPage";
import DealWorkspacePage from "./pages/DealWorkspacePage";

export default function FddRoutes() {
  return (
    <Routes>
      <Route path="deals" element={<DealListPage />} />
      <Route path="deals/new" element={<DealSetupWizardPage />} />
      <Route path="deals/:dealId/*" element={<DealWorkspacePage />} />
      <Route index element={<Navigate to="deals" replace />} />
    </Routes>
  );
}

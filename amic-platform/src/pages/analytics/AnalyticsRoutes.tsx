import { Routes, Route } from "react-router-dom";
import AnalyticsPage from "./AnalyticsPage";

export default function AnalyticsRoutes() {
  return (
    <Routes>
      <Route index element={<AnalyticsPage />} />
    </Routes>
  );
}

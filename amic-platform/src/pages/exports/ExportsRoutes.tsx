import { Routes, Route } from "react-router-dom";
import ExportsPage from "./ExportsPage";

export default function ExportsRoutes() {
  return (
    <Routes>
      <Route index element={<ExportsPage />} />
    </Routes>
  );
}

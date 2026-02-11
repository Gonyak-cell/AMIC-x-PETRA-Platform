import { Routes, Route } from "react-router-dom";
import HelpPage from "./HelpPage";

export default function HelpRoutes() {
  return (
    <Routes>
      <Route index element={<HelpPage />} />
    </Routes>
  );
}

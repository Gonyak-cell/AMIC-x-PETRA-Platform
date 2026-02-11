import { Routes, Route } from "react-router-dom";
import CalendarPage from "./CalendarPage";

export default function CalendarRoutes() {
  return (
    <Routes>
      <Route index element={<CalendarPage />} />
    </Routes>
  );
}

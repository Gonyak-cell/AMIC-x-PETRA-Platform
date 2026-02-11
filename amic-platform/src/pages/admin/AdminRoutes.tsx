import { Routes, Route, Navigate } from "react-router-dom";
import UserManagementPage from "./UserManagementPage";
import ActivityLogPage from "./ActivityLogPage";

export default function AdminRoutes() {
  return (
    <Routes>
      <Route path="users" element={<UserManagementPage />} />
      <Route path="activity" element={<ActivityLogPage />} />
      <Route index element={<Navigate to="users" replace />} />
    </Routes>
  );
}

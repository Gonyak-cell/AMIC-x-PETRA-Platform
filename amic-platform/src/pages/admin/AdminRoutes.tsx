import { Routes, Route, Navigate } from "react-router-dom";
import UserManagementPage from "./UserManagementPage";
import ActivityLogPage from "./ActivityLogPage";
import AdminSettingsPage from "./AdminSettingsPage";

export default function AdminRoutes() {
  return (
    <Routes>
      <Route path="users" element={<UserManagementPage />} />
      <Route path="activity" element={<ActivityLogPage />} />
      <Route path="settings" element={<AdminSettingsPage />} />
      <Route index element={<Navigate to="users" replace />} />
    </Routes>
  );
}

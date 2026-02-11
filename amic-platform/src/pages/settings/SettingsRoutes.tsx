import { Routes, Route, Navigate } from "react-router-dom";
import ProfilePage from "./ProfilePage";

export default function SettingsRoutes() {
  return (
    <Routes>
      <Route path="profile" element={<ProfilePage />} />
      <Route index element={<Navigate to="profile" replace />} />
    </Routes>
  );
}

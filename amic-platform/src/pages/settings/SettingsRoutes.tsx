import { Routes, Route, Navigate } from "react-router-dom";
import ProfilePage from "./ProfilePage";
import WebhooksPage from "./WebhooksPage";

export default function SettingsRoutes() {
  return (
    <Routes>
      <Route path="profile" element={<ProfilePage />} />
      <Route path="webhooks" element={<WebhooksPage />} />
      <Route index element={<Navigate to="profile" replace />} />
    </Routes>
  );
}

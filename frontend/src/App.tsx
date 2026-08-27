import { Navigate, Route, Routes } from "react-router-dom";
import { GuestRoute, ProtectedRoute } from "./components/Guards";
import { Shell } from "./components/Shell";
import { DashboardPage } from "./pages/Dashboard";
import { LevelPage } from "./pages/Level";
import { LoginPage } from "./pages/Login";
import { RegisterPage } from "./pages/Register";
import { VictoryPage } from "./pages/Victory";

export function App() {
  return (
    <Routes>
      <Route element={<GuestRoute />}>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
      </Route>
      <Route element={<ProtectedRoute />}>
        <Route element={<Shell />}>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/nivel/:id" element={<LevelPage />} />
          <Route path="/victoria" element={<VictoryPage />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

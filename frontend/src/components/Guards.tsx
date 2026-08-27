import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export function ProtectedRoute() {
  const { user, loading } = useAuth();
  if (loading) return <div className="page-center muted">Cargando sesión…</div>;
  if (!user) return <Navigate to="/login" replace />;
  return <Outlet />;
}

export function GuestRoute() {
  const { user, loading } = useAuth();
  if (loading) return <div className="page-center muted">Cargando sesión…</div>;
  if (user) return <Navigate to="/" replace />;
  return <Outlet />;
}

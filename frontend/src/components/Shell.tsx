import { Link, NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export function Shell() {
  const { user, logout } = useAuth();

  return (
    <div className="app-shell">
      <header className="topbar">
        <Link to="/" className="brand">
          <span className="brand-mark">pre</span>CTF UCC
        </Link>
        {user && (
          <div className="topbar-right">
            <span className="chip">{user.full_name}</span>
            <span className="chip score">Puntos {user.score}</span>
            <NavLink to="/" className="nav-link">
              Dashboard
            </NavLink>
            <button type="button" className="linkish" onClick={logout}>
              Salir
            </button>
          </div>
        )}
      </header>
      <main className="content">
        <Outlet />
      </main>
    </div>
  );
}

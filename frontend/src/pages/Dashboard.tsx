import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, type Dashboard, type LevelCard } from "../api/client";
import { useAuth } from "../context/AuthContext";

function statusLabel(status: LevelCard["status"]): string {
  if (status === "completed") return "Completado";
  if (status === "available") return "Disponible";
  return "Bloqueado";
}

export function DashboardPage() {
  const { user, refresh } = useAuth();
  const [data, setData] = useState<Dashboard | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    void refresh();
    api
      .dashboard()
      .then(setData)
      .catch((err) => setError(err instanceof Error ? err.message : "No se pudo cargar."));
  }, [refresh]);

  if (error) return <p className="alert error">{error}</p>;
  if (!data) return <p className="muted">Cargando dashboard…</p>;

  const percent = data.total === 0 ? 0 : Math.round((data.completed / data.total) * 100);

  return (
    <div className="dashboard">
      <section className="panel intro">
        <div>
          <p className="eyebrow">Progreso de {user?.full_name}</p>
          <h1>Ruta de 8 niveles</h1>
          <p className="muted">
            Debes superar cada vector en orden. Las pistas restan puntos. Al completar el
            último nivel se emite tu token de acceso al CTF práctico.
          </p>
        </div>
        <div className="progress-box">
          <strong>
            {data.completed}/{data.total}
          </strong>
          <span>niveles</span>
          <div className="bar">
            <i style={{ width: `${percent}%` }} />
          </div>
        </div>
      </section>

      {data.access_token && (
        <Link to="/victoria" className="banner success">
          Entrenamiento completado. Abre tu certificado y token de acceso.
        </Link>
      )}

      <div className="level-grid">
        {data.levels.map((level) => {
          const inner = (
            <>
              <div className="level-index">N{level.order_index}</div>
              <h3>{level.title}</h3>
              <p className="vector">{level.vector_name}</p>
              <p className="meta">
                {level.points} pts · pista −{level.hint_cost}
              </p>
              <span className={`tag ${level.status}`}>{statusLabel(level.status)}</span>
            </>
          );
          if (level.status === "locked") {
            return (
              <article key={level.id} className="level-card locked">
                {inner}
              </article>
            );
          }
          return (
            <Link key={level.id} to={`/nivel/${level.id}`} className={`level-card ${level.status}`}>
              {inner}
            </Link>
          );
        })}
      </div>
    </div>
  );
}

import { FormEvent, useEffect, useState } from "react";
import { Link, Navigate, useNavigate, useParams } from "react-router-dom";
import { api, type LevelCard, type SubmitResult } from "../api/client";
import { useAuth } from "../context/AuthContext";

export function LevelPage() {
  const { id } = useParams();
  const levelId = Number(id);
  const navigate = useNavigate();
  const { refresh } = useAuth();
  const [level, setLevel] = useState<LevelCard | null>(null);
  const [flag, setFlag] = useState("");
  const [hint, setHint] = useState("");
  const [message, setMessage] = useState<SubmitResult | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api
      .dashboard()
      .then((data) => {
        const found = data.levels.find((item) => item.id === levelId) ?? null;
        setLevel(found);
        if (found?.hint_used) {
          api.hint(levelId).then((res) => setHint(res.hint)).catch(() => undefined);
        }
      })
      .catch((err) => setError(err instanceof Error ? err.message : "No se pudo cargar el nivel."));
  }, [levelId]);

  if (!Number.isFinite(levelId)) return <Navigate to="/" replace />;
  if (error) return <p className="alert error">{error}</p>;
  if (!level) return <p className="muted">Cargando nivel…</p>;
  if (level.status === "locked") return <Navigate to="/" replace />;

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const result = await api.submit(levelId, flag);
      setMessage(result);
      await refresh();
      if (result.ok && result.token) {
        navigate("/victoria", { replace: true });
        return;
      }
      const data = await api.dashboard();
      setLevel(data.levels.find((item) => item.id === levelId) ?? null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo validar.");
    } finally {
      setBusy(false);
    }
  }

  async function onHint() {
    setBusy(true);
    setError("");
    try {
      const result = await api.hint(levelId);
      setHint(result.hint);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo mostrar la pista.");
    } finally {
      setBusy(false);
    }
  }

  const tone = message?.ok ? "success" : message ? "error" : "";

  return (
    <article className="level-view">
      <Link to="/" className="back">
        ← Dashboard
      </Link>
      <header className="panel">
        <p className="eyebrow">
          Nivel {level.order_index} · {level.points} pts
        </p>
        <h1>{level.title}</h1>
        <p className="vector">{level.vector_name}</p>
        <p className="muted">Referencia en el laboratorio: {level.lab_endpoint}</p>
        <p>{level.description}</p>
      </header>

      <form className="panel" onSubmit={onSubmit}>
        <h2>Validar flag</h2>
        <label>
          Flag
          <input
            value={flag}
            onChange={(e) => setFlag(e.target.value)}
            placeholder="FLAG{…}"
            autoComplete="off"
            required
          />
        </label>
        {message && <p className={`alert ${tone}`}>{message.message}</p>}
        {error && <p className="alert error">{error}</p>}
        <div className="actions">
          <button type="submit" disabled={busy || level.status === "completed"}>
            {level.status === "completed" ? "Nivel completado" : busy ? "Validando…" : "Enviar flag"}
          </button>
          <button type="button" className="secondary" onClick={onHint} disabled={busy}>
            {hint ? "Pista revelada" : `Pedir pista (−${level.hint_cost} pts)`}
          </button>
        </div>
      </form>

      {hint && (
        <aside className="panel hint-box">
          <h2>Pista</h2>
          <p>{hint}</p>
        </aside>
      )}
    </article>
  );
}

import { FormEvent, useEffect, useState } from "react";
import { Link, Navigate, useNavigate, useParams } from "react-router-dom";
import { api, type LabEnvironment, type LevelDetail, type SubmitResult } from "../api/client";
import { LabPanel, LearningMode, useLearningMode } from "../components/LearningMode";
import { useAuth } from "../context/AuthContext";

export function LevelPage() {
  const { id } = useParams();
  const levelId = Number(id);
  const navigate = useNavigate();
  const { refresh } = useAuth();
  const [level, setLevel] = useState<LevelDetail | null>(null);
  const [flag, setFlag] = useState("");
  const [hint, setHint] = useState("");
  const [message, setMessage] = useState<SubmitResult | null>(null);
  const [error, setError] = useState("");
  const [labError, setLabError] = useState("");
  const [busy, setBusy] = useState(false);
  const [labBusy, setLabBusy] = useState(false);
  const [locked, setLocked] = useState(false);
  const [learning, setLearning] = useLearningMode(true);

  useEffect(() => {
    api
      .getLevel(levelId)
      .then((data) => {
        setLevel(data);
        if (data.hint_used) {
          api.hint(levelId).then((res) => setHint(res.hint)).catch(() => undefined);
        }
      })
      .catch((err) => {
        const text = err instanceof Error ? err.message : "No se pudo cargar el nivel.";
        if (text.includes("nivel anterior")) {
          setLocked(true);
          return;
        }
        setError(text);
      });
  }, [levelId]);

  if (!Number.isFinite(levelId)) return <Navigate to="/" replace />;
  if (locked) return <Navigate to="/" replace />;
  if (error) return <p className="alert error">{error}</p>;
  if (!level) return <p className="muted">Cargando nivel…</p>;

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
      const data = await api.getLevel(levelId);
      setLevel(data);
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

  async function onStartLab() {
    setLabBusy(true);
    setLabError("");
    try {
      const env = await api.startEnvironment(levelId);
      setLevel((current) => (current ? { ...current, environment: env } : current));
    } catch (err) {
      setLabError(err instanceof Error ? err.message : "No se pudo iniciar el laboratorio.");
    } finally {
      setLabBusy(false);
    }
  }

  async function onStopLab() {
    setLabBusy(true);
    setLabError("");
    try {
      const env = await api.stopEnvironment(levelId);
      setLevel((current) => (current ? { ...current, environment: env } : current));
    } catch (err) {
      setLabError(err instanceof Error ? err.message : "No se pudo apagar el laboratorio.");
    } finally {
      setLabBusy(false);
    }
  }

  const tone = message?.ok ? "success" : message ? "error" : "";
  const environment: LabEnvironment = level.environment;

  const labPanel = environment.has_lab ? (
    <LabPanel
      environment={environment}
      endpoint={level.lab_endpoint}
      busy={labBusy}
      onStart={() => void onStartLab()}
      onStop={() => void onStopLab()}
    />
  ) : (
    <section className="panel lab-panel">
      <h2>Laboratorio</h2>
      <p className="muted">
        Este nivel se resuelve en la instancia de entrenamiento externa. Referencia: {level.lab_endpoint}
      </p>
    </section>
  );

  const flagForm = (
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
      {labError && <p className="alert error">{labError}</p>}
      <div className="actions">
        <button type="submit" disabled={busy || level.status === "completed"}>
          {level.status === "completed" ? "Nivel completado" : busy ? "Validando…" : "Enviar flag"}
        </button>
        <button type="button" className="secondary" onClick={onHint} disabled={busy}>
          {hint ? "Pista revelada" : `Pedir pista (−${level.hint_cost} pts)`}
        </button>
      </div>
    </form>
  );

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
        <p className="muted">
          Misma instancia IDS. Ruta de este nivel: <code>{level.lab_endpoint}</code>
        </p>
        <p>{level.description}</p>
      </header>

      <LearningMode
        content={level.tutorial_content}
        enabled={learning}
        onToggle={setLearning}
        lab={labPanel}
      >
        {flagForm}
      </LearningMode>

      {hint && (
        <aside className="panel hint-box">
          <h2>Pista</h2>
          <p>{hint}</p>
        </aside>
      )}
    </article>
  );
}

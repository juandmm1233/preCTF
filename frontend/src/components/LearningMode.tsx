import { useEffect, useState, type ReactNode } from "react";
import ReactMarkdown from "react-markdown";
import rehypeSanitize from "rehype-sanitize";
import type { LabEnvironment } from "../api/client";

const LEARNING_KEY = "prectf_learning_mode";

function envLabel(status: LabEnvironment["status"]): string {
  if (status === "running") return "En ejecución";
  if (status === "starting") return "Arrancando";
  if (status === "stopping") return "Apagando";
  if (status === "error") return "Error";
  return "Apagado";
}

type LabPanelProps = {
  environment: LabEnvironment;
  endpoint: string;
  busy: boolean;
  onStart: () => void;
  onStop: () => void;
};

export function LabPanel({ environment, endpoint, busy, onStart, onStop }: LabPanelProps) {
  const running = environment.status === "running" && Boolean(environment.public_url);
  const expiry = environment.expires_at
    ? new Date(environment.expires_at).toLocaleTimeString("es-CO", { hour: "2-digit", minute: "2-digit" })
    : null;

  function labHref(url: string | null): string | undefined {
    if (!url) return undefined;
    if (url.includes("index.php")) return url;
    return `${url.replace(/\/$/, "")}/index.php`;
  }

  return (
    <section className="panel lab-panel">
      <h2>Laboratorio aislado</h2>
      <p className="muted">
        Instancia temporal de este nivel. Endpoint de referencia: <code>{endpoint}</code>
      </p>
      <p className={`lab-status ${environment.status}`}>{envLabel(environment.status)}</p>
      {environment.message && <p className="alert error">{environment.message}</p>}
      {running && (
        <>
          <a
            className="button-link"
            href={labHref(environment.public_url)}
            target="_blank"
            rel="noreferrer"
          >
            Abrir instancia
          </a>
          {expiry && <p className="muted">Caduca alrededor de las {expiry}.</p>}
          <p className="muted">La flag se valida en este panel, no en el laboratorio.</p>
        </>
      )}
      <div className="actions">
        <button type="button" onClick={onStart} disabled={busy || running}>
          {busy && !running ? "Iniciando…" : "Iniciar lección"}
        </button>
        <button type="button" className="secondary" onClick={onStop} disabled={busy || !running}>
          Terminar lección
        </button>
      </div>
    </section>
  );
}

type LearningModeProps = {
  content: string;
  enabled: boolean;
  onToggle: (value: boolean) => void;
  lab: ReactNode;
  children: ReactNode;
};

export function useLearningMode(defaultEnabled = true): [boolean, (value: boolean) => void] {
  const [enabled, setEnabled] = useState(() => {
    const stored = sessionStorage.getItem(LEARNING_KEY);
    if (stored === null) return defaultEnabled;
    return stored === "1";
  });

  useEffect(() => {
    sessionStorage.setItem(LEARNING_KEY, enabled ? "1" : "0");
  }, [enabled]);

  return [enabled, setEnabled];
}

export function LearningMode({ content, enabled, onToggle, lab, children }: LearningModeProps) {
  return (
    <>
      <div className="learning-bar">
        <label className="learning-toggle">
          <input type="checkbox" checked={enabled} onChange={(event) => onToggle(event.target.checked)} />
          <span>
            <strong>Modo aprendizaje</strong>
            <em>Teoría del vector y laboratorio aislado</em>
          </span>
        </label>
      </div>
      {enabled ? (
        <div className="level-split">
          <section className="panel markdown-panel">
            <p className="eyebrow">Teoría</p>
            <h2>Guía conceptual</h2>
            {content.trim() ? (
              <div className="markdown-body">
                <ReactMarkdown rehypePlugins={[rehypeSanitize]}>{content}</ReactMarkdown>
              </div>
            ) : (
              <p className="muted">Este nivel aún no tiene tutorial. Usa la descripción y la pista conceptual.</p>
            )}
          </section>
          <div className="level-split-right">
            {lab}
            {children}
          </div>
        </div>
      ) : (
        <>
          {lab}
          {children}
        </>
      )}
    </>
  );
}

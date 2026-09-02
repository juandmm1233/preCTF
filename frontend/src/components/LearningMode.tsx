import { type ReactNode } from "react";
import type { LabEnvironment } from "../api/client";

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
  const activityPath = environment.activity_path || endpoint;

  return (
    <section className="panel lab-panel">
      <h2>Laboratorio aislado</h2>
      <p className="muted">
        Es la misma instancia IDS para todos los niveles web. Este nivel se trabaja en{" "}
        <code>{activityPath}</code>
        {activityPath !== "/index.php" && (
          <>
            {" "}
            (no sigas en <code>/index.php</code>).
          </>
        )}
      </p>
      <p className={`lab-status ${environment.status}`}>{envLabel(environment.status)}</p>
      {environment.message && <p className="alert error">{environment.message}</p>}
      {running && (
        <>
          <a
            className="button-link"
            href={environment.public_url ?? undefined}
            target="_blank"
            rel="noreferrer"
          >
            Abrir {activityPath}
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
  lab: ReactNode;
  children: ReactNode;
};

export function LearningMode({ lab, children }: LearningModeProps) {
  return (
    <>
      {lab}
      {children}
    </>
  );
}

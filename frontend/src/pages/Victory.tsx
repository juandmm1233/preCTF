import { useEffect, useState } from "react";
import { Link, Navigate } from "react-router-dom";
import { api, type Dashboard } from "../api/client";
import { useAuth } from "../context/AuthContext";

export function VictoryPage() {
  const { user } = useAuth();
  const [data, setData] = useState<Dashboard | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    api.dashboard().then(setData).catch(() => setData(null));
  }, []);

  if (data && !data.access_token) return <Navigate to="/" replace />;
  if (!data) return <p className="muted">Cargando certificado…</p>;

  async function copyToken() {
    if (!data?.access_token) return;
    await navigator.clipboard.writeText(data.access_token);
    setCopied(true);
  }

  const issued = new Date().toLocaleDateString("es-CO", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });

  return (
    <section className="certificate-wrap">
      <article className="certificate">
        <p className="eyebrow">Universidad Cooperativa de Colombia</p>
        <h1>Certificado de acceso al CTF práctico</h1>
        <p className="lead">
          Se otorga a <strong>{user?.full_name}</strong> ({user?.student_code}) por completar
          los {data.total} niveles del campo de entrenamiento preCTF.
        </p>
        <p className="muted">Puntaje final: {data.user.score} · {issued}</p>
        <div className="token-box">
          <span>Token de acceso</span>
          <code>{data.access_token}</code>
        </div>
        <div className="actions">
          <button type="button" onClick={copyToken}>
            {copied ? "Copiado" : "Copiar token"}
          </button>
          <Link to="/" className="button-link">
            Volver al dashboard
          </Link>
        </div>
        <p className="fineprint">
          Presenta este token al instructor al inicio de la clase Attack &amp; Defend.
          Es personal e intransferible.
        </p>
      </article>
    </section>
  );
}

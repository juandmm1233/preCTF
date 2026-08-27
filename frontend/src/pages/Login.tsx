import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError("");
    setBusy(true);
    try {
      await login(identifier, password);
      navigate("/", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo iniciar sesión.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth-layout">
      <section className="hero">
        <p className="eyebrow">Universidad Cooperativa de Colombia</p>
        <h1>Campo de entrenamiento previo al CTF</h1>
        <p>
          Completa los 8 niveles en orden. Cada flag desbloquea el siguiente. Al
          terminar recibes el token de acceso a la sesión práctica.
        </p>
      </section>
      <form className="panel auth-card" onSubmit={onSubmit}>
        <h2>Ingreso de estudiante</h2>
        <label>
          Correo o código
          <input
            value={identifier}
            onChange={(e) => setIdentifier(e.target.value)}
            autoComplete="username"
            required
          />
        </label>
        <label>
          Contraseña
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
            minLength={8}
            required
          />
        </label>
        {error && <p className="alert error">{error}</p>}
        <button type="submit" disabled={busy}>
          {busy ? "Entrando…" : "Entrar"}
        </button>
        <p className="muted">
          ¿Primera vez? <Link to="/register">Crea tu cuenta</Link>
        </p>
      </form>
    </div>
  );
}

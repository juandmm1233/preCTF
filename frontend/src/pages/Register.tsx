import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export function RegisterPage() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [studentCode, setStudentCode] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError("");
    setBusy(true);
    try {
      await register({
        email,
        student_code: studentCode,
        full_name: fullName,
        password,
      });
      navigate("/", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo registrar.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth-layout">
      <section className="hero">
        <p className="eyebrow">Registro</p>
        <h1>Crea tu bitácora de progreso</h1>
        <p>
          Usa tu correo institucional y código de estudiante. El avance es
          individual y secuencial.
        </p>
      </section>
      <form className="panel auth-card" onSubmit={onSubmit}>
        <h2>Nueva cuenta</h2>
        <label>
          Nombre completo
          <input value={fullName} onChange={(e) => setFullName(e.target.value)} required minLength={2} />
        </label>
        <label>
          Correo
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        </label>
        <label>
          Código de estudiante
          <input
            value={studentCode}
            onChange={(e) => setStudentCode(e.target.value)}
            minLength={4}
            required
            pattern="[A-Za-z0-9_-]+"
          />
        </label>
        <label>
          Contraseña (mín. 8)
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            minLength={8}
            required
          />
        </label>
        {error && <p className="alert error">{error}</p>}
        <button type="submit" disabled={busy}>
          {busy ? "Creando…" : "Registrarme"}
        </button>
        <p className="muted">
          ¿Ya tienes cuenta? <Link to="/login">Inicia sesión</Link>
        </p>
      </form>
    </div>
  );
}

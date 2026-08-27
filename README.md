# preCTF UCC — campo de entrenamiento secuencial

Plataforma web para que los estudiantes de ingeniería de sistemas completen **8 niveles en orden** antes de la clase Attack & Defend. El estudiante resuelve cada vector en una **instancia de entrenamiento** del laboratorio CTF UCC y **solo envía la flag** aquí. Al completar el último nivel recibe un **token de acceso** para el CTF práctico.

Esta aplicación **no incluye** payloads ni procedimientos de explotación. El código del laboratorio vulnerable **no vive en este repositorio**: el instructor publica una imagen Docker propia y preCTF solo la arranca, la aísla y la apaga.

## Arquitectura

| Capa | Tecnología | Rol |
|------|------------|-----|
| Frontend | React + Vite + TypeScript | Login, dashboard, envío de flags, modo aprendizaje, certificado |
| Backend | FastAPI | Auth JWT, validación secuencial, pistas, tokens, orquestación de labs |
| Base de datos | PostgreSQL 16 | Usuarios, niveles (Markdown de tutorial), progreso, sesiones de lab |
| Labs aislados | Docker + Traefik (rutas en archivo) | Una instancia por estudiante en la red `prectf_challenges` (puerto `:8088`) |
| Despliegue | Docker Compose | `web` (`:80`) + `api` (`:8001`) + `db` (`:5432`) + `dockerproxy` + `lab-proxy` |

Flujo: estudiante → instancia aislada del nivel (si está configurada) o laboratorio de entrenamiento → flag → `POST /api/levels/{id}/submit` → desbloqueo del siguiente nivel → token al completar N8.

## Mapeo laboratorio CTF UCC → niveles preCTF

Orden pedagógico (menor a mayor complejidad). CSRF existe en el lab como vector bonus **sin flag** en el scoreboard original; no forma parte de los 8 niveles obligatorios. XSS no está en el laboratorio actual.

| Nivel | Vector | Endpoint de referencia | Puntos | Flag de entrenamiento (rotar antes de la clase 15v15) |
|------:|--------|------------------------|-------:|------------------------------------------------------|
| 1 | SQL Injection | `/index.php` | 50 | `FLAG{PRECTF_N1_SQLI}` |
| 2 | Cookie tampering / BAC | `/admin.php` | 75 | `FLAG{PRECTF_N2_COOKIE}` |
| 3 | LFI / Path Traversal | `/download.php` | 60 | `FLAG{PRECTF_N3_LFI}` |
| 4 | Config leak | `download.php` + `config/app.ini` | 70 | `FLAG{PRECTF_N4_CONFIG}` |
| 5 | Command Injection | `/network.php` | 80 | `FLAG{PRECTF_N5_CMDI}` |
| 6 | Hash débil (MD5) | tabla `secrets` | 100 | `FLAG{PRECTF_N6_HASH}` |
| 7 | Upload inseguro | `/upload.php` | 120 | `FLAG{PRECTF_N7_UPLOAD}` |
| 8 | Credenciales SSH débiles | contenedor `db_ssh` | 150 | `FLAG{PRECTF_N8_SSH}` |

Las flags `FLAG{HONEYPOT_*}` y `FLAG{FAKE_*}` **restan 50 puntos** y no desbloquean nivel.

**Importante:** estas flags son de *entrenamiento*. Deben ser distintas de las de la sesión 15v15. El manual del laboratorio original ya documenta cómo rotar banderas.

## Cómo rotar flags

1. Edita las variables `PRECTF_FLAG_N1` … `PRECTF_FLAG_N8` en `.env`.
2. Recrea o reinicia el API para que el seed actualice los hashes:

```bash
docker compose up -d --build api
```

3. Los hashes SHA-256 se guardan en la tabla `levels`. La API **nunca** devuelve el texto plano de una flag.
4. Replica los mismos valores en la instancia de entrenamiento del lab (no en la VM de la clase competitiva).

## Arranque

```bash
copy .env.example .env   # Windows
# cp .env.example .env  # Linux/macOS
docker compose up -d --build
```

- UI: http://localhost
- API: http://localhost:8001/api/health
- Docs: http://localhost:8001/docs
- Labs (Traefik): http://n1-{8hex}.localhost:8088  (tras *Iniciar lección*; misma instancia para todos los niveles web)

Cuenta instructor por defecto (cámbiala): `instructor@ucc.local` / `CambiaEstaClave!`.

### Laboratorio aislado (una instancia IDS, varias rutas)

Los niveles 1–7 se resuelven **en el mismo contenedor** (Ibague Data Services / `ctf1`). El Nivel 2 no es otro laboratorio: es otra ruta.

| Tras *Iniciar lección* | Abrir |
|------------------------|--------|
| Nivel 1 | `http://n1-{8hex}.localhost:8088/index.php` |
| Nivel 2 | `http://n1-{8hex}.localhost:8088/admin.php` |
| Nivel 3 | `http://n1-{8hex}.localhost:8088/download.php` |

El login de práctica es el de **CTF UCC `ctf1`**. preCTF no copia ese código: construye una imagen desde la carpeta del lab.

```bash
docker compose --profile build-labs build challenge-n1
docker compose up -d --build api
```

En `.env`: `CHALLENGE_N1_IMAGE=prectf-challenge-n1:local` y, si el lab no está al lado, `CTF_LAB_N1_CONTEXT` con la ruta a `ctf1`. Detalle en [`challenges/n1/README.md`](challenges/n1/README.md).

Tras *Iniciar lección*, el botón del panel abre la ruta del nivel actual (`/index.php` en N1, `/admin.php` en N2, …). Las banderas de la instancia son las de este repo (`FLAG{PRECTF_N*}`), no las `FLAG{UCC_*}` del laboratorio de clase. Valídalas en preCTF.

- Tope simultáneo: `PRECTF_MAX_LAB_SESSIONS` (por defecto 20).
- Cada instancia caduca a los `LAB_TTL_MINUTES` (45).
- Los labs no alcanzan PostgreSQL ni el socket de Docker.
- En el aula, si los PCs no son el host de Compose, configure `LAB_BASE_DOMAIN` con DNS comodín hacia esa máquina.

### Desarrollo local (sin Docker para el frontend)

1. Levanta `db` y `api` con Compose, o PostgreSQL local.
2. En `backend/`: `pip install -r requirements.txt && alembic upgrade head && python -m app.seed && uvicorn app.main:app --reload --port 8001`
3. En `frontend/`: `npm install && npm run dev` → http://localhost:5173 (proxy `/api` → `:8001`)

## API principal

| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/api/auth/register` | Alta de estudiante (email + código) |
| POST | `/api/auth/login` | JWT (email o código) |
| GET | `/api/dashboard` | Progreso, estados `locked \| available \| completed`, token si aplica |
| POST | `/api/levels/{id}/submit` | Valida flag; `403 LEVEL_LOCKED` si el anterior no está hecho |
| POST | `/api/levels/{id}/hint` | Revela pista conceptual y resta puntos una sola vez |
| GET | `/api/levels/{id}` | Detalle, Markdown del tutorial y estado del laboratorio |
| POST | `/api/levels/{id}/environment/start` | Arranca (o reutiliza) la instancia aislada |
| GET | `/api/levels/{id}/environment` | Estado y URL pública de la instancia |
| POST | `/api/levels/{id}/environment/stop` | Apaga y elimina el contenedor |
| GET | `/api/admin/verify-token?token=` | Verifica el token de acceso (JWT admin o header `X-Instructor-Key`) |

Límite de envíos: 30 por minuto y estudiante.

## Esquema de datos (resumen)

- `users` — cuenta, puntaje, rol instructor
- `levels` — catálogo + `flag_hash` + `tutorial_content` (Markdown conceptual)
- `progress` — único por `(user_id, level_id)`
- `submissions` — auditoría de envíos
- `hint_uses` — pistas cobradas
- `honeypots` — hashes que penalizan
- `lab_sessions` — un contenedor IDS por estudiante (reutilizado en los niveles web)
- `access_tokens` — `PRECTF-UCC-{año}-{user8}-{nonce}.{hmac}`

## Verificación del token (instructor)

```bash
curl -s -H "X-Instructor-Key: cambia-esta-clave-de-instructor" ^
  "http://localhost:8001/api/admin/verify-token?token=PRECTF-UCC-...."
```

## Contenido que no va en esta plataforma

- Payloads, PoCs o playbooks ofensivos
- Copias de `ctf1/` o `ctf2` dentro de este repo
- Las flags de la clase competitiva 15v15

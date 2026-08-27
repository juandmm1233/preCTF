from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.security import hash_flag, hash_password
from app.models import Honeypot, Level, User

TUTORIAL_N1 = """## Qué es este vector

La inyección SQL aparece cuando la aplicación mezcla **estructura de la consulta** con **datos del usuario**. El motor de base de datos deja de distinguir un identificador (nombre, clave) de un trozo de SQL.

En un login, el síntoma típico es que el resultado de la autenticación depende de cómo se arma la sentencia, no solo de si las credenciales coinciden.

## Cómo identificarlo (sin explotar)

El laboratorio de este nivel expone un formulario en `/index.php`. El trabajo de observación es decidir si usuario y contraseña se tratan como **parámetros** o se interpolan en una cadena:

1. ¿La consulta se construye concatenando texto del formulario, o usa placeholders (`?` / nombres enlazados)?
2. ¿El plan de la consulta es fijo, independiente de lo que se escribe en los campos?
3. ¿Un error de autenticación se explica por credenciales incorrectas, o por un cambio en la lógica de la sentencia?

Si la autenticación no trata las credenciales como datos, la instancia de entrenamiento oculta la flag de este nivel. Recupérala en el laboratorio aislado y **envíala en este panel**.

## Cómo se corrige

- Consultas parametrizadas (prepared statements) en el servidor.
- Cuenta de base de datos con privilegios mínimos: el usuario de la app web no debe leer secretos ajenos al login.
- Nunca concatenar entrada de usuario dentro de SQL.
- Registrar y limitar intentos de autenticación.

Esta guía no incluye payloads ni procedimientos de explotación.
"""

LEVELS = [
    {
        "id": 1,
        "order_index": 1,
        "slug": "sqli",
        "title": "Autenticación rota",
        "vector_name": "SQL Injection",
        "lab_endpoint": "/index.php",
        "points": 50,
        "hint_cost": 10,
        "tutorial_content": TUTORIAL_N1,
        "description": (
            "El inicio de sesión construye la consulta con datos del formulario. "
            "Identifica por qué la autenticación no trata las credenciales como datos "
            "y confirma el hallazgo con la flag de este nivel."
        ),
        "hint_text": (
            "Revisa cómo se arma la consulta en el formulario de login de /index.php. "
            "La pista está en si usuario y contraseña se interpolan o se parametrizan."
        ),
    },
    {
        "id": 2,
        "order_index": 2,
        "slug": "cookie-bac",
        "title": "Control de acceso en el cliente",
        "vector_name": "Cookie tampering / Broken Access Control",
        "lab_endpoint": "/admin.php",
        "points": 75,
        "hint_cost": 15,
        "tutorial_content": "",
        "description": (
            "El panel administrativo decide el rol con un valor que el navegador envía. "
            "Un control de acceso sólido se verifica en el servidor, no en el cliente."
        ),
        "hint_text": (
            "Observa /robots.txt y cómo /admin.php interpreta la cookie de rol. "
            "Pregúntate quién puede modificar ese valor."
        ),
    },
    {
        "id": 3,
        "order_index": 3,
        "slug": "lfi",
        "title": "Lectura de archivos fuera de alcance",
        "vector_name": "LFI / Path Traversal",
        "lab_endpoint": "/download.php",
        "points": 60,
        "hint_cost": 15,
        "tutorial_content": "",
        "description": (
            "El visor de archivos del bucket concatena la ruta pedida por el usuario. "
            "Sin una ancla al directorio base, se pueden leer recursos que no deberían "
            "exponerse."
        ),
        "hint_text": (
            "El parámetro file de /download.php une rutas. Contrasta el directorio bucket "
            "con cualquier ruta que escape de esa carpeta."
        ),
    },
    {
        "id": 4,
        "order_index": 4,
        "slug": "config-leak",
        "title": "Divulgación de configuración",
        "vector_name": "Information disclosure (config leak)",
        "lab_endpoint": "/download.php + config/app.ini",
        "points": 70,
        "hint_cost": 15,
        "tutorial_content": "",
        "description": (
            "Si el lector de archivos no está acotado, los archivos de configuración "
            "fuera del bucket quedan al alcance. Encadena el hallazgo del nivel anterior."
        ),
        "hint_text": (
            "Hay notas en el bucket que mencionan un archivo de configuración. "
            "Piensa en rutas relativas desde download.php hacia config/."
        ),
    },
    {
        "id": 5,
        "order_index": 5,
        "slug": "cmdi",
        "title": "Diagnóstico que ejecuta de más",
        "vector_name": "Command Injection",
        "lab_endpoint": "/network.php",
        "points": 80,
        "hint_cost": 20,
        "tutorial_content": "",
        "description": (
            "La herramienta de red toma un host y lo pasa a una utilidad del sistema. "
            "Separar datos de comandos es el control que falta."
        ),
        "hint_text": (
            "En /network.php el campo host llega a una utilidad de diagnóstico. "
            "Distingue entre un nombre de host y metacaracteres de intérprete."
        ),
    },
    {
        "id": 6,
        "order_index": 6,
        "slug": "weak-hash",
        "title": "Secretos con hash débil",
        "vector_name": "Hash débil (MD5)",
        "lab_endpoint": "tabla secrets (MariaDB)",
        "points": 100,
        "hint_cost": 20,
        "tutorial_content": "",
        "description": (
            "Hay secretos almacenados con un algoritmo de hash obsoleto. "
            "La misma familia de fallos de autenticación del nivel 1 puede exponer "
            "filas que no deberían leerse."
        ),
        "hint_text": (
            "Busca etiquetas legacy_md5 en la base. Un hash rápido y sin sal "
            "no es un secreto: es un puzzle."
        ),
    },
    {
        "id": 7,
        "order_index": 7,
        "slug": "upload",
        "title": "Subida sin frontera",
        "vector_name": "Unrestricted file upload",
        "lab_endpoint": "/upload.php",
        "points": 120,
        "hint_cost": 25,
        "tutorial_content": "",
        "description": (
            "El módulo de almacenamiento acepta archivos y los deja donde el "
            "servidor web puede interpretarlos. Extensión, tipo y carpeta de destino "
            "tienen que coincidir con una política restrictiva."
        ),
        "hint_text": (
            "Revisa qué extensiones acepta /upload.php y si la carpeta uploads/ "
            "puede ejecutar código del lado del servidor."
        ),
    },
    {
        "id": 8,
        "order_index": 8,
        "slug": "ssh-creds",
        "title": "Acceso remoto predecible",
        "vector_name": "Credenciales SSH débiles",
        "lab_endpoint": "contenedor db_ssh (puertos 2222 / 2223)",
        "points": 150,
        "hint_cost": 25,
        "tutorial_content": "",
        "description": (
            "El acceso remoto usa credenciales débiles visibles en el panel Compute. "
            "Este es el último nivel: al superarlo obtienes el token de acceso "
            "al CTF práctico de la siguiente clase."
        ),
        "hint_text": (
            "Las credenciales de acceso remoto aparecen en Compute Engine. "
            "El objetivo es reconocer el riesgo de contraseñas por defecto, no tumbar el servicio."
        ),
    },
]

HONEYPOTS = [
    {"label": "secrets-table-1", "value": "FLAG{HONEYPOT_DO_NOT_SUBMIT_01}", "penalty": 50},
    {"label": "secrets-table-2", "value": "FLAG{HONEYPOT_TRAP_SOC_02}", "penalty": 50},
    {"label": "session-cookie", "value": "FLAG{FAKE_IN_COOKIE}", "penalty": 50},
]


def seed_levels(db: Session) -> None:
    for spec in LEVELS:
        flag = settings.flag_for_level(spec["order_index"])
        row = db.get(Level, spec["id"])
        payload = {**spec, "flag_hash": hash_flag(flag), "is_bonus": False}
        if row is None:
            db.add(Level(**payload))
        else:
            for key, value in payload.items():
                setattr(row, key, value)


def seed_honeypots(db: Session) -> None:
    for spec in HONEYPOTS:
        digest = hash_flag(spec["value"])
        existing = db.query(Honeypot).filter(Honeypot.flag_hash == digest).one_or_none()
        if existing is None:
            db.add(Honeypot(label=spec["label"], flag_hash=digest, penalty=spec["penalty"]))
        else:
            existing.label = spec["label"]
            existing.penalty = spec["penalty"]


def seed_admin(db: Session) -> None:
    if not settings.admin_email or not settings.admin_password:
        return
    email = settings.admin_email.lower()
    user = db.query(User).filter(User.email == email).one_or_none()
    if user is None:
        db.add(
            User(
                email=email,
                student_code=settings.admin_code.upper(),
                full_name=settings.admin_name,
                password_hash=hash_password(settings.admin_password),
                is_admin=True,
            )
        )
        return
    user.is_admin = True
    user.full_name = settings.admin_name
    user.student_code = settings.admin_code.upper()
    user.password_hash = hash_password(settings.admin_password)


def run() -> None:
    db = SessionLocal()
    try:
        seed_levels(db)
        seed_honeypots(db)
        seed_admin(db)
        db.commit()
        print("Seed preCTF completado.")
    finally:
        db.close()


if __name__ == "__main__":
    run()

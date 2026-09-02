from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.security import hash_flag, hash_password
from app.models import Honeypot, Level, User

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
        "tutorial_content": "",
        "explanation": (
            "La inyección SQL aparece cuando la aplicación mezcla la estructura de la "
            "consulta con datos del usuario. El motor de base de datos deja de distinguir "
            "un identificador (nombre, clave) de un trozo de SQL. En un login, el síntoma "
            "típico es que el resultado depende de cómo se arma la sentencia."
        ),
        "goal": (
            "El laboratorio expone un formulario en `/index.php`. Tu trabajo es inyectar "
            "código (ej. ' OR '1'='1) para obligar a la consulta a evaluar una condición "
            "como verdadera, sin importar la contraseña. Recupera la flag oculta tras "
            "evadir el inicio de sesión."
        ),
        "prevention": (
            "1. Usa consultas parametrizadas (prepared statements) en el servidor.\n"
            "2. Aplica el principio de mínimos privilegios en la base de datos.\n"
            "3. Nunca concatenes entradas del usuario directamente dentro de sentencias SQL."
        ),
        "tutorial_url": "https://www.youtube.com/watch?v=EWGUznyQIhE",
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
        "explanation": (
            "El control de acceso roto (Cookie Tampering) ocurre cuando una aplicación "
            "confía ciegamente en datos almacenados en el navegador del usuario (como "
            "cookies o Local Storage) para determinar sus permisos. Un atacante puede "
            "interceptar y alterar estos valores libremente."
        ),
        "goal": (
            "La instancia genera una cookie al ingresar. Inspecciona las herramientas de "
            "desarrollo de tu navegador (F12 > Aplicación/Almacenamiento). Encuentra la "
            "cookie que define tu rol, modifícala para suplantar a un administrador, "
            "recarga la página y captura la flag."
        ),
        "prevention": (
            "1. Nunca almacenes información de roles o estados de autorización en texto "
            "plano en el cliente.\n"
            "2. Implementa la validación de sesión y control de acceso estrictamente "
            "en el backend.\n"
            "3. Si debes enviar estado al cliente, utiliza tokens seguros y firmados "
            "criptográficamente (como JWT bien configurados)."
        ),
        "tutorial_url": "https://www.youtube.com/watch?v=Z261_-MPvZY",
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
        "title": "Notas internas en el bucket",
        "vector_name": "Information disclosure (objetos del bucket)",
        "lab_endpoint": "/download.php",
        "points": 60,
        "hint_cost": 15,
        "tutorial_content": "",
        "explanation": (
            "Antes de hablar de salir del directorio, hay un fallo más básico: el visor "
            "de Storage trata como objeto público todo lo que está en el bucket, incluidas "
            "notas de administración. Si la interfaz lista esos archivos, no hace falta "
            "alterar la ruta: el filtrado ya ocurrió al publicarlos."
        ),
        "goal": (
            "Abre el visor de `/download.php` y revisa los objetos que la propia página "
            "ofrece. La flag de este nivel está en un archivo del bucket que no debería "
            "ser público. No necesitas salir de esa carpeta; eso corresponde al nivel 4."
        ),
        "prevention": (
            "1. Separa el contenido público del interno: las notas de administración no "
            "pertenecen al bucket descargable.\n"
            "2. Lista blanca de nombres o IDs de objeto, no un listado de todo el directorio.\n"
            "3. El control de acceso debe aplicarse por objeto, no solo por estar logueado."
        ),
        "tutorial_url": "https://www.youtube.com/watch?v=8r1HQVZZ6hU",
        "description": (
            "El visor concatena el nombre pedido y, además, enlaza varios archivos del "
            "bucket. Uno de ellos es material interno. Este nivel se resuelve enumerando "
            "lo que ya está expuesto, sin modificar directorios."
        ),
        "hint_text": (
            "En `/download.php` hay accesos directos a objetos del bucket. Distingue un "
            "archivo de bienvenida de unas notas que no deberían estar ahí. robots.txt "
            "en esa misma lista es otra pista de superficie, no la flag."
        ),
    },
    {
        "id": 4,
        "order_index": 4,
        "slug": "config-leak",
        "title": "Divulgación de configuración",
        "vector_name": "Information disclosure (config leak)",
        "lab_endpoint": "/download.php",
        "points": 70,
        "hint_cost": 15,
        "tutorial_content": "",
        "explanation": (
            "El mismo visor del nivel 3 concatena la ruta al directorio del bucket "
            "sin comprobar que el archivo resultante siga dentro de esa carpeta. "
            "Ahí aparece el Path Traversal: un nombre de objeto deja de ser un "
            "nombre y pasa a ser una ruta relativa hacia archivos de configuración."
        ),
        "goal": (
            "Usa lo que ya viste en las notas del bucket: hay un archivo de "
            "configuración fuera de esa carpeta. Este nivel sí exige que el visor "
            "salga del directorio base. La flag no está en los objetos listados."
        ),
        "prevention": (
            "1. Resuelve la ruta con una función de canonización y verifica que "
            "quede dentro del directorio base.\n"
            "2. Rechaza separadores de ruta y nombres que no coincidan con una lista blanca.\n"
            "3. No sirvas archivos de configuración de la aplicación por el mismo visor."
        ),
        "tutorial_url": "URL_DEL_TUTORIAL_AQUI",
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
        "explanation": (
            "El Command Injection ocurre cuando la aplicación toma la entrada del "
            "usuario y la pasa directamente a la consola del sistema operativo sin "
            "validación, permitiendo a un atacante concatenar comandos maliciosos."
        ),
        "goal": (
            "Inyecta comandos del sistema operativo (usando separadores como ; o &&) "
            "en el formulario de diagnóstico para ejecutar comandos arbitrarios y "
            "leer la flag."
        ),
        "tutorial_url": "https://www.youtube.com/watch?v=4Ep3Pe0_6xA",
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
        "explanation": (
            "El uso de algoritmos de hashing criptográficamente rotos u obsoletos "
            "(como MD5) permite a los atacantes descifrar contraseñas rápidamente "
            "utilizando ataques de diccionario, fuerza bruta o Rainbow Tables."
        ),
        "goal": (
            "Identifica el hash MD5 filtrado en la aplicación y descífralo utilizando "
            "herramientas como Hashcat, John the Ripper o bases de datos en línea "
            "para obtener la flag."
        ),
        "tutorial_url": "URL_DEL_TUTORIAL_AQUI",
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
        "explanation": (
            "La vulnerabilidad de Unrestricted File Upload se da cuando la aplicación "
            "permite subir archivos sin validar correctamente su extensión, tipo MIME "
            "o contenido, lo que posibilita subir scripts maliciosos ejecutables."
        ),
        "goal": (
            "Sube una webshell o un script malicioso disfrazado al servidor para "
            "ganar ejecución remota de código (RCE) y extraer la flag del sistema."
        ),
        "tutorial_url": "URL_DEL_TUTORIAL_AQUI",
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
        "explanation": (
            "Los servicios de administración expuestos (como SSH) que utilizan "
            "contraseñas por defecto, credenciales débiles o predecibles, son "
            "altamente susceptibles a ataques de fuerza bruta automatizados."
        ),
        "goal": (
            "Utiliza una herramienta de ataque de diccionario como Hydra para "
            "realizar fuerza bruta sobre el servicio SSH, obtener acceso y "
            "capturar la flag final."
        ),
        "tutorial_url": "URL_DEL_TUTORIAL_AQUI",
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
        payload.setdefault("prevention", "")
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

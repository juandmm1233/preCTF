# Nivel 1 — login de entrenamiento (laboratorio CTF UCC)

preCTF **no reescribe** el login del CTF. Empaqueta el `ctf1` que ya existe en disco (`servidor_web` + MariaDB) y lo arranca aislado por estudiante.

## Construir la imagen

Desde `preCTF`, con el lab en `D:\juandmm1233\CTF ucc\ctf1`:

```bash
docker compose --profile build-labs build challenge-n1
```

O a mano:

```bash
docker build -f ./challenges/n1/Dockerfile -t prectf-challenge-n1:local "D:/juandmm1233/CTF ucc/ctf1"
```

`.env`:

```
CHALLENGE_N1_IMAGE=prectf-challenge-n1:local
CTF_LAB_N1_CONTEXT=../CTF ucc/ctf1
```

Luego:

```bash
docker compose up -d --build api
```

En el Nivel 1, *Iniciar lección* abre `http://n1-{8hex}.localhost:8088/index.php` con el formulario IDS.

La flag de entrenamiento (`PRECTF_FLAG_N1`) aparece en el dashboard **después** de autenticarse. Hay que validarla en preCTF, no en el scoreboard 15v15.

## Aislamiento

Los contenedores viven en `prectf_challenges`. No alcanzan PostgreSQL ni el socket de Docker. ~512 MB RAM. Tope: `PRECTF_MAX_LAB_SESSIONS`.

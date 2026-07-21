# GymFlow

Sistema de control de acceso físico y gestión de membresías para gimnasios
pequeños y medianos. Este README es solo un quickstart; el diseño completo
(Historias de Usuario, Requerimientos Funcionales y No Funcionales, Reglas
de Negocio) vive en `docs/Análisis.pdf`.

## Estructura

- `backend/` — API FastAPI (monolito modular)
- `frontend/` — kiosko táctil + backoffice (React + Vite + Tailwind)
- `docs/` — material fuente original (propuesta, análisis, diagramas)

## Quickstart local

```bash
cp .env.example .env   # y completar los valores reales

# Backend
cd backend
pipenv install --dev
pipenv run alembic upgrade head
pipenv run uvicorn main:app --reload

# Frontend (en otra terminal)
cd frontend
npm install
npm run dev
```

## Con Docker

```bash
cp .env.example .env
docker compose up --build
```

- Backend: http://localhost:8000 (`/health` para verificar que levantó)
- Frontend: http://localhost:5173
- Postgres: localhost:5432

El backend aplica las migraciones y **siembra solo los datos de desarrollo**
(`backend/scripts/seed_dev.py`, idempotente; se salta con
`ENVIRONMENT=production`): staff de prueba, un tipo de membresía "Mensual" y
una socia demo. No hay pasos manuales: se levanta el stack y se puedes probar.

⚠️ **Si el volumen de datos es anterior al cambio de HU-07** (cambio de hashing
passlib/bcrypt → pwdlib/Argon2): el login devuelve 401 aunque la contraseña
sea correcta, porque los hashes viejos ya no se pueden verificar. Resetear:

```bash
docker compose down -v      # borra el volumen con los hashes viejos
docker compose up --build   # migra y re-siembra solo
```

## Rutas del frontend

- `/` — dashboard del socio (HU-06): sin sesión redirige a `/portal/login`; con sesión, va directo al resumen de membresía.
- `/kiosko` — kiosko táctil de check-in (sin login, dispositivo físico).
- `/staff/login` — login del backoffice (Empleado/Administrador, HU-10 — Autenticación segura).
- `/staff/home` — panel del backoffice (sidebar): usuarios y membresías (HU-07 — Gestión de usuarios), permisos, dispositivos bloqueados (RN-03).
- `/portal/login` — portal del socio: login del Miembro con correo/contraseña.
- `/portal/activar` — activación de cuenta del Miembro (la cuenta la crea el staff; el socio define su contraseña la primera vez).
- `/portal` — alias que redirige a `/` (compatibilidad con el link antiguo).

## Cuentas de desarrollo (sembradas automáticamente)

`docker compose up` (o `pipenv run python scripts/seed_dev.py` si se trabaja sin
Docker) se dejan estas cuentas — **solo para desarrollo local**, nunca producción:

| Cuenta | Contraseña | Qué es |
|---|---|---|
| `empleado@gymflow.test` | `ClaveSegura123` | Backoffice, rol Empleado con permisos de ejemplo otorgados (para probar la diferencia entre rol y permiso) |
| `admin@gymflow.test` | `ClaveSegura123` | Backoffice, rol Administrador (todos los permisos, implícito) |
| `laura@socia.test` (cédula `555444333`) | — sin activar | Socia demo con membresía "Mensual" activa: prueba el check-in del kiosko por cédula, y la activación + login del portal en `/portal/activar` |

El **catálogo de permisos** no lo crea ningún admin desde la UI: los códigos de
permiso son de developer (nacen con la feature que les da lógica) y viajan en
las migraciones Alembic. El admin solo otorga/quita códigos existentes.

⚠️ Los tests de backend (`pipenv run pytest`) truncan las tablas antes de cada
test — se deben correr contra una base aparte (p. ej. `gymflow_test`), no contra la
del stack de Docker. Si igual se barrió la base de dev, `docker compose restart
backend` (o el seed manual) la vuelve a sembrar.

## Evitar problemas de saltos de línea (CRLF/LF)

El repo ya trae `.gitattributes` (`* text=auto eol=lf`), que fuerza LF en el contenido versionado sin importar el sistema operativo. Aun así, hay dos casos donde igual puede llegar CRLF a disco:

**1. Clon nuevo, primera vez (sobre todo en Windows):**

```bash
git config core.autocrlf false
git config core.eol lf
```

Esto evita que Git reintroduzca CRLF al hacer `checkout`, aunque no debería hacer falta porque `.gitattributes` ya lo fuerza.

**2. Ya se tenía el repo clonado y te sigue fallando (típicamente `docker-entrypoint.sh: /bin/bash^M: bad interpreter` al levantar el backend en Docker):**

`.gitattributes` se agregó *después* del primer commit, así que si clonaste antes de esa fecha, Git nunca reescribió los archivos que ya tenías en disco — un `git pull` normal no vuelve a aplicar las reglas de fin de línea a archivos que no cambiaron de contenido. Hay que forzar un re-checkout completo:

```bash
git config core.autocrlf false
git config core.eol lf
git rm --cached -r .
git reset --hard
```

Después, verificá que quedó bien:

```bash
git ls-files --eol | grep -i crlf   # no debería imprimir nada
```

Si se tenía cambios sin commitear, se guardan con `git stash` antes de correr `git reset --hard` y se recuperan después con `git stash pop`.

Si en cambio se quien tiene una rama con archivos ya commiteados en CRLF (antes de que existiera `.gitattributes`), antes de hacer push conviene correr:

```bash
git add --renormalize .
git commit -m "Normalize line endings"
```

Esto último arregla lo que se va a subir al repo; el paso 2 de arriba es el que arregla lo que ya tenés *en disco* después de bajar el `.gitattributes` nuevo.

## Tests

```bash
cd backend
pipenv run pytest
```

# GymFlow

Sistema de control de acceso físico y gestión de membresías para gimnasios
pequeños y medianos. Ver `AGENTS.md` para la descripción completa, stack y
convenciones — este README es solo un quickstart.

**Antes de tocar código, lee `AGENTS.md` y `spec/`.** Es un proyecto SDD
(Spec-Driven Development): la fuente de verdad del diseño es `spec/`.

## Estructura

- `backend/` — API FastAPI (monolito modular)
- `frontend/` — kiosko táctil + backoffice (React + Vite + Tailwind)
- `spec/` — constitución + specs de cada feature (SDD)
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
docker compose up
```

- Backend: http://localhost:8000 (`/health` para verificar que levantó)
- Frontend: http://localhost:5173
- Postgres: localhost:5432

## Rutas del frontend

- `/` — kiosko táctil de check-in (sin login, dispositivo físico).
- `/staff/login` — login del backoffice (Empleado/Administrador, `003-autenticacion-segura`).
- `/staff/dispositivos-bloqueados` — pantalla protegida: ver y desbloquear dispositivos de kiosko bloqueados (RN-03). Requiere login y, si el rol es Empleado, los permisos `checkin.ver_dispositivos_bloqueados`/`checkin.desbloquear_dispositivo` otorgados (ver siguiente sección). Administrador los tiene implícitos.

## Probar el backoffice (usuarios de prueba)

Todavía no existe `004-gestion-usuarios` (CRUD de usuarios), así que para probar el login del backoffice localmente hay que sembrar usuarios de Staff a mano. Hay un script para eso, idempotente (se puede correr las veces que haga falta):

```bash
cd backend
pipenv run alembic upgrade head        # asegúrate de tener la BD migrada
pipenv run python scripts/seed_dev_staff.py
```

Crea (si no existen ya) dos cuentas — **solo para desarrollo local**, no usar en producción:

| Correo | Contraseña | Rol | Permisos |
|---|---|---|---|
| `empleado@gymflow.test` | `ClaveSegura123` | Empleado | `checkin.ver_dispositivos_bloqueados`, `checkin.desbloquear_dispositivo` (otorgados explícitamente, para poder probar la diferencia entre rol y permiso) |
| `admin@gymflow.test` | `ClaveSegura123` | Administrador | Todos, implícito (no necesita filas en `usuario_permisos`) |

⚠️ Los tests de backend (`pipenv run pytest`) truncan la tabla `usuarios` antes de cada test — si corres los tests después de sembrar estos usuarios, se borran. Hay que volver a correr `seed_dev_staff.py`.

## Evitar problemas de saltos de línea (CRLF/LF)

Para que no se rompa el arranque del backend en Docker o entre Windows/Mac/Linux, mantén estos archivos con saltos de línea Unix:

```bash
git config core.autocrlf false
git config core.eol lf
git add --renormalize .
```

Si ya tuvieron problemas de line endings en una rama, antes de hacer push conviene correr:

```bash
git add --renormalize .
git commit -m "Normalize line endings"
```

Esto ayuda a que tu compañero en Mac no tenga errores al hacer pull/commit/push por diferencias de formato.

## Tests

```bash
cd backend
pipenv run pytest
```

# GymFlow

Sistema de control de acceso físico y gestión de membresías para gimnasios pequeños y medianos. Reemplaza la validación manual en recepción (planillas/Excel) por un motor de reglas que valida el ingreso en tiempo real desde un kiosko táctil, con un backoffice para administrar usuarios, membresías y reportes. Proyecto académico de Ingeniería de Software II (equipo de 5, entrega en 1 semana).

La fuente de verdad del diseño es `spec/`. Este archivo no repite ese contenido, lo indexa (ver **Documentación**).

## Stack

- **Lenguaje:** Python 3.13 (backend), TypeScript (frontend), Node.js 20.19+/22.12+
- **Framework / runtime:** FastAPI 0.139.0 (backend), React 19.2.7 + Vite 8.1.x (frontend)
- **Base de datos:** PostgreSQL 16 con SQLAlchemy 2.0.51 + Alembic 1.18.5 (ORM y migraciones)
- **Dependencias / entorno:** Pipenv — entorno virtual aislado por proyecto (`Pipfile` / `Pipfile.lock`)
- **Estilos / UI:** Tailwind CSS · consumo de API con React Query + Axios
- **Auth:** JWT propio y simple. Staff/Administrador (sesión corta, 30 min) y Miembro (sesión larga vía refresh token, portal web) — ver `spec/features/003-autenticacion-segura/` y `spec/features/011-portal-miembro-autenticacion/`. El kiosko sigue sin requerir JWT de usuario.
- **Tests:** pytest (backend); framework de tests frontend a definir con el equipo
- **Despliegue:** Docker (contenedorizado)

## Comandos

**Dependencias (Pipenv) — todo queda instalado en el entorno del proyecto, nunca global:**

- `pipenv install` — instala las dependencias del proyecto desde `Pipfile`/`Pipfile.lock`
- `pipenv install --dev` — instala también las dependencias de desarrollo (tests, lint)
- `pipenv install <paquete>` — añade una librería nueva (actualiza `Pipfile` y `Pipfile.lock`)
- `pipenv install --dev <paquete>` — añade una dependencia solo de desarrollo
- `pipenv shell` — abre una shell dentro del entorno del proyecto
- `pipenv run <comando>` — ejecuta un comando puntual dentro del entorno

**Backend (dentro del entorno de Pipenv):**

- `pipenv run uvicorn main:app --reload` — arranca el backend en local
- `pipenv run pytest` — ejecuta los tests de backend (deben pasar antes de cada commit)
- `pipenv run alembic revision --autogenerate -m "<mensaje>"` / `pipenv run alembic upgrade head` — crea y aplica migraciones

**Frontend:**

- `npm run dev` — arranca el frontend (Vite)
- `npm run build` — compila el frontend para producción

**Stack completo:**

- `docker compose up` — levanta el stack completo

**Lint:** frontend usa `oxlint` (`frontend/.oxlintrc.json`, `npm run lint`); backend usa `ruff` (`pipenv run ruff check .`), ya en `Pipfile` como dependencia de desarrollo.

## Estructura del proyecto

Monolito modular: cada módulo agrupa `router` + `service` + `repository` + `schemas` por dominio de negocio.

- `core/` — config, conexión a base de datos, seguridad JWT y dependencias compartidas
- `auth/` — router + service + schemas. **No tiene repository propio**: reutiliza el de `members` para leer `User`
- `members/` — dueño de la tabla `User`
- `checkin/` — dueño de la tabla `CheckIn`; orquesta la validación del ingreso (RN-01 a RN-04)
- `membership/` — dueño de `Membership` y `MembershipType`
- `reports/` — lectura agregada para reportes de asistencia
- `models/` — modelos SQLAlchemy centralizados (`User`, `Membership`, `MembershipType`, `CheckIn`, `Guest`)
- `main.py` — registra todos los routers; único punto de integración entre módulos
- `frontend/` — kiosko táctil (check-in) y panel de backoffice (React + Vite + Tailwind)
- `spec/` — especificación del proyecto (constitution + features)
- `docs/` — material fuente original (propuesta, análisis, diagramas), para trazabilidad
- `docker-compose.yml`, `backend/Dockerfile`, `frontend/Dockerfile` — stack contenedorizado (ver `spec/constitution/ci-cd.md`)
- `.github/workflows/ci.yml` — pipeline de GitHub Actions (tests + build + smoke test en contenedores)

## Convenciones

- **Regla de módulos (no negociable):** cada módulo accede solo a sus propias tablas vía su `repository`. Si necesita datos de otro módulo, llama al `service` del módulo dueño — nunca consulta su tabla ni importa su `repository`.
- **Validación con Pydantic** (`schemas.py` por módulo); nunca validar a mano en el `router`.
- **Atomicidad (RN-10):** toda operación que descuente visitas o cupos de invitado va envuelta en una transacción; no separar `SELECT` y `UPDATE` sin lock/transacción.
- **Nombres:** `snake_case` en Python, `camelCase` en TypeScript/React.
- **Idioma:** nombres de entidades y campos en español; variables y funciones de código en inglés.
- **Tests al lado del código del módulo**, corriendo con `pytest`.
- **Kiosko táctil primero:** botones ≥48×48px, alto contraste, legible a 1m. El backoffice puede ser más denso.
- **Commits sin `Co-Authored-By`:** los mensajes de commit no llevan línea `Co-Authored-By` del agente. El repo es de un equipo humano; la autoría del commit la lleva quien lo pide.

## Regla de ambigüedad (no negociable)

**El agente no toma decisiones de negocio ni de diseño que no estén ya resueltas en `spec/`. Si algo no está resuelto, se detiene y pregunta — nunca improvisa "lo más razonable".**

Antes de escribir código para una feature, el agente verifica:

1. ¿Existe `spec.md` de esa feature? Si no, se genera primero y se confirma con el equipo (no se implementa sobre un spec inexistente).
2. ¿El `spec.md` tiene una sección **"Duda abierta"** con ítems sin resolver que afectan lo que se va a implementar? Si sí, **no se implementa esa parte todavía** — se pregunta primero. No se elige la opción "más razonable" de la lista de propuestas ni se avanza "para no bloquear", aunque el spec ya sugiera un default.
3. ¿Hay algo en el camino (un valor, un umbral, un orden de validación, qué pasa en un caso borde) que el `spec.md`/`plan.md` no diga explícitamente? Eso es ambigüedad — se pregunta, no se asume.

**Ejemplos de decisiones que el agente NO puede tomar solo** (debe preguntar):
- Un valor numérico no especificado (duración de una ventana de tiempo, un umbral, un tamaño de página) — aunque el spec proponga un "default razonable", eso sigue siendo una propuesta a confirmar, no una decisión tomada.
- Qué hacer en un caso borde que el spec no menciona explícitamente (ej. ¿qué pasa si dos condiciones de una regla se cumplen a la vez y el spec no dice cuál gana?).
- Elegir entre dos formas igualmente válidas de modelar algo (ej. ¿un campo nuevo en una tabla existente, o una tabla aparte?) cuando el spec no lo especifica.
- Resolver una contradicción entre `docs/` y `spec/constitution/` a su criterio — eso se avisa (ver Flujo de trabajo), no se decide en silencio.

**Ejemplos de decisiones que el agente SÍ puede tomar solo** (no hace falta preguntar):
- Estilo de código, nombres de variables, organización interna de un archivo — siempre que respete las Convenciones ya fijadas aquí (`snake_case`, `camelCase`, etc.).
- Elegir *cómo* implementar algo que el spec ya especifica *qué* debe hacer, cuando solo hay una forma razonable de hacerlo con el stack ya definido (ej. usar SQLAlchemy para una migración, no si migrar o no).
- Corregir errores obvios de sintaxis, lint o tests que fallan, sin que eso cambie ningún comportamiento de negocio.

**Al preguntar:** el agente entrega la pregunta lista para responder (no un ensayo) — qué necesita saber, y si aplica, las opciones consideradas, igual que se ha hecho en `spec/` con las secciones "Duda abierta". No sigue implementando otras partes de la misma feature mientras espera respuesta si esas partes dependen de la decisión pendiente.

## No hagas

- **No agregues OAuth2 Authorization Server ni login federado (Google/GitHub).** El auth sigue siendo JWT propio y simple. El Miembro **sí puede** loguearse con correo/contraseña en el portal web (decisión en `spec/constitution/mission.md`) — esto no es una excepción al límite, sigue siendo el mismo JWT propio, solo que ahora cubre un rol más. El kiosko en sí (check-in por cédula/nombre) sigue sin requerir login. El Invitado nunca tiene login.
- **No introduzcas microservicios** ni comunicación entre servicios: es un monolito modular por decisión del equipo.
- **No hagas queries cruzadas** entre tablas de módulos distintos saltándote el `service` del módulo dueño.
- **No instales librerías con `pip` suelto ni de forma global.** Toda dependencia se añade con `pipenv install` para que quede aislada en el proyecto y registrada en `Pipfile`/`Pipfile.lock`. No edites `Pipfile.lock` a mano ni subas el entorno virtual (`.venv`) al repositorio.
- **No guardes contraseñas en texto plano** — siempre hash (RN-12).
- **No expongas `.env` ni credenciales** de base de datos en el repositorio.
- **No amplíes el alcance** a multi-sede, pasarela de pagos/checkout ni app móvil nativa: están explícitamente fuera de alcance (ver `spec/constitution/mission.md`).
- **No inventes reglas de negocio** que no estén en `docs/` o en `spec/constitution/`. Si una HU es ambigua, señálalo en vez de asumir.

## Flujo de trabajo

- Antes de implementar una feature, verifica que existe su `spec.md` en `spec/features/`. Si no existe, genérala primero (plantilla en `spec/README.md`) y confirma antes de pasar a `plan.md`/código.
- Antes de implementar, **revisa la carpeta de skills** (ver **Herramientas del agente**): si hay una skill aplicable a la tarea, léela y síguela antes de escribir código.
- Antes de una tarea no trivial, propón un plan y espera mi OK.
- Una tarea a la vez; al terminar, dime qué cambiaste para que lo revise.
- **Ver "Regla de ambigüedad" arriba — se aplica en cada paso de este flujo, no solo al empezar.**
- Verifica cada criterio de aceptación de la `spec.md` uno por uno antes de dar la feature por terminada.
- Al cerrar una feature, muévela a "Hecho" en `spec/constitution/roadmap.md`.
- Si `docs/` (material original) contradice a `spec/constitution/` (ya corregido, p. ej. el ORM), manda `spec/constitution/` y avisa de la discrepancia.

## Herramientas del agente (MCP y skills)

- **Skills:** antes de crear/editar archivos o abordar una tarea, **valida la carpeta de skills del proyecto** (`skills/`, o donde el equipo la ubique) y revisa si alguna aplica al caso. Si hay una skill relevante, léela y **síguela** en lugar de improvisar. No asumas que no existe una skill sin haber mirado la carpeta primero.
- **Context7 (MCP):** usa el MCP de Context7 para consultar **documentación actualizada** de librerías y frameworks (FastAPI, SQLAlchemy, Alembic, React, etc.) antes de usar una API, en vez de asumirla de memoria. Prioriza lo que devuelva Context7/la skill correspondiente sobre suposiciones.
- **Orden de preferencia:** skill del proyecto aplicable → documentación vía Context7 → conocimiento general. Si algo sigue sin estar claro, pregunta antes de implementar.

## Documentación

- `spec/constitution/mission.md` — qué construimos y para quién
- `spec/constitution/tech-stack.md` — stack, arquitectura, convenciones y límites duros
- `spec/constitution/roadmap.md` — orden de features por sprint
- `spec/constitution/design-system.md` — paleta y tokens del portal del socio
- `spec/constitution/ci-cd.md` — decisiones de Docker y del pipeline de GitHub Actions
- `spec/features/NNN-nombre/` — `spec.md`, `plan.md` y `tasks.md` de cada feature
- `docs/` — propuesta, análisis, HU, reglas de negocio (RN-01…RN-12), requisitos (RF-01…RF-13), mockups y diagramas

# Tech stack y convenciones

> ⚠️ La Propuesta original lista "Prisma" como ORM con una justificación que describe Node.js/Express — es un error de copiado (Prisma no aplica a FastAPI/Python). Este documento asume **SQLAlchemy + Alembic**, que es lo que aparece en el Diseño Preliminar y en el diagrama de arquitectura ya validado. Confirmar con el equipo/profesora antes de seguir si hay duda.

## Tecnologías

> Versiones confirmadas (julio 2026), no supuestas — `pipenv`/`npm` resolvieron estas versiones reales contra PyPI/npm al armar el scaffold (ver `ci-cd.md`). Se fija versión exacta donde ya se generó lock file real; donde no, queda como "última estable" a resolver cuando se instale.

- **Lenguaje backend:** Python **3.13** (`Pipfile` lo declara así). El lock file ya se regeneró en una máquina con Python 3.13 real, así que el Dockerfile usa `pipenv install --deploy` (ver `ci-cd.md`).
- **Lenguaje frontend:** TypeScript, Node.js **20.19+ / 22.12+** (requisito de Vite 8)
- **Framework / runtime backend:** FastAPI **0.139.0**
- **Framework frontend:** React **19.2.7** + Vite **8.1.x**, Tailwind CSS **4.3.2**
- **Consumo de API en frontend:** React Query (`@tanstack/react-query`) + Axios
- **Base de datos:** PostgreSQL 16
- **ORM / migraciones:** SQLAlchemy **2.0.51** + Alembic **1.18.5**
- **Auth:** JWT propio (sin OAuth2 Authorization Server). Dos usos: (1) Staff/Administrador → backoffice, sesión corta (30 min inactividad, ver `003-autenticacion-segura`); (2) Miembro → portal web, sesión larga con **access token + refresh token** (ver `011-portal-miembro-autenticacion`). El kiosko físico sigue sin requerir JWT de usuario para el check-in por cédula/nombre.
- **Tests:** pytest + httpx (backend) — framework de tests frontend a definir con el equipo
- **Despliegue:** Docker (contenedorizado, requisito RNF de despliegue). Ver `ci-cd.md` para el detalle de servicios, `Dockerfile`s y el pipeline de CI.

## Archivos / módulos clave (Monolito Modular)

- `core/` — config, conexión a base de datos, seguridad JWT, dependencias compartidas.
- `auth/` — router + service + schemas. **No tiene repository propio**: reutiliza el repository de `members` para leer `User` (no duplica acceso a esa tabla).
- `members/` — router, service, repository, schemas. Dueño de la tabla `User`.
- `checkin/` — router, service, repository, schemas. Dueño de la tabla `CheckIn`. Orquesta la validación de RN-01 a RN-04.
- `membership/` — router, service, repository, schemas. Dueño de `Membership` y `MembershipType`.
- `reports/` — router, service, repository, schemas. Lectura agregada sobre `CheckIn` para reportes.
- `models/` — modelos SQLAlchemy centralizados (`User`, `Membership`, `MembershipType`, `CheckIn`, `Guest`).
- `main.py` — registra todos los routers, único punto de integración entre módulos.

## Comandos

- `uvicorn main:app --reload` — arranca el backend en desarrollo.
- `alembic revision --autogenerate -m "<mensaje>"` / `alembic upgrade head` — migraciones.
- `pytest` — corre tests de backend.
- `npm run dev` — arranca el frontend (Vite).
- `docker compose up --build` — levanta el stack completo (db + backend + frontend); ver `ci-cd.md` para el detalle de los servicios.

## Modelo de datos / dominio

- `User` — cédula, nombre, email, rol (Invitado/Miembro/Empleado/Administrador), estado (Activo/Inactivo). Al eliminar un usuario se borra su info personal pero se preservan sus `CheckIn` históricos (RN-07).
- `Membership` — vinculada a `User` (miembro_id), tipo, `visitas_restantes`, `cupo_invitados_restantes`, `fecha_inicio`, `fecha_vencimiento`, estado (Activa/Vencida). **Un socio puede tener varias filas `Membership` a lo largo del tiempo** — cada renovación (`004-gestion-usuarios`) crea una fila nueva en vez de editar la anterior, para preservar qué plan/precio tenía en cada ciclo pasado (RN-06, RN-07). En un momento dado, normalmente hay a lo sumo una `Membership` con `estado = Activa` por socio.
- `MembershipType` — plantilla configurable: nombre, precio_base, visitas_totales, cupo_invitados, duracion_dias, activo. **No se puede eliminar/desactivar si tiene membresías activas vinculadas** (RN-05). Cambios en sus parámetros no alteran contratos vigentes, solo aplican al siguiente ciclo (RN-06).
- `CheckIn` — usuario_id, fecha_hora, resultado (Exitoso/Denegado), razon_denegacion, titular_id (solo si es check-in de invitado), **`isActive` (bool, campo nuevo — ver `001-checkin-membresia-activa`)**: `true` marca el `CheckIn` que representa el acceso ya concedido para el día calendario de `fecha_hora`; un reingreso exitoso el mismo día no crea un nuevo `isActive=true` ni descuenta visita, siempre que la consulta filtre explícitamente por fecha (un `isActive=true` de un día anterior no cuenta). Índice único parcial recomendado: `UNIQUE(usuario_id, DATE(fecha_hora)) WHERE isActive = true`. Registro inmutable.
- `Guest` (Invitado) — cédula, nombre, titular_id (el miembro que lo invita).

## Convenciones

- **Regla de módulos (no negociable):** cada módulo solo accede a sus propias tablas vía su `repository.py`. Si un módulo necesita datos de otro (ej. `checkin` necesita saber si la `membership` está activa), llama al `service.py` del módulo dueño — nunca consulta la tabla directamente ni importa su repository.
- Nombres: `snake_case` en Python, `camelCase` en TypeScript/React.
- Validación de entrada con Pydantic schemas (`schemas.py` por módulo), nunca validar a mano en el router.
- Todo endpoint que descuente visitas o cupos de invitado debe envolver la operación en una transacción (RN-10) — no hacer el `SELECT` y el `UPDATE` en pasos separados sin lock/transacción.
- Idioma del contenido: nombres de entidades y campos en español (como en el análisis), nombres de variables/funciones de código en inglés, consistente con lo ya definido en el diagrama de clases.

## Estilo visual

- Kiosko de check-in: botones táctiles ≥48x48px, alto contraste, legible a 1 metro de distancia (RNF de usabilidad).
- Backoffice/admin: puede ser más denso en información, prioriza tablas y filtros sobre botones grandes.
- Tailwind CSS como sistema de utilidades; sin librería de componentes definida aún (a decidir con el equipo Frontend).
- **Portal del socio (web):** sigue el sistema de diseño extraído de los mockups en `docs/` — ver `design-system.md` para la paleta completa (tokens Tailwind listos para usar). Resumen: navy `#1c294c` como color primario/sidebar, verde-teal `#24c19f` como acento de éxito, fondo de página gris muy claro `#f5f6fb`, cards blancas con esquinas redondeadas y sombra suave. **No inventar colores nuevos** fuera de esta paleta sin confirmarlo con el equipo — si falta un color para un caso (ej. error/rojo, que no aparece en los mockups provistos), queda como duda abierta en la spec correspondiente.

## Límites duros

- No agregar Spring/OAuth2 Authorization Server, login federado, ni multi-`SecurityFilterChain` — el auth es JWT propio y simple.
- No introducir microservicios ni comunicación entre servicios — es un monolito modular por decisión explícita del equipo.
- No hacer queries cruzadas entre tablas de distintos módulos saltándose el service del módulo dueño.
- No guardar contraseñas en texto plano — siempre hash (RN-12).
- No exponer `.env` ni credenciales de base de datos en el repo.
- Toda conexión debe ir sobre HTTPS/TLS en producción (RNF de seguridad).

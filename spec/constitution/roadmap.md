# Roadmap

> Basado en el mapa de historias de usuario y la planeación de 3 sprints de la Propuesta. Cada feature se crea en `features/NNN-nombre-feature/` con `spec.md`, `plan.md` y `tasks.md` antes de tocar código.

## Hecho

- **001 · Check-in con membresía activa** — HU-01. Motor de validación (Filtro 1 `isActive` de hoy, Filtro 2 RN-01) en una transacción única (RN-10), con `SELECT ... FOR UPDATE` + índice único parcial para concurrencia (RN-08/RN-02), `GET /health`, y pantalla de kiosko (teclado numérico + semáforo). 6/6 tests en verde (incluye 10 check-ins concurrentes) y verificado end-to-end en navegador real. Ver `features/001-checkin-membresia-activa/`.
- **002 · Acceso denegado** — HU-02. Semáforo rojo con motivo exacto (`MEMBRESIA_VENCIDA`/`SIN_VISITAS`/`CEDULA_NO_ENCONTRADA`) persistido en `CheckIn`, y bloqueo de dispositivo 20 min tras 3 fallos por cédula inválida en ≤5 min (RN-03, contador en tabla `CheckinDeviceLock` para ser correcto con múltiples workers). Identidad de dispositivo resuelta como `X-Device-Id` + fallback IP. Endpoint de desbloqueo manual implementado sin guard de rol (pendiente de `003`). 11/11 tests en verde y verificado end-to-end en Docker + navegador real. Ver `features/002-acceso-denegado/`.
- **003 · Autenticación segura** — HU-10. Login de Empleado/Administrador con JWT (expiración deslizante de 30 min, RN-11, entregada vía header `X-New-Token`) y RBAC. Ampliada durante la implementación con un sistema de **permisos por usuario individual** (tablas `permisos`/`usuario_permisos`, dueño `auth`) además del rol: un empleado puede tener permisos que otro empleado del mismo rol no tiene (ej. `checkin.desbloquear_dispositivo`); `administrador` los tiene todos implícitamente. Otorgar permisos a una persona específica queda para `004` (es CRUD). Cierra los 2 endpoints `TODO(003)` de `checkin` con `require_permission`. 29/29 tests en verde (incluye los primeros tests HTTP/`TestClient` del repo). Ver `features/003-autenticacion-segura/`.

## Sprint 1 (base del sistema — prerrequisito real de todo lo demás)

> **Va primero, no es un cambio de opinión sobre qué es "el core".** `011` (login del socio) necesita que exista un socio real en la base, y hoy la única forma de crear uno es que el Staff lo dé de alta desde `004`, que a su vez necesita que el Staff se loguee (`003`, ya hecho). Sin esto, `007`/`011`/`012`/`013` no tienen con qué probarse de verdad (un seed manual por SQL serviría para desarrollo aislado, pero no para el flujo completo que va a revisar la profesora: staff crea al socio → socio se loguea → escanea QR).

- **004 · Gestión de usuarios y membresías** — HU-07. CRUD de usuarios, **primera asignación de membresía y renovación** (fusionado con lo que iba a ser "013 original" — ver `004`, sin HU de origen para la parte de renovación, hueco identificado en revisión de dominio: cierra lo que dejaba RN-06 sin forma de dispararse). Incluye también otorgar/editar permisos individuales de un usuario (nuevo alcance agregado durante `003`, ver `features/003-autenticacion-segura/spec.md`).

## Core del producto (justo después de Sprint 1)

> Estas 4 features son las que sí tienen respaldo real detrás de los mockups aceptados (Dashboard, Account, Achievements) más el QR, que es la esencia del producto (HU-03) — van primero dentro de lo que queda después de `003`/`004`, no se esperan `005`-`010`.
>
> Resuelve además la contradicción documentada en `008-busqueda-multiples-criterios` (RF-02 pedía "QR dinámico por sesión del Miembro" pero la misión decía "sin login"). Decisión: el Miembro puede loguearse en un portal web nuevo; el check-in por cédula/nombre en el kiosko sigue intacto. Ver `mission.md` para el detalle de la decisión.
>
> **Reinterpretación de prioridad (HU-01 vs HU-03):** el equipo confirma que la esencia del producto siempre fue **HU-03** (identificación por QR, sin contacto), no **HU-01** (cédula). Esto **no reescribe el texto de HU-01/HU-03** en `docs/` — esos quedan como registro histórico de lo que se redactó. Lo que cambia es cómo se prioriza en `spec/`: `001` deja de tratarse como "el flujo central" y pasa a ser el **motor de validación compartido** (reglas de negocio: membresía activa, visitas, duplicado del día, descuento atómico) que tanto el check-in manual (`001`) como el check-in por QR (`012`) reutilizan. La parte que sí cambia de rol es solo la **identificación** (cédula → respaldo, QR → camino esperado), no el motor de reglas en sí.
>
> **Decisión de alcance sobre los mockups (equipo, no ambigüedad):** de las 6 pantallas del mockup del portal, solo **Dashboard**, **Account** y **Achievements** entran — todas con datos reales detrás. **Workouts** y **Classes** (calorías, reserva de clases con IA) se cortan del entregable por completo: no tienen ninguna regla de negocio de origen en `docs/`, son contenido de una plantilla de fitness genérica que se coló en el mockup. Ver la nota en `011` y en `mission.md`.

- **007 · Resumen de membresía** — HU-06. Detalle de tipo, vencimiento y visitas restantes. Es el dato que alimenta el Dashboard del portal (`011`).
- **011 · Portal del socio y autenticación** — Login/registro del Miembro con correo/contraseña, sesión larga con refresh token, y pantalla de resumen (reutiliza el endpoint de `007`). Prerrequisito de `012` y `013`.
- **012 · Check-in por QR dinámico (HU-03 — flujo esencial del producto)** — El kiosko muestra un QR que rota, el socio lo escanea desde el portal web (botón de cámara), el backend valida su sesión + el QR y notifica al kiosko por WebSocket. Reutiliza el motor de reglas de `001`. Depende de `011` y reemplaza el workaround de "QR estático" que quedó anotado como pendiente en `008`.
- **013 · Logros por racha de asistencia** — Sin HU de origen (decisión del equipo): pantalla de Achievements del mockup, con datos reales calculados de `CheckIn.isActive` (racha actual, racha más larga, insignias por umbral). Depende de `011` (mismo portal).

## Sprint 2 (Alta/Media — invitados y experiencia)

- **005 · Cortesía de primer día** — HU-04. Alta automática como "Prospecto" con acceso gratuito único.
- **006 · Check-in de invitado** — HU-05. Descuento atómico de cupo de invitado del socio titular.
- **008 · Búsqueda por múltiples criterios** — HU-03. Búsqueda por cédula, QR o nombre.

## Sprint 3 (Media/Baja — administración y reportes)

- **009 · Configuración de tipos de membresía** — HU-08. CRUD de `MembershipType` respetando RN-05/RN-06.
- **010 · Reportes de asistencia** — HU-09. Reporte histórico con filtro por rango de fechas y export a XLSX/CSV.

## Semana de documentación

- Consolidar `docs/` y `spec/` finales para entrega.
- Verificar trazabilidad: cada HU → su feature → sus criterios de aceptación cumplidos.

## Backlog / ideas 💡

- Bloqueo de dispositivo tras 3 intentos fallidos en 5 min (RN-03) — **hecho** dentro de `002-acceso-denegado` como guard de dispositivo del módulo `checkin` (el contador vive donde se producen las denegaciones), no como feature independiente. Ver `features/002-acceso-denegado/`. La *identidad de dispositivo* se resolvió como `X-Device-Id` + fallback IP para poder avanzar — sigue sin confirmar formalmente con el equipo/profesora.
- Multi-sede — explícitamente fuera de alcance (ver `mission.md`), no planear a menos que cambie el alcance del proyecto.

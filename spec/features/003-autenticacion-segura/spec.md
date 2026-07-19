# 003 · Autenticación segura

**Estado:** implementada

**Traza:** HU-10 · RN-11, RN-12 · RF-09 · RNF seguridad (HTTPS/TLS), límite duro "JWT propio, sin OAuth server"

## Qué hace

Permite a **Empleado** y **Administrador** iniciar sesión con credenciales y obtener un **JWT propio** que autoriza el acceso al backoffice y a los endpoints de API según su **rol** (RBAC). Las sesiones expiran por inactividad y las contraseñas se guardan siempre con hash.

El flujo de **Miembro/Invitado en el kiosko no requiere login** (así lo fija la misión): el check-in por cédula/nombre es público a nivel de usuario y se protege por dispositivo (RN-03), no por JWT. Esto sigue siendo cierto para el kiosko. El Miembro sí puede loguearse por fuera del kiosko, en el **portal web** (`011-portal-miembro-autenticacion`), con su propio esquema de sesión (access + refresh token, distinto al de Staff/Administrador porque su propósito es otro: consulta de cuenta y habilitar check-in por QR, no acceso al backoffice). El Invitado nunca tiene login, en ningún canal.

## Por qué

Las funciones administrativas (CRUD de usuarios, configuración, reportes) deben quedar restringidas por rol (RF-09). Es prerrequisito de las features `004`, `009` y `010`.

## Criterios de aceptación

- [x] Un Empleado/Administrador con credenciales válidas recibe un **JWT firmado** que incluye su `rol` y una expiración (`exp`).
- [x] Credenciales inválidas → **401** sin revelar si el usuario existe.
- [x] Un usuario con `estado=inactivo` no puede loguearse, aunque sus credenciales sean correctas (mismo **401** genérico, sin distinguir el motivo).
- [x] Un endpoint de backoffice sin token válido → **401**; con token válido pero **autorización insuficiente** → **403** (RBAC, RF-09). En esta feature los dos endpoints protegidos usan el mecanismo de **permiso específico** (ver más abajo), no un rol genérico — `require_role(*roles)` queda implementado y disponible en `auth/dependencies.py` para `004`/`009`/`010`, pero ningún endpoint de `003` lo usa directamente.
- [x] La sesión expira tras **30 min de inactividad** (RN-11), implementada como **expiración deslizante**: cada request autenticada exitosa reemite el token con `exp` renovado y lo entrega en el header de respuesta `X-New-Token`. Sin actividad 30 min → el token vencido devuelve 401 y no hay renovación.
- [x] Las contraseñas se almacenan **hasheadas** (bcrypt/argon2), nunca en texto plano (RN-12). *Comprobable: inspección de la tabla no muestra la contraseña en claro.*
- [x] Los endpoints del **kiosko** (check-in, cortesía, invitado, resumen) funcionan **sin** JWT de usuario (misión).
- [x] **Permisos por usuario individual:** además del rol (`empleado`/`administrador`), un usuario puede tener permisos específicos otorgados de forma individual (ej. un empleado de recepción puede tener `checkin.desbloquear_dispositivo` y otro empleado, sin ese permiso, no). El rol `administrador` tiene implícitamente **todos** los permisos, sin necesidad de que se le otorguen explícitamente.
- [x] Los endpoints `GET /checkin/dispositivos-bloqueados` y `POST /checkin/desbloquear/{device_id}` (marcados `TODO(003)` en `checkin/router.py`) quedan protegidos por permiso específico, no solo por rol genérico: `checkin.ver_dispositivos_bloqueados` y `checkin.desbloquear_dispositivo` respectivamente.

## Fuera de alcance

- **CRUD** de usuarios/altas de staff → `004-gestion-usuarios` (esta feature solo autentica y autoriza).
- **Otorgar o editar permisos de un usuario específico** → también es CRUD, queda para `004-gestion-usuarios`. `003` solo construye el modelo de datos (`permisos`, `usuario_permisos`) y el mecanismo de verificación (`require_permission`); no expone ningún endpoint para asignar permisos. Para probar `003` sin que exista `004` todavía, los permisos se siembran directo en la base vía SQLAlchemy en los tests (mismo patrón que ya usa `checkin/test_service.py` para crear socios).
- **OAuth2 / Authorization Server / login federado / multi-SecurityFilterChain** → prohibido por la constitución.
- Recuperación de contraseña / MFA → no está en `docs/`; no se implementa.
- **Revalidación de sesión ante desactivación a mitad de sesión:** decisión confirmada — el JWT es totalmente stateless (`get_current_user` no consulta la base de datos en cada request); si un Administrador desactiva a un Empleado, el JWT ya emitido sigue siendo válido hasta su expiración natural (máx. 30 min). No se implementa revocación inmediata.

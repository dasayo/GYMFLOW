# 011 · Portal del socio y autenticación de Miembro — Plan

## Enfoque

El módulo **`auth`** (dueño de la identidad) gana una segunda "cara": además del login de staff (`003`, sesión deslizante de 30 min), maneja la sesión del Miembro con **access token corto (15 min) + refresh token rotatorio (ventana de 7 días deslizantes)**. `auth` sigue sin repository de usuarios: lee `User` vía `members.service` (regla de módulos); sí es dueño de la tabla nueva `refresh_tokens`. El portal es un frontend nuevo bajo `/portal/*`, separado del kiosko y del backoffice, y su Dashboard consume el resumen de `007`.

## Implementación

### Backend

1. **Migración Alembic:** tabla `refresh_tokens` (dueño `auth`): `id`, `usuario_id` (FK `usuarios.id`), `token_hash` (SHA-256 del token opaco — nunca el token en claro), `expira_en` (timestamptz), `creado_en`, `revocado_en` (nullable). Índice por `token_hash`.
2. **`core/config.py`:** `member_access_token_minutes = 15`, `member_refresh_days = 7`.
3. **`models/refresh_token.py`:** modelo SQLAlchemy; export en `models/__init__.py`.
4. **`auth/repository.py`:** CRUD de `refresh_tokens` (crear, buscar por hash vigente, revocar).
5. **`auth/service.py`:**
   - `login_member(email, password, db)` — solo rol `miembro` + estado `activo`; error genérico (mismo criterio anti-enumeración que `003`). Devuelve access token (claim `kind="member"`) + refresh token opaco.
   - `refresh_member_session(raw_token, db)` — valida hash vigente y no revocado; **rota**: revoca el usado, emite uno nuevo con `expira_en = ahora + 7 días`, y devuelve access token nuevo.
   - `activate_member_account(cedula, email, password, db)` — cédula+correo deben coincidir con un `miembro` sin `password_hash`; setea el hash (RN-12, `core.security.hash_password`). Error genérico si no aplica.
   - `logout_member(raw_token, db)` — revoca el refresh token.
6. **`auth/router.py`:** `POST /auth/portal/login`, `POST /auth/portal/refresh`, `POST /auth/portal/activar`, `POST /auth/portal/logout`. El refresh token viaja en **cookie httpOnly** (`Set-Cookie` con `samesite=lax`, `path=/auth/portal`); el access token va en el body JSON.
7. **`auth/dependencies.py`:** `require_member` — exige JWT con claim `kind="member"`; el JWT de staff (`003`) no sirve en el portal ni viceversa (el de staff no lleva ese claim).

### Frontend (portal `/portal/*`)

8. Contexto de sesión del Miembro separado del de staff: access token **en memoria** (no `localStorage`), refresh silencioso contra `/auth/portal/refresh` al montar y al recibir 401 (interceptor Axios con `withCredentials`).
9. Pantallas: **Login** (`/portal/login`), **Activar cuenta** (`/portal/activar`), **Dashboard** (`/portal`, protegido): saludo por nombre + tarjeta de resumen de `007` + aviso de vencimiento (≤10 días). Estilo según `spec/constitution/design-system.md`, pensado para celular (es la superficie donde vivirá el escaneo QR de `012`).
10. Nada se registra en `staffMenu.ts` (eso es solo backoffice).

## Decisiones

- **Refresh token opaco + hash en DB** (no JWT): permite revocación y rotación real; un token robado deja de servir en cuanto se usa el legítimo.
- **Claim `kind="member"`** en el access token para separar poblaciones de tokens sin duplicar `core/security`.
- **Cookie `httpOnly` con `path=/auth/portal`**: el refresh token solo viaja a los endpoints de sesión, no en cada request de API.
- **Sin autorregistro**: solo activación de cuentas creadas por staff (dudas resueltas en `spec.md`).

## Riesgos

- **Rotación + requests concurrentes** del mismo navegador pueden intentar refrescar con el token ya rotado → el frontend serializa el refresh (una sola promesa en vuelo).
- **Usuario anonimizado (RN-07)** pierde `cedula`/`email` → no puede activar ni loguearse; el login genérico ya lo cubre sin caso especial.

# 011 · Portal del socio y autenticación de Miembro — Tareas

## Backend

- [x] Migración Alembic: tabla `refresh_tokens` (`token_hash`, `expira_en`, `revocado_en`, FK `usuario_id`) — `c98ffd6f38d1`.
- [x] `models/refresh_token.py` + export en `models/__init__.py`.
- [x] `core/config.py`: `member_access_token_minutes` (15) y `member_refresh_days` (7).
- [x] `auth/repository.py`: `RefreshTokenRepository` (crear/buscar-vigente/revocar).
- [x] `auth/service.py`: `login_member`, `refresh_member_session` (rotación + ventana deslizante), `activate_member_account` (cédula+correo, sin `password_hash` previo; el hash lo hace `members.service`, dueño de `usuarios`), `logout_member`.
- [x] `auth/router.py`: `POST /auth/portal/{login,refresh,activar,logout}` con cookie httpOnly para el refresh token (path `/` porque el navegador ve la API con prefijo `/api` vía proxy).
- [x] `auth/dependencies.py`: `require_member` (claim `kind="member"`; rechaza JWT de staff).

## Frontend

- [x] Contexto de sesión del Miembro (`MemberAuthContext` + `useMemberAuth`; access token solo en memoria en `api/portal.ts`, refresh silencioso single-flight, Axios `withCredentials`). El provider solo envuelve `/portal/*`.
- [x] `/portal/login` — login correo/contraseña (`PortalLogin.tsx`).
- [x] `/portal/activar` — activación de cuenta (`PortalActivate.tsx`).
- [x] `/portal` — Dashboard protegido: saludo por nombre + tarjeta de resumen (007) + aviso ≤10 días (`PortalDashboard.tsx`). Tokens de `design-system.md` (incluye `--color-member-error` resuelto), mobile-first.

## Tests

- [x] Login ok / credenciales inválidas (error genérico) / staff rechazado / miembro inactivo rechazado.
- [x] Refresh: rota el token (el viejo deja de servir), renueva la ventana; expirado/ausente → 401; miembro desactivado → 401.
- [x] Activación: caso feliz + login posterior; datos que no coinciden / ya activada / cédula inexistente → 400 genérico idéntico; rol no-miembro rechazado; hash RN-12 verificado.
- [x] `require_member`: sin token → 401; JWT de staff → 403 (en `membership/test_summary.py`).
- [x] Frontend: `npm run lint` (oxlint) + `tsc -b` + `npm run build` en verde.
- [x] `pytest` completo: 117/117 en verde (contra `gymflow_test` aislada, no la DB de Docker compartida).

## Cierre

- [x] Validar contra los criterios de aceptación de `spec.md` uno por uno.
- [x] Flujo end-to-end verificado con `curl` a través del proxy nginx: staff crea socio (004) → activa cuenta → login → resumen real → rotación de refresh → reuso viejo 401.
- [ ] **Pendiente de confirmación del usuario:** verificación visual en navegador (login, activación, dashboard).
- [ ] Mover la feature a "Hecho" en `../../constitution/roadmap.md` (tras la confirmación visual).

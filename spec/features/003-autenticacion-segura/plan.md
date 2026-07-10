# 003 · Autenticación segura — Plan

## Enfoque

Módulo **`auth`** con `router.py`, `service.py`, `schemas.py` y, a diferencia del plan original, **sí tiene su propio `repository.py`** — pero únicamente para las tablas nuevas `permisos`/`usuario_permisos`, que `auth` posee (es un concepto de autorización, no un atributo intrínseco de `User`). Para leer `User` sigue reutilizando `members.service` (nunca importa `members.repository` ni consulta `usuarios` directamente).

Las primitivas de hashing y JWT (sin acceso a BD) viven en `core/security.py`, que se mantiene como hoja del árbol de módulos, sin `Depends` ni lógica de negocio (su propio docstring ya lo decía antes de esta sesión). Las dependencias FastAPI de autorización — `get_current_user`, `require_role` **y** `require_permission` — viven todas juntas en `auth/dependencies.py` (ajuste sobre la primera versión de este plan, que ponía `get_current_user`/`require_role` en `core/security.py`): las tres son "quién es el usuario / qué puede hacer", lógica de `auth`, no utilidad técnica de `core`.

Ya usa realmente **PyJWT** (`pyjwt`, ya en `Pipfile`), no python-jose como decía la versión anterior de este plan — `core/security.py` ya estaba parcialmente implementado con PyJWT antes de esta sesión.

## Implementación

1. Migración Alembic: tablas `permisos` (`id`, `codigo` único, `descripcion`) y `usuario_permisos` (asociación `usuario_id`↔`permiso_id`), con seed de los códigos iniciales `checkin.ver_dispositivos_bloqueados` y `checkin.desbloquear_dispositivo`.
2. `models/permiso.py`: modelo `Permiso` + tabla de asociación `usuario_permisos`.
3. `members/repository.py` + `members/service.py :: get_user_by_email(email, db)` — único punto de acceso que `auth` usa para leer `usuarios`.
4. `core/security.py`: ya tiene `hash_password`/`verify_password` (passlib/bcrypt) y `create_access_token`/`decode_access_token` (PyJWT). Sin cambios — se consume desde `auth/`.
5. `auth/repository.py` (nuevo): `AuthRepository.get_permission_codes(usuario_id) -> set[str]`.
6. `auth/service.py`: `login(email, password, db)` (verifica hash + `rol` en `{empleado, administrador}` + `estado == activo`, emite JWT) y `get_user_permissions(usuario_id, db)`.
7. `auth/dependencies.py` (nuevo): `get_current_user(response, credentials)` (usa `HTTPBearer`, no `OAuth2PasswordBearer`, para no importar nada con semántica OAuth2), `require_role(*roles)`, y `require_permission(*codigos)` — si `rol == administrador` pasa siempre (permisos implícitos); si no, consulta `auth.service.get_user_permissions` y exige intersección no vacía con los códigos requeridos.
8. `auth/schemas.py` + `auth/router.py`: `POST /auth/login`.
9. **Expiración deslizante (RN-11):** `get_current_user` reemite el token con `exp` renovado a +30min en el header de respuesta `X-New-Token` en cada request autenticada válida. Sin actividad 30 min → el token ya vencido → 401, sin renovación.
10. `checkin/router.py`: los dos endpoints marcados `TODO(003)` (`GET /dispositivos-bloqueados`, `POST /desbloquear/{device_id}`) usan `Depends(require_permission(...))` con su código específico, no un rol genérico.
11. Frontend: pantalla de login (solo backoffice) + almacenamiento del token + interceptor Axios que adjunta `Authorization: Bearer` y reemplaza el token guardado cada vez que llega `X-New-Token` en la respuesta.

## Decisiones

- **`auth` con repository propio, pero solo para `permisos`/`usuario_permisos`** — la tabla `User` sigue teniendo único dueño (`members`); `auth` no la toca directo, sigue orquestando sobre `members.service`.
- **Hash con bcrypt vía passlib** — ya implementado en `core/security.py`. Sin texto plano (RN-12).
- **Expiración deslizante confirmada** (no refresh token explícito — ese esquema queda reservado para `011-portal-miembro-autenticacion`, que tiene un propósito distinto). Entregada vía header `X-New-Token`.
- **RBAC por rol** (`require_role`) para chequeos genéricos de claims JWT sin BD, y **permisos por usuario individual** (`require_permission`) para chequeos finos que sí requieren BD — ambos en `auth/dependencies.py`, dos mecanismos separados (no uno solo) porque tienen necesidades de datos distintas.
- **Otorgar permisos a un usuario es CRUD, fuera de `003`** — pertenece a `004-gestion-usuarios`. `003` solo deja el modelo de datos y el mecanismo de verificación listos.
- **`login()` rechaza `estado=inactivo`** y **no revalida sesión activa contra BD** (JWT totalmente stateless entre reemisiones) — ambas decisiones confirmadas con el equipo.

## Riesgos

- **Fuga de secreto JWT** — mitigación: `JWT_SECRET` en `.env`, fuera del repo (límite duro); rotación documentada.
- **HTTPS obligatorio en prod** (RNF) — el JWT viaja en claro si no hay TLS; documentar despliegue tras TLS 1.3.
- **Diferencia inactividad vs. expiración fija** — cubrir con test la renovación deslizante (`X-New-Token` con `exp` mayor tras cada request).
- **Ventana de riesgo tras desactivar a un usuario** — hasta 30 min de JWT válido tras desactivar `estado`, por ser stateless (decisión aceptada explícitamente, no es un descuido).
- **`bcrypt==5.0.0` (pineado en `Pipfile.lock` desde antes de esta sesión) es incompatible con `passlib==1.7.4`** — rompía `hash_password`/`verify_password` con un `ValueError` interno de passlib (self-test de `detect_wrap_bug` falla con bcrypt ≥4.1). Nadie lo había notado porque ningún test anterior a `003` llamaba esas funciones. Corregido pineando `bcrypt<4.1` vía `pipenv install` (no es un cambio de comportamiento de negocio, es una corrección de dependencia rota).

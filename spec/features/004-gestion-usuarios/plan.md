# 004 · Gestión de usuarios — Plan

## Enfoque

El módulo **`members`** es dueño de la tabla `User` y expone el CRUD completo (`router/service/repository/schemas`). Para **asignar/renovar una membresía** (que vive en otra tabla) llama a `membership.service.create_membership(...)` / `renew_membership(...)` — nunca toca la tabla `Membership` ni su repository. El borrado respeta RN-07 anonimizando la fila en vez de eliminarla físicamente. El módulo `auth` (dueño de `permisos`/`usuario_permisos` desde `003`) gana los endpoints para otorgar/quitar permisos individuales.

## Implementación

1. `members/schemas.py`: `UserCreate`, `UserUpdate`, `UserOut` (validación Pydantic; `rol` y `estado` como enums de la constitución).
2. `members/repository.py`: `create`, `get`, `list`, `update`, `anonymize` sobre `User`.
3. `members/service.py`: reglas de negocio del CRUD + `anonymize_user(user_id, db)` (RN-07): vacía `cedula/nombre/email`, marca `estado=Inactivo`, conserva `id`.
4. **Asignar membresía (primera vez):** `members.service.assign_membership(user_id, tipo_id, monto, nota, db)` → delega en `membership.service.create_membership(...)` (crea `Membership` con `visitas_restantes = tipo.visitas_totales`, `cupo_invitados_restantes = tipo.cupo_invitados`, `fecha_inicio = hoy`, fechas según `duracion_dias`, `monto`, `nota`).
5. **Renovar membresía:** `members.service.renew_membership(user_id, tipo_id, monto, nota, db)` → delega en `membership.service.renew_membership(...)`:
   - Busca la `Membership` más reciente del usuario (si no hay ninguna, error — usar "asignar" en su lugar).
   - Calcula `fecha_inicio`: si la anterior tiene `fecha_vencimiento >= hoy` (sigue vigente), `fecha_inicio = fecha_vencimiento_anterior + 1 día`; si no, `fecha_inicio = hoy`.
   - Crea la `Membership` nueva con los valores del `MembershipType` pedido (puede diferir del anterior — upgrade/downgrade permitido), `monto`, `nota`. No modifica la fila anterior.
   - Envuelta en transacción (RN-10): la nueva `Membership` se crea sin tocar la anterior, sin necesidad de lock porque no hay condición de carrera de saldo (a diferencia de `consume_visit`).
6. Migración Alembic: agregar columnas `monto` (`Numeric(10,2)`, NOT NULL) y `nota` (`String`, nullable) a `membresias`. Agregar el código `membership.renovar` al `_CATALOGO_INICIAL` de permisos (mismo patrón que la migración de `003`, `alembic/versions/e57695beaef9_...py`) — nueva migración de datos, no se edita la ya aplicada.
7. Si el usuario es staff con login: `core.security.hash_password` al persistir (RN-12).
8. `members/router.py`: endpoints `POST/GET/PUT/DELETE /users`, `POST /users/{id}/membresias` (asignar), `POST /users/{id}/membresias/renovar`, todos con `Depends(require_role("Empleado","Administrador"))` salvo renovar que usa `Depends(require_permission("membership.renovar"))`.
9. `auth/router.py`: `POST /auth/usuarios/{id}/permisos` (otorgar), `DELETE /auth/usuarios/{id}/permisos/{codigo}` (quitar), `GET /auth/usuarios/{id}/permisos` (listar) — todos `Depends(require_role("Administrador"))`. Reutiliza `auth/repository.py` (dueño de `permisos`/`usuario_permisos` desde `003`).
10. Frontend backoffice: tabla de usuarios densa con filtros + formularios de alta/edición/renovación + UI mínima para otorgar/quitar permisos.

## Decisiones

- **Anonimización en lugar de `DELETE` físico (RN-07)** — preserva la integridad referencial con `CheckIn` (dueño: `checkin`) sin que `members` tenga que tocar esa tabla. Se descarta `ON DELETE SET NULL` porque perdería la asociación histórica útil para estadística.
- **Asignación/renovación de membresía vía `membership.service`** — respeta la regla de módulos (no cruzar a la tabla `Membership`).
- **Snapshot de saldos al asignar/renovar** — `visitas_restantes`/`cupo_invitados_restantes` se copian del `MembershipType` al crear la `Membership`, habilitando RN-06 (cambios del tipo no afectan contratos vigentes).
- **Upgrade/downgrade permitido** — renovar no obliga a mantener el mismo `MembershipType`.
- **Fecha de inicio en renovación anticipada** — si la anterior sigue vigente, la nueva empieza al día siguiente de su vencimiento (no se pierden días pagados); si ya venció, empieza hoy.
- **`membership.renovar` como permiso individual** — sigue el mismo mecanismo de `permisos`/`usuario_permisos` de `003`; `administrador` lo tiene implícito, un `Empleado` necesita que se lo otorguen.
- **Otorgar/quitar permisos vive en `auth`, no en `members`** — `auth` ya es dueño de `permisos`/`usuario_permisos` desde `003` (reutiliza su `repository`, igual que hace con `User` de `members`); `members` no debe tocar esas tablas directamente (regla de módulos).
- **`monto` + `nota` en `Membership`** — trazabilidad interna del cobro en ventanilla, no una integración de pagos real.

## Riesgos

- **PII en logs** — evitar loguear cédula/email; revisar antes de la entrega.
- **Borrado de usuario con membresía activa** — decidir si se bloquea o se anonimiza igualmente; por defecto se permite anonimizar (el histórico se preserva). Documentar.
- **Consistencia de enums** `rol`/`estado` entre backend y frontend.
- **Migración de columnas NOT NULL (`monto`)** sobre `membresias` si ya hay filas existentes (de tests/seed) — definir un default o backfill en la migración para no romper `alembic upgrade head` en un entorno con datos.

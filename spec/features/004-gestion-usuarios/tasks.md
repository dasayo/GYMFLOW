# 004 · Gestión de usuarios — Tareas

## CRUD de usuarios
- [x] `members/schemas.py`: `UserCreate/UserUpdate/UserOut` con enums de `rol`/`estado`.
- [x] `members/repository.py`: `create/get/list/update/anonymize` sobre `User`.
- [x] `members/service.py`: CRUD + `anonymize_user` (RN-07).
- [x] Hash de contraseña al crear staff con login (RN-12, ahora vía `pwdlib`/Argon2).
- [x] `members/router.py`: endpoints CRUD protegidos por `require_role` (RF-09).

## Membresías (asignación y renovación)
- [x] Migración Alembic: columnas `monto` (`Numeric(10,2)`, NOT NULL) y `nota` (nullable) en `membresias`.
- [x] Migración Alembic: agregar código de permiso `membership.renovar` al catálogo (`permisos`), mismo patrón que `003`.
- [x] `members/schemas.py`: `MembershipActionRequest`/`MembershipHistoryItem` (`tipo_id`, `monto`, `nota`, `vigente` calculado).
- [x] `membership/service.py`: `create_membership(user_id, tipo_id, monto, nota, db)` — primera asignación, snapshot de saldos y fechas.
- [x] `membership/service.py`: `renew_membership(user_id, tipo_id, monto, nota, db)` — crea `Membership` nueva, calcula `fecha_inicio` (hoy vs. día siguiente al vencimiento anterior si sigue vigente), no modifica la anterior. Además: `get_active_by_user` corregido para filtrar por ventana de fechas (no solo `estado`), evitando doble-fila-activa tras renovación anticipada.
- [x] `members/service.py`: `assign_membership(...)` / `renew_membership(...)` delegando en `membership.service`.
- [x] `members/router.py`: `POST /usuarios/{id}/membresias` (asignar, `require_role`) y `POST /usuarios/{id}/membresias/renovar` (`require_permission("membership.renovar")`).

## Permisos individuales (otorgar/quitar)
- [x] `auth/router.py`: `POST /auth/usuarios/{id}/permisos`, `DELETE /auth/usuarios/{id}/permisos/{codigo}`, `GET /auth/usuarios/{id}/permisos` — todos `require_role(administrador)`.
- [x] `auth/service.py` + reutilización de `auth/repository.py` (dueño de `permisos`/`usuario_permisos`) para otorgar/quitar/listar.

## Frontend
- [x] Tabla + formularios de usuarios (backoffice denso): alta, edición, borrado. `UsersPage.tsx`.
- [x] Formulario de asignación/renovación de membresía (tipo, monto, nota) + historial. `MembershipPanel.tsx`.
- [x] UI mínima para que un Administrador otorgue/quite `membership.renovar` a un Empleado. `PermissionsPage.tsx`.
- [x] (Fuera del alcance original, pedido durante la implementación) Sidebar de navegación tipo mockup (`StaffLayout.tsx`) reemplazando el menú de cards suelto — ver `AGENTS.md` convención de `staffMenu.ts`.

## Tests
- [x] Alta, edición, borrado → PII eliminada + `CheckIn` conservados (RN-07).
- [x] Asignación de membresía (primera vez): saldos y fechas correctas.
- [x] Renovación: fecha de inicio correcta en ambos casos (anterior vigente vs. vencida), upgrade/downgrade de tipo, `Membership` anterior sin modificar, doble-activa resuelta (regression test explícito).
- [x] Renovación sin permiso `membership.renovar` → 403 (Empleado genérico no puede; `administrador` sí).
- [x] Otorgar/quitar permiso → 403 si no es `administrador`; efecto verificado en un intento de renovación posterior.
- [x] RBAC 401/403 en todos los endpoints nuevos.
- [x] `pytest` completo: 76/76 en verde (contra DB de test aislada, no la de Docker compartida).

## Cierre
- [x] Validar contra los criterios de aceptación de `spec.md`.
- [ ] **Pendiente de confirmación del usuario:** verificación visual en navegador real (no hay herramienta de browser automation disponible en este entorno) — backend verificado con tests + `curl` real end-to-end; frontend verificado con `oxlint`/`tsc` + smoke test de API vía proxy, pero no visualmente.
- [ ] Mover la feature a "Hecho" en `../../constitution/roadmap.md` (dejar para después de la confirmación visual de arriba).

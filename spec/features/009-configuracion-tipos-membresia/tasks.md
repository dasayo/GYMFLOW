# 009 · Configuración de tipos de membresía — Tareas

- [ ] `membership/schemas.py`: `MembershipTypeCreate/Update/Out` con validaciones.
- [ ] `membership/repository.py`: CRUD `MembershipType` + `count_active_memberships_by_type`.
- [ ] `membership/service.py`: `create/update/list_types` + `delete_or_deactivate_type` (RN-05).
- [ ] Confirmar snapshot de saldos en `create_membership` (RN-06) — coordinar con feature 004.
- [ ] `membership/router.py`: CRUD protegido por `require_role("Administrador")` (RF-09).
- [ ] Frontend: tabla + formulario de tipos; motivo de bloqueo RN-05 visible.
- [ ] Tests: crear/editar/listar, bloqueo de borrado y de desactivación con membresía activa (RN-05), editar tipo no altera membresía activa (RN-06), RBAC solo Admin.
- [ ] Validar contra los criterios de aceptación de `spec.md`.
- [ ] Mover la feature a "Hecho" en `../../constitution/roadmap.md`.

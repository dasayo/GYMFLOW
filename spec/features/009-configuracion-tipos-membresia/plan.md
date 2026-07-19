# 009 · Configuración de tipos de membresía — Plan

## Enfoque

Todo ocurre dentro del módulo **`membership`**, dueño de `MembershipType` **y** de `Membership`. La comprobación de RN-05 (¿hay membresías activas del tipo?) es una consulta **intramódulo** (ambas tablas son suyas), así que no cruza fronteras. RN-06 se sostiene por diseño: los saldos viven en `Membership` como **snapshot**, independientes del `MembershipType`.

## Implementación

1. `membership/schemas.py`: `MembershipTypeCreate/Update/Out` (validaciones: `visitas_totales ≥ 0`, `duracion_dias > 0`, etc.).
2. `membership/repository.py`: CRUD de `MembershipType` + `count_active_memberships_by_type(tipo_id)`.
3. `membership/service.py`:
   - `create/update/list_types`.
   - `delete_or_deactivate_type(tipo_id)` → si `count_active_memberships_by_type > 0` → error de negocio (RN-05).
4. **RN-06 por snapshot:** confirmar que `create_membership` (feature 004) copia `visitas_totales→visitas_restantes` y `cupo_invitados→cupo_invitados_restantes` al asignar; editar el tipo nunca toca filas de `Membership`.
5. `membership/router.py`: endpoints CRUD con `Depends(require_role("Administrador"))`.
6. Frontend backoffice: tabla de tipos + formulario; el botón eliminar/desactivar muestra el motivo si RN-05 lo bloquea.

## Decisiones

- **RN-05 como consulta intramódulo** — `membership` posee ambas tablas; no requiere llamar a otro service. Cubre tanto borrado físico como desactivación comercial (`activo=false`).
- **RN-06 por snapshot en `Membership`** — los contratos vigentes son inmutables ante cambios del tipo; se descarta recalcular saldos (rompería contratos vendidos).
- **Solo Administrador** — más restrictivo que el resto del backoffice (que admite Empleado), acorde a HU-08.

## Riesgos

- **Desactivación vs. eliminación** — RN-05 aplica a ambas; asegurarse de cubrir el flag `activo`, no solo el `DELETE`.
- **Tipos huérfanos** — un tipo desactivado sin membresías puede archivarse; no borrar histórico si alguna `Membership` (aunque vencida) lo referencia y se necesita para reportes.

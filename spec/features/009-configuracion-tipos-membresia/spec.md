# 009 · Configuración de tipos de membresía

**Estado:** propuesta

**Traza:** HU-08 · RN-05, RN-06 · RF-11, RF-09 · depende de `003-autenticacion-segura`

## Qué hace

Da al **Administrador** un CRUD del catálogo de **tipos de membresía** (`MembershipType`): nombre, `precio_base`, `visitas_totales`, `cupo_invitados`, `duracion_dias`, `activo`. Impide eliminar/desactivar un tipo que tenga membresías activas vinculadas (RN-05) y asegura que editar sus parámetros no altere los contratos vigentes (RN-06).

> **Aclaración sobre "eliminar" vs "desactivar" (ajuste tras revisión de dominio):** RN-05 en el Análisis solo protege contra membresías **activas**, pero no dice nada de las **históricas**. Con el modelo de `004`/`013` (cada renovación crea una `Membership` nueva, preservando el histórico de precios/planes), **eliminar físicamente** un `MembershipType` que tiene *cualquier* `Membership` histórica vinculada rompería esa trazabilidad. Se separan las dos operaciones:
> - **Desactivar** (`activo = false`, soft): permitido en cuanto no queden `Membership` **activas** vinculadas (tal como decía RN-05 originalmente). Impide asignaciones/renovaciones nuevas con ese tipo, pero el histórico sigue intacto.
> - **Eliminar** (borrado físico de la fila): solo permitido si el tipo **nunca** tuvo ninguna `Membership` (ni activa ni histórica) — es decir, en la práctica, casi nunca aplica una vez el tipo se usó al menos una vez. Si ya tiene historial, la única opción es desactivar.

## Por qué

Permite adaptar las reglas del negocio (planes) sin tocar código y sin romper los contratos ya vendidos. Es la base configurable sobre la que operan las membresías (`004`) y el check-in (`001`).

## Criterios de aceptación

- [ ] Un Administrador puede **crear** un tipo con `nombre`, `precio_base`, `visitas_totales`, `cupo_invitados`, `duracion_dias`, `activo` (RF-11).
- [ ] Un Administrador puede **editar** y **listar** tipos.
- [ ] Intentar **desactivar** un tipo con **≥1 `Membership` activa** vinculada → **rechazado** con motivo claro (RN-05). Sin activas vinculadas → permitido (el histórico, si lo hay, se preserva intacto).
- [ ] Intentar **eliminar** (borrado físico) un tipo con **cualquier** `Membership` vinculada — activa o histórica — → **rechazado** con motivo claro ("este tipo tiene historial, desactívalo en vez de eliminarlo"). Solo se permite eliminar un tipo que nunca se usó.
- [ ] Al **editar** los parámetros de un tipo, las `Membership` activas existentes **conservan sus valores** (no se recalculan `visitas_restantes` ni fechas); los nuevos valores aplican solo a **nuevas membresías / próximos ciclos** (RN-06). *Comprobable: editar `visitas_totales` no cambia el saldo de una membresía activa.*
- [ ] Todos los endpoints exigen rol **Administrador** (RBAC, RF-09).

## Fuera de alcance

- **Asignar** una membresía a un usuario → `004-gestion-usuarios` (aquí se define la plantilla, no se asigna).
- **Facturación/cobro** del `precio_base` → fuera de alcance del producto (misión).

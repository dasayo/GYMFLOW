# 006 · Check-in de invitado — Plan

> **Actualizado tras la implementación (2026-07-20).** El equipo decidió acotar
> el alcance a **solo el "Camino 2"** del `spec.md`: el titular **siempre debe
> estar presente** para hacer entrar a su invitado. Esto **elimina la ventana
> temporal de RN-04** (y sus dudas abiertas de duración / por-dispositivo-o-global)
> y el auto-check-in del invitado (Camino 1), que quedan **fuera del alcance
> entregado**. El plan de abajo refleja lo realmente construido.

## Enfoque

El módulo **`checkin`** orquesta: resuelve al titular vía `members.service`,
valida su membresía y cupo vía `membership.service`, y descuenta el cupo +
registra el `CheckIn` del invitado en **una única transacción** (RN-10). Sin
consultar la tabla `CheckIn` en busca de una ventana temporal (no hay ventana).

## Decisión de modelado (resuelve dos dudas abiertas)

`CheckIn.usuario_id` es un FK **NOT NULL** a `usuarios`, pero un invitado vive
conceptualmente en `invitados`. Decisión del equipo: **la identidad del invitado
es una fila en `usuarios` con `rol=invitado`** (igual que un prospecto en `005`),
creada/reutilizada por `members.service.get_or_create_guest_user`. Con esto:

- No se toca el esquema de `CheckIn`, su índice único parcial ni los reportes (`010`).
- La tabla `invitados` (`Guest`) **queda sin uso** por ahora; su duda de propiedad
  se vuelve irrelevante en este alcance.
- El vínculo invitado↔titular se registra en `CheckIn.titular_id`.

## Implementación (construido)

1. `checkin/schemas.py`: `GuestCheckinRequest` (`cedula_titular`, `cedula_invitado`,
   `nombre_invitado`; valida cédulas 5-15 dígitos, nombre no vacío, y titular ≠
   invitado). Nuevas razones `TITULAR_NO_ENCONTRADO`, `TITULAR_SIN_MEMBRESIA`,
   `SIN_CUPO_INVITADOS`.
2. `members/service.py :: get_or_create_guest_user(cedula, nombre, db)` → fila
   `usuarios` rol=invitado. Flush, no commit.
3. `membership/service.py`:
   - `get_membership_for_guest(titular_id, db)` → membresía activa y no vencida
     del titular, **sin** exigir `visitas_restantes > 0` (el invitado descuenta
     cupo, no las visitas del titular).
   - `consume_guest_slot(membership_id, db)` → `SELECT … FOR UPDATE` + decremento
     de `cupo_invitados_restantes` (RN-09). Flush, no commit.
4. `checkin/service.py :: checkin_guest(cedula_titular, cedula_invitado, nombre, db)`:
   titular no encontrado / sin membresía / sin cupo → Denegado con su razón.
   Si el invitado ya ingresó hoy → éxito idempotente sin re-descontar (Filtro 1,
   análogo a `001`). Si no → **transacción única**: `consume_guest_slot` +
   `CheckIn(usuario_id=invitado, titular_id=titular, Exitoso, is_active=True)` →
   `commit`. `IntegrityError` (carrera del mismo invitado) → `rollback` + éxito
   idempotente.
5. `checkin/router.py :: POST /checkin/guest`, con el guard de dispositivo de
   `002` (RN-03), como el check-in normal del kiosko.
6. Frontend: modo "Ingresar un invitado" en el kiosko (`CheckinKiosk`) — formulario
   con cédula del titular, cédula y nombre del invitado; reutiliza el semáforo
   verde/rojo.

## Decisiones

- **Solo titular presente (sin ventana)** — decisión del equipo; la presencia
  del titular sustituye a la ventana temporal de RN-04, y con ella se evita el
  abuso del cupo sin el titular. Por eso no se implementa el Camino 1.
- **Invitado = fila `usuarios` rol=invitado** — ver "Decisión de modelado".
- **`FOR UPDATE` sobre la membresía del titular** — evita doble descuento del
  cupo en concurrencia (RN-09/RN-10).

## Riesgos / notas

- **Reingreso del mismo invitado el mismo día** → no se descuenta doble (Filtro 1
  + `IntegrityError` como red de seguridad sobre el índice único parcial).
- **Interacción con `005`**: como un invitado queda como `usuarios` registrado,
  una futura cortesía de primer día para esa misma cédula se deniega
  (`YA_REGISTRADO`). Señalado al equipo por si se quiere otro comportamiento.
- **Endpoint sin auth de usuario** (guard de dispositivo, como el kiosko): puede
  crear filas `usuarios` de invitado desde el kiosko. Mismo modelo de confianza
  que el check-in del kiosko; RN-03 sigue aplicando.

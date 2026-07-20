# 006 · Check-in de invitado — Tareas

> **Alcance acotado (decisión del equipo):** solo "Camino 2" (titular siempre
> presente), sin ventana temporal. Por eso las tareas de ventana quedan
> descartadas, no pendientes.

- [x] ~~`core/config.py`: `VENTANA_INVITADO_MIN`.~~ **Descartado:** no hay ventana (titular siempre presente).
- [x] `checkin/schemas.py`: `GuestCheckinRequest` (+ razones `TITULAR_NO_ENCONTRADO`/`TITULAR_SIN_MEMBRESIA`/`SIN_CUPO_INVITADOS`).
- [x] ~~`members/service.py`: `upsert_guest` (entidad `Guest`).~~ **Reemplazado:** `get_or_create_guest_user` (invitado = fila `usuarios` rol=invitado; la tabla `invitados` queda sin uso — ver plan.md).
- [x] `membership/service.py`: `consume_guest_slot(membership_id, db)` con `FOR UPDATE` (RN-09) + `get_membership_for_guest` (activa, sin exigir visitas del titular).
- [x] ~~`checkin/repository.py`: `get_last_successful_member_checkin` (RN-04 ventana).~~ **Descartado:** sin ventana. Se reutiliza `exists_successful_checkin_today` para el reingreso idempotente.
- [x] `checkin/service.py`: `checkin_guest(...)` en una única transacción (RN-10).
- [x] `checkin/router.py`: `POST /checkin/guest` con guard de dispositivo (RN-03, feature 002).
- [x] Frontend: modo "Ingresar un invitado" en el kiosko (`CheckinKiosk`).
- [x] Tests: éxito descuenta 1 cupo (atómico), cupos=0→denegado, titular vencido→denegado, titular no encontrado→denegado, titular sin visitas pero con cupo→ok, reingreso no descuenta doble, 422 (titular=invitado / cédula inválida). *(7 de servicio + 4 de router.)*
- [x] Validar contra los criterios de aceptación de `spec.md` (ver nota abajo).
- [x] Mover la feature a "Hecho" en `../../constitution/roadmap.md`.

> **Criterios de aceptación:** se cumplen los que aplican al Camino 2 — descuento
> de exactamente 1 cupo (crit. 1, sin la parte de "dentro de la ventana"),
> transacción única (crit. 4), titular inactivo/vencido o cupo=0 → denegado sin
> descontar (crit. 5), mensaje con cupos restantes (crit. 6), titular puede hacer
> entrar al invitado en persona siempre (crit. 3). **NO** entregados: crit. 2
> (denegar al invitado que entra solo fuera de ventana) y la auto-identificación
> del invitado del crit. 1 — ambos pertenecen al Camino 1, fuera del alcance
> acordado.

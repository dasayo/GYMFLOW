# 005 · Cortesía de primer día — Tareas

- [x] `members/service.py`: `create_prospect(...)`. *(Sin `has_used_courtesy`: `checkin.service` lee el flag `cortesia_usada` directo del `User` que devuelve `get_user_by_cedula`, sin un método redundante.)*
- [x] `models/` + migración: flag `cortesia_usada` en `User` (migración `27f9ec997e70`). El índice único por `cedula` ya venía de `004`.
- [x] `checkin/service.py`: `first_day_courtesy(...)` en una única transacción (RN-10).
- [x] ~~Enrutar en `checkin.service.checkin_member`: cédula inexistente → cortesía.~~ **Descartado:** la cortesía es un flujo de Staff (backoffice), no del kiosko (ver `spec.md`, "Cambio de canal"). Se expone en `POST /checkin/cortesia` con RBAC, no en el check-in del kiosko.
- [x] `checkin/repository.py`: insertar `CheckIn` de cortesía (Exitoso) y de denegación (`CORTESIA_YA_UTILIZADA`). *(Se reutilizó `CheckinRepository.insert` existente.)*
- [x] Frontend: página `/staff/cortesia` con semáforo de cortesía + CTA de afiliación, en el menú de staff.
- [x] Tests: primera cortesía crea prospecto + CheckIn (atómico), segundo intento denegado, ya-registrado denegado, RBAC 401/403, validación 422. *(5 de servicio + 6 de router.)*
- [x] Validar contra los criterios de aceptación de `spec.md` — 5/5 cumplidos (ver nota abajo).
- [x] Mover la feature a "Hecho" en `../../constitution/roadmap.md`.

> **Criterio 4 (afiliación reutiliza los datos del Prospecto):** se cumple vía los
> endpoints de `004` — el Prospecto ya es un `User`, así que el Staff le cambia el
> `rol` a miembro y le asigna membresía sobre la misma fila (no se re-digitan datos
> ni se crea un usuario nuevo). El flag `cortesia_usada` persiste para no reconceder
> la cortesía.

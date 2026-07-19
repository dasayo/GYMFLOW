# 006 · Check-in de invitado — Tareas

- [ ] `core/config.py`: parámetro `VENTANA_INVITADO_MIN` (default 10).
- [ ] `checkin/schemas.py`: `GuestCheckinIn`.
- [ ] `members/service.py`: `upsert_guest(...)` (entidad `Guest`).
- [ ] `membership/service.py`: `consume_guest_slot(membership_id, db)` con `FOR UPDATE` (RN-09).
- [ ] `checkin/repository.py`: `get_last_successful_member_checkin(titular_id, device_id)` (RN-04).
- [ ] `checkin/service.py`: `checkin_guest(...)` en una única transacción (RN-10) con validación RN-04.
- [ ] `checkin/router.py`: `POST /checkin/guest` con guard de dispositivo (RN-03, feature 002).
- [ ] Frontend: flujo de invitado con confirmación del titular.
- [ ] Tests: éxito descuenta 1 cupo (atómico), titular fuera de ventana→denegado, cupos=0→denegado, titular vencido→denegado, rollback, concurrencia sobre cupos.
- [ ] Validar contra los criterios de aceptación de `spec.md`.
- [ ] Mover la feature a "Hecho" en `../../constitution/roadmap.md`.

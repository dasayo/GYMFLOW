# 005 · Cortesía de primer día — Tareas

- [ ] `members/service.py`: `create_prospect(...)` y `has_used_courtesy(...)`.
- [ ] `models/` + migración: flag `cortesia_usada` en `User` (+ índice único por `cedula`).
- [ ] `checkin/service.py`: `first_day_courtesy(...)` en una única transacción (RN-10).
- [ ] Enrutar en `checkin.service.checkin_member`: cédula inexistente → cortesía.
- [ ] `checkin/repository.py`: insertar `CheckIn` de cortesía (Exitoso) y de denegación ("ya utilizada").
- [ ] Frontend: semáforo de bienvenida de cortesía + CTA de afiliación.
- [ ] Tests: primera cortesía crea prospecto + CheckIn (atómico), segundo intento denegado, rollback ante fallo, doble kiosko misma cédula.
- [ ] Validar contra los criterios de aceptación de `spec.md`.
- [ ] Mover la feature a "Hecho" en `../../constitution/roadmap.md`.

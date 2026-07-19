# 001 · Check-in con membresía activa — Tareas

_Checklist accionable derivada del `plan.md`._

- [x] `models/`: confirmar modelos `User`, `Membership`, `MembershipType`, `CheckIn` alineados con la constitución.
- [x] `membership/service.py`: `get_active_membership(user_id, db)` con validación RN-01.
- [x] `membership/service.py`: `consume_visit(membership_id, db)` con `SELECT … FOR UPDATE` + decremento (RN-08).
- [x] `members/service.py`: `get_user_by_cedula(cedula, db)`.
- [x] `checkin/repository.py`: `exists_successful_checkin_today(...)` e `insert(CheckIn, db)`.
- [x] `checkin/service.py`: `checkin_member(...)` orquestando todo en una sola transacción (RN-10).
- [x] `checkin/schemas.py` + `checkin/router.py`: `POST /checkin` (cédula) con validación Pydantic.
- [x] Migración Alembic: índice único parcial `(usuario_id, fecha)` para check-ins exitosos.
- [x] Frontend: pantalla de cédula + semáforo verde (botones ≥48×48px, legible a 1m).
- [x] Tests: éxito, descuento exacto de 1 visita, rollback ante fallo de descuento, doble check-in mismo día, concurrencia (10 simultáneos).
- [x] Validar contra los criterios de aceptación de `spec.md`.
- [x] Mover la feature a "Hecho" en `../../constitution/roadmap.md`.

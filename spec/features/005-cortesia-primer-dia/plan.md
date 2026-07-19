# 005 · Cortesía de primer día — Plan

## Enfoque

Es una **rama del flujo de check-in** del módulo `checkin`: cuando `members.service.get_user_by_cedula` no encuentra al usuario, `checkin.service` invoca la cortesía. La creación del prospecto (tabla `User`, dueño `members`) y el `CheckIn` (dueño `checkin`) se confirman en **una sola transacción** (RN-10) coordinada por `checkin.service`.

## Implementación

1. `members/service.py`: `create_prospect(cedula, nombre|None, db)` → crea `User` (rol `Invitado`, flag `cortesia_usada=True`, `estado=Activo`). Y `has_used_courtesy(cedula, db)`.
2. `checkin/service.py :: first_day_courtesy(cedula, db)`:
   1. Si `members.service.has_used_courtesy(cedula)` → **Denegado** ("cortesía ya utilizada"), registrar `CheckIn` Denegado.
   2. Si no: **transacción única** → `members.service.create_prospect(...)` + `checkin.repository.insert(CheckIn Exitoso, tipo=cortesía)` → `commit`. Ante fallo → `rollback`.
3. `checkin/service.py :: checkin_member` (feature 001) enruta a `first_day_courtesy` cuando la cédula no existe.
4. Frontend: semáforo verde con mensaje de cortesía + CTA de afiliación para el staff.

## Decisiones

- **Prospecto = flag sobre `User`, no nuevo valor de enum** — evita alterar el enum `rol` de la constitución; `cortesia_usada` es suficiente para impedir la segunda cortesía. Marcado como duda a confirmar.
- **Transacción coordinada por `checkin`** — mismo patrón de sesión compartida que `001` (RN-10).
- **Impedir segunda cortesía por cédula** (no por `id`) — la cédula es el identificador natural del kiosko.

## Riesgos

- **Colisión de cédula** entre prospecto y futura alta formal — al afiliar en `004`, reutilizar la misma fila (upsert por cédula) en vez de duplicar.
- **Nombre ausente del prospecto** — permitir `nombre` nulo temporal; documentar completado por staff.
- **Carrera de dos kioskos con la misma cédula nueva** — índice único por `cedula` en `User` evita el doble alta.

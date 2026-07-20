# 005 · Cortesía de primer día — Plan

> **Actualizado tras la implementación (2026-07-20).** La versión anterior de
> este plan describía la cortesía como una rama del check-in **del kiosko**
> (cuando la cédula no existe, `checkin_member` la enrutaba a la cortesía). Eso
> quedó **superado** por la decisión del equipo registrada en `spec.md`
> ("Cambio de canal"): la cortesía la registra el **Staff desde el backoffice**,
> no el kiosko self-service. El plan de abajo refleja lo realmente construido.

## Enfoque

La cortesía es un flujo de **Staff** coordinado por `checkin.service`, expuesto
en un endpoint autenticado del backoffice (no en el kiosko). La creación del
Prospecto (tabla `User`, dueño `members`) y del `CheckIn` (dueño `checkin`) se
confirman en **una sola transacción** (RN-10) que hace `commit` `checkin.service`
—mismo patrón que `consume_visit` en el flujo de `001` (los services de otros
módulos hacen `flush`, el orquestador `commit`).

## Implementación (construido)

1. `models/User`: columna `cortesia_usada: bool` (default false). Un **Prospecto**
   es un `User` con `rol=invitado` + `cortesia_usada=True` (decisión del equipo
   sobre la duda abierta: flag, no un valor de enum nuevo). Migración Alembic
   `27f9ec997e70`. El índice único de `usuarios.cedula` ya existía de `004`.
2. `members/service.py :: create_prospect(cedula, nombre, db)` → crea el `User`
   Prospecto. Hace `flush`, **no** `commit` (atomicidad la cierra `checkin`).
3. `checkin/service.py :: first_day_courtesy(cedula, nombre, db)`:
   1. Cédula ya existe con `cortesia_usada=True` → **Denegado** (`CORTESIA_YA_UTILIZADA`),
      registra `CheckIn` Denegado (rastro auditable).
   2. Cédula ya existe sin cortesía usada (socio/staff real) → **Denegado**
      (`YA_REGISTRADO`), sin persistir `CheckIn` (no es abuso, la cortesía no aplica).
   3. Cédula nueva → **transacción única**: `create_prospect` + `CheckIn` Exitoso
      (`is_active=True`) → `commit`. Ante `IntegrityError` (carrera por la misma
      cédula) → `rollback` + `YA_REGISTRADO`.
4. `checkin/router.py :: POST /checkin/cortesia`, gateado con
   `require_permission("members.gestionar_usuarios")` (crea un `User`, mismo
   permiso que el CRUD de `004`). Validación de cédula/nombre en `CortesiaRequest`
   (Pydantic), no en el router.
5. Frontend: página `/staff/cortesia` (backoffice), entrada en el menú de staff
   con el mismo permiso; semáforo verde/rojo con el motivo y CTA de afiliación.

## Decisiones

- **Canal Staff, no kiosko** — ver `spec.md`. Resuelve el riesgo de abuso de un
  self-service sin verificación de identidad; por eso RN-03 (bloqueo de
  dispositivo del kiosko) no aplica a este endpoint.
- **Prospecto = `rol=invitado` + flag `cortesia_usada`** — confirmado con el
  equipo. `rol=invitado` no lo usaba ninguna fila real (los invitados de socio
  viven en la tabla `Guest` de `006`), así que no colisiona.
- **Transacción coordinada por `checkin`** — mismo patrón de `001` (RN-10).
- **Impedir segunda cortesía por cédula** (el identificador natural), vía el flag.

## Riesgos

- **Colisión de cédula** entre prospecto y futura alta formal → al afiliar en
  `004` se **reutiliza la misma fila** (se cambia `rol` a miembro y se asigna
  membresía); el flag `cortesia_usada` persiste para no reconceder cortesía.
- **Carrera de dos registros con la misma cédula nueva** → índice único por
  `cedula` en `User` + captura de `IntegrityError` → `YA_REGISTRADO`.

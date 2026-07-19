# 006 · Check-in de invitado — Plan

## Enfoque

El módulo **`checkin`** orquesta: resuelve al titular vía `members.service`, valida su membresía y cupos vía `membership.service`, comprueba la **ventana temporal de RN-04** consultando su **propia** tabla `CheckIn` (el último check-in exitoso del titular), y descuenta el cupo vía `membership.service` — todo en **una única transacción** (RN-10). El `Guest` se registra/consulta vía `members.service`.

## Implementación

1. `checkin/schemas.py`: `GuestCheckinIn` (cédula/datos del invitado + cédula del titular).
2. `checkin/service.py :: checkin_guest(datos, db)`:
   1. `members.service.get_user_by_cedula(titular_cedula, db)` → titular.
   2. `membership.service.get_active_membership(titular_id, db)` → valida activa + `cupo_invitados_restantes > 0` (RN-04).
   3. **RN-04 ventana:** `checkin.repository.get_last_successful_member_checkin(titular_id, device_id, db)`; si no existe o está fuera de la ventana (`> VENTANA_INVITADO`) → **Denegado**.
   4. `members.service.upsert_guest(datos_invitado, titular_id, db)` → registra/recupera `Guest`.
   5. **Transacción única:** `membership.service.consume_guest_slot(membership_id, db)` (`SELECT … FOR UPDATE` + decremento de `cupo_invitados_restantes`) **+** `checkin.repository.insert(CheckIn Exitoso, usuario_id=invitado, titular_id)` → `commit`; ante fallo → `rollback`.
3. `checkin/router.py`: `POST /checkin/guest`, protegido por el guard de dispositivo de la feature `002` (RN-03).
4. `core/config.py`: parámetro `VENTANA_INVITADO_MIN` (default 10).
5. Frontend: flujo de invitado en el kiosko con confirmación del titular.

## Decisiones

- **RN-04 como ventana temporal sobre el último check-in del titular** — se interpreta "justo después" como: el titular hizo check-in exitoso en el mismo dispositivo dentro de `VENTANA_INVITADO_MIN`. Se descarta validar solo cupos (incumpliría RN-04). **Duración marcada como duda abierta.**
- **`Guest` gestionado por `members`** — es un registro de persona; `checkin` lo pide vía `members.service`. Duda de propiedad marcada.
- **`FOR UPDATE` sobre la membresía del titular** — evita descontar el mismo cupo dos veces en concurrencia (RN-09/RN-10).

## Riesgos

- **Ventana mal definida** → falsos positivos/negativos; mitigar con parámetro configurable + tests de tiempo inyectable.
- **Titular y invitado en dispositivos distintos** → decisión inicial: la ventana es por dispositivo; documentar y confirmar.
- **Regla de módulos** → `checkin` nunca consulta `Membership` ni `User` directamente; solo `*.service`.

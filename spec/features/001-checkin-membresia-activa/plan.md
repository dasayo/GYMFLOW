# 001 · Check-in con membresía activa — Plan

_Cómo se implementa lo descrito en `spec.md`. Respeta `constitution/tech-stack.md`._

## Enfoque

El módulo **`checkin`** (dueño de la tabla `CheckIn`) **orquesta** el flujo pero no consulta tablas ajenas: resuelve al usuario vía `members.service` y valida/descuenta la membresía vía `membership.service`. La atomicidad (RN-10) se garantiza propagando **una única `Session` de SQLAlchemy** a través de las llamadas entre servicios, de modo que el descuento de la visita y la inserción del `CheckIn` se confirmen (`commit`) o se reviertan (`rollback`) juntos en el orquestador.

## Implementación

1. **Endpoint** `POST /checkin` (cédula) — `checkin/router.py`. Valida entrada con Pydantic (`checkin/schemas.py`), nunca a mano en el router.
2. `checkin/service.py :: checkin_member(cedula, db)`:
   1. `members.service.get_user_by_cedula(cedula, db)` → usuario. Si no existe → se delega a cortesía (`005`), fuera de alcance aquí.
   2. `membership.service.get_active_membership(user_id, db)` → aplica RN-01 (activa + `visitas_restantes > 0`).
   3. `checkin.repository.exists_successful_checkin_today(user_id, hoy, db)` (tabla propia `CheckIn`) → RN-02.
   4. **Transacción única:** `membership.service.consume_visit(membership_id, db)` (hace `SELECT … FOR UPDATE` + decremento sobre `Membership`, tabla propia de `membership`) **+** `checkin.repository.insert(CheckIn Exitoso, db)`; el orquestador hace `commit`. Ante cualquier excepción → `rollback`.
   5. Construye la respuesta del semáforo con `membership.service.get_membership_summary(...)` (reutilizado por `007`).
3. **Zona horaria** para "día calendario": `America/Bogota`, centralizada en `core/config.py`.
4. **Frontend kiosko** (`React + Vite + Tailwind`): pantalla de cédula → llamada a la API (React Query + Axios) → semáforo verde. Botones ≥48×48px, alto contraste.

## Decisiones

- **Sesión compartida entre servicios para atomicidad** — se pasa la `Session` (dependencia `get_db` de FastAPI) a cada `service` para que todos se enlisten en la misma transacción; el `commit`/`rollback` lo hace solo el orquestador (`checkin.service`). Se descarta que cada módulo abra su propia transacción, porque rompería RN-10.
- **`SELECT … FOR UPDATE` sobre la fila de `Membership`** — serializa descuentos concurrentes (RNF ≥10 concurrencia) evitando doble descuento. Se descarta el optimistic-locking por simplicidad y por el requisito ACID explícito.
- **RN-02 reforzado con índice único parcial** sobre `(usuario_id, fecha)` para `CheckIn` exitosos, además del chequeo en transacción, para blindar contra carreras.

## Riesgos

- **Doble check-in concurrente** — mitigado con `FOR UPDATE` + índice único parcial.
- **Timezone / cambio de día** — mitigado fijando TZ del gimnasio en config; los tests usan una fecha/hora inyectable.
- **Fuga de la regla de módulos** — `checkin` nunca importa `membership.repository` ni `members.repository`; revisión de PR verifica que solo se llaman `*.service`.

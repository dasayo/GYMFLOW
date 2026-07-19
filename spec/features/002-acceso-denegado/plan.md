# 002 · Acceso denegado — Plan

## Enfoque

Reutiliza el flujo de validación de `001` en el módulo **`checkin`**: cuando `RN-01`/`RN-02` no se cumplen, en lugar de descontar se persiste un `CheckIn` **Denegado** con su `razon_denegacion` y se devuelve el semáforo rojo. El control **RN-03** se implementa como una **dependencia de FastAPI** (`enforce_device_not_locked`) sobre los endpoints de check-in, con un contador de fallos consecutivos por dispositivo persistido en una **tabla propia de `checkin`** (no en memoria, para ser correcto con múltiples workers en Docker).

## Implementación

1. `checkin/service.py :: checkin_member(...)`: extender el resultado de validación para devolver `Denegado` + `razon_denegacion` en vez de lanzar excepción genérica.
2. `checkin/schemas.py`: enum `RazonDenegacion` (`MEMBRESIA_VENCIDA`, `SIN_VISITAS`, `CEDULA_NO_ENCONTRADA`, `DISPOSITIVO_BLOQUEADO`). **`YA_INGRESO_HOY` no existe** — un reingreso el mismo día es Exitoso (ver `001`), no una razón de denegación.
3. `models/`: tabla `CheckinDeviceLock` (propia de `checkin`): `device_id`, `intentos_fallidos`, `ventana_inicio`, `bloqueado_hasta`.
4. `checkin/repository.py`: `register_failed_attempt(device_id, now)`, `reset_attempts(device_id)`, `is_locked(device_id, now)`.
5. `checkin/router.py`: dependencia `enforce_device_not_locked` (lee `X-Device-Id`, fallback IP) aplicada a `POST /checkin` (y a `006`).
6. En cada resultado **Denegado** → `register_failed_attempt`; en cada **Exitoso** → `reset_attempts`. Al superar 3 fallos en ventana ≤5 min → set `bloqueado_hasta = now + 20 min`.
7. Frontend: semáforo rojo con motivo + pantalla de bloqueo con cuenta regresiva.

## Decisiones

- **Contador en tabla, no en memoria** — con varios workers/uvicorn en Docker un contador en RAM sería inconsistente. Se descarta memoria/Redis (no está en el stack) a favor de una tabla del propio módulo.
- **Identidad de dispositivo = `X-Device-Id` con fallback a IP** — el kiosko envía un id estable; la IP sola es frágil (NAT). **Marcado como duda abierta** para confirmar con el equipo.
- **`razon_denegacion` como enum** — habilita métricas y mensajes consistentes; se descarta texto libre por trazabilidad.

## Riesgos

- **Ventana deslizante mal calculada** (reinicio de los 5 min) — cubrir con tests de tiempo inyectable.
- **Bloqueo legítimo molesto** (staff atascado) — mitigación: el staff autenticado (feature `003`) puede resetear el bloqueo desde backoffice (endpoint protegido por rol).
- **Consistencia con RN-10** — el registro del intento denegado nunca debe tocar saldos; se cubre con test.

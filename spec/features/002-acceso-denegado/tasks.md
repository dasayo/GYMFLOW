# 002 · Acceso denegado — Tareas

- [x] `checkin/schemas.py`: enum `RazonDenegacion` (`MEMBRESIA_VENCIDA`, `SIN_VISITAS`, `CEDULA_NO_ENCONTRADA`, `DISPOSITIVO_BLOQUEADO` — sin `YA_INGRESO_HOY`) + DTO de respuesta denegada.
- [x] `checkin/service.py`: devolver `Denegado` + motivo para RN-01 inversa (`MEMBRESIA_VENCIDA`/`SIN_VISITAS`) y formato de cédula inválido (`CEDULA_NO_ENCONTRADA`).
- [x] `models/` + migración Alembic: tabla `CheckinDeviceLock`.
- [x] `checkin/repository.py`: `register_failed_attempt`, `reset_attempts`, `is_locked`.
- [x] `checkin/router.py`: dependencia `enforce_device_not_locked` (X-Device-Id / IP) en endpoints de check-in.
- [x] Lógica RN-03: 3 fallos en ≤5 min → `bloqueado_hasta = now+20min`; éxito resetea contador. Solo cuentan denegaciones por `CEDULA_NO_ENCONTRADA`.
- [x] Endpoint para **desbloquear** dispositivo manualmente — implementado sin guard de rol todavía (`# TODO(003)`: agregar `Depends` de rol Staff cuando exista la feature `003-autenticacion-segura`).
- [x] `GET /checkin/dispositivos-bloqueados` — lista `device_id`/`intentos_fallidos`/`bloqueado_hasta` de los bloqueados vigentes; sin esto no había forma de saber qué `device_id` pasarle al endpoint de desbloqueo (no hay panel de staff todavía). Mismo `# TODO(003)` de guard de rol pendiente.
- [x] Frontend: semáforo rojo con motivo + pantalla de bloqueo con cuenta regresiva.
- [x] Tests: vencida, sin visitas, 3 fallos→bloqueo, éxito resetea, denegado no toca saldos, ventana de 5 min expira el conteo. *(No aplica "ya ingresó hoy": ya no es una razón de denegación, ver `001`.)*
- [x] Validar contra los criterios de aceptación de `spec.md`.
- [x] Mover la feature a "Hecho" en `../../constitution/roadmap.md`.

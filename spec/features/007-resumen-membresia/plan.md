# 007 · Resumen de membresía — Plan

> Reescrito el 2026-07-11: la versión anterior proponía `proximo_pago` (eliminado del `spec.md` — GymFlow no procesa pagos) y un endpoint público del kiosko por cédula (descartado por el equipo: el resumen vive detrás del login del Miembro de `011`).

## Enfoque

Lógica de **lectura** en el módulo **`membership`** (dueño de `Membership` y `MembershipType`), expuesta al Miembro autenticado del portal (`011`) vía `GET /membresias/me/resumen`. El `user_id` sale del JWT del Miembro — nunca de un query param. `checkin` sigue usando el `MembershipSummary` mínimo de `001` para el semáforo; no se toca.

## Implementación

1. `membership/schemas.py :: MembershipSummaryOut` — `tipo`, `estado` (`activa`/`vencida`/`sin_plan`), `fecha_vencimiento`, `visitas_restantes`, `cupo_invitados_restantes`, `dias_restantes` (calculado, no almacenado; `None` si vencida/sin plan). Sin PII innecesaria.
2. `membership/service.py :: get_membership_summary_detail(user_id, db)` — usa `MembershipRepository.get_latest_by_user` para devolver un resumen coherente también cuando la membresía está vencida o el usuario nunca tuvo plan (nunca 404/500 hacia el portal). Solo lectura: no descuenta visitas/cupos ni registra `CheckIn`.
3. `membership/router.py :: GET /membresias/me/resumen` — protegido con `require_member` (dependencia nueva de `011`).
4. Frontend: tarjeta de resumen en el **Dashboard del portal** (`011`), con aviso de vencimiento solo si `0 ≤ dias_restantes ≤ 10`.

## Decisiones

- **Resumen en `membership`, portal como consumidor** — la información pertenece al dominio de membresías; el módulo `auth` solo aporta la identidad (regla de módulos).
- **`dias_restantes` se calcula en el backend** (`fecha_vencimiento - hoy`, con el `hoy()` canónico del módulo); el frontend solo decide mostrar u ocultar el aviso según el umbral de 10.
- **Sin `proximo_pago`** — el sistema no cobra (misión); el dato honesto es cuánto falta para el vencimiento.
- **El kiosko no consulta este endpoint** — el flujo del kiosko (cédula → semáforo) es de `001`/`002` y ya incluye las visitas restantes en el mensaje de éxito.

## Riesgos

- **Miembro sin membresía** → DTO con `estado="sin_plan"`, no error, para que el Dashboard renderice un estado vacío amable.
- **Orden de dependencia** → requiere `require_member` de `011`; este plan se implementa después de la base de auth de esa feature.

# 007 · Resumen de membresía — Tareas

> Reescritas el 2026-07-11 junto con `plan.md` (canal: portal del Miembro, no kiosko).

- [x] `membership/schemas.py`: `MembershipSummaryOut` (tipo, estado, fecha_vencimiento, visitas_restantes, cupo_invitados_restantes, dias_restantes).
- [x] `membership/service.py`: `get_membership_summary_detail(user_id, db)` (solo lectura, RF-04; coherente para activa/vencida/sin plan — revalida `fecha_vencimiento` porque `get_active_by_user` no la filtra a propósito).
- [x] `membership/router.py`: `GET /membresias/me/resumen` con `require_member` (dependencia de 011).
- [x] Frontend: tarjeta de resumen en el Dashboard del portal (011) + aviso solo si `0 ≤ dias_restantes ≤ 10` (`PortalDashboard.tsx`).
- [x] Tests: miembro activo (valores exactos), vencido, sin plan; borde del aviso (11/10/0); lectura sin efectos colaterales (visitas/cupos intactos, cero `CheckIn` nuevos); 401/403 sin JWT de Miembro o con JWT de staff. `membership/test_summary.py`, dentro de los 117/117 en verde.
- [x] Validar contra los criterios de aceptación de `spec.md` (verificado también end-to-end con `curl` a través del proxy nginx del stack Docker).
- [ ] **Pendiente de confirmación del usuario:** verificación visual del Dashboard en navegador real.
- [ ] Mover la feature a "Hecho" en `../../constitution/roadmap.md` (tras la confirmación visual).

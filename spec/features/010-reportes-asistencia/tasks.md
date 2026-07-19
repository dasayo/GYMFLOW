# 010 · Reportes de asistencia — Tareas

- [ ] `checkin/service.py`: `get_attendance(fecha_inicio, fecha_fin, db)` sobre la tabla propia `CheckIn` (RF-12).
- [ ] Migración: índice por `fecha_hora` en `CheckIn`.
- [ ] `reports/schemas.py`: `AttendanceRow`, `ReportFilters`.
- [ ] `reports/service.py`: `generate(...)` (orquesta checkin + enriquece con members/membership).
- [ ] `reports/service.py`: `export(...)` a XLSX (openpyxl) y CSV (RF-13).
- [ ] `reports/router.py`: `GET /reports/attendance` y `.../export` con `require_role("Administrador")` (RF-09).
- [ ] Enriquecimiento en lote (evitar N+1).
- [ ] Frontend: selector de rango + tabla + exportación.
- [ ] Confirmar con el equipo la discrepancia `reports/repository` vs. límite duro (posible ajuste de `tech-stack.md`).
- [ ] Tests: filtro por rango, rango vacío, export XLSX/CSV con mismos datos, RBAC solo Admin, inmutabilidad (no escribe).
- [ ] Validar contra los criterios de aceptación de `spec.md`.
- [ ] Mover la feature a "Hecho" en `../../constitution/roadmap.md`.

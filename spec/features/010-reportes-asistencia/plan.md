# 010 · Reportes de asistencia — Plan

## Enfoque

Para respetar el **límite duro** de la regla de módulos, la **agregación de asistencias vive en el módulo dueño de `CheckIn`** (`checkin.service.get_attendance(filtros)`), y el módulo **`reports`** orquesta: pide los datos a `checkin.service`, los **enriquece** con `members.service` (nombres) y `membership.service` (tipo de plan), y produce la salida tabular y los ficheros de exportación. Esto resuelve la discrepancia entre el `reports/repository` descrito en `tech-stack.md` y el límite duro; **se marca para confirmar** con el equipo y, si procede, ajustar `tech-stack.md`.

## Implementación

1. `checkin/service.py :: get_attendance(fecha_inicio, fecha_fin, db)` → filas de `CheckIn` en el rango (consulta sobre su **propia** tabla). Índice por `fecha_hora`.
2. `reports/schemas.py`: `AttendanceRow`, `ReportFilters`.
3. `reports/service.py :: generate(filtros, db)`:
   - `checkin.service.get_attendance(...)` → filas base.
   - Enriquecer: `members.service.get_users_by_ids(...)` (nombres) y `membership.service.get_types_by_user(...)` (tipo).
   - Devuelve la tabla consolidada.
4. `reports/service.py :: export(filtros, formato)` → `xlsx` (openpyxl) o `csv` (módulo `csv`) del mismo dataset (RF-13).
5. `reports/router.py`: `GET /reports/attendance` (JSON) y `GET /reports/attendance/export?format=xlsx|csv`, con `Depends(require_role("Administrador"))`.
6. Frontend backoffice: selector de rango + tabla + botones de exportación.

> **Nota:** con esta resolución, `reports` **no** necesita `repository.py` propio (no posee tablas). Si el equipo prefiere mantener el `reports/repository` de `tech-stack.md`, habría que relajar el límite duro para lecturas agregadas de solo lectura — decisión a tomar explícitamente.

## Decisiones

- **Agregación en `checkin.service`, orquestación/export en `reports`** — honra el límite duro "no cruzar tablas ajenas". Alternativa (repository de `reports` sobre `CheckIn`) descartada por chocar con la regla no negociable; se marca la discrepancia de la constitución.
- **Export con openpyxl (XLSX) + `csv` estándar** — sin dependencias pesadas; alineado con el stack Python.
- **Fuente inmutable** — el reporte solo lee `CheckIn`; nunca escribe.

## Riesgos

- **Rangos amplios / muchos registros** → paginar la consulta y hacer streaming en la exportación para no agotar memoria.
- **Coste de enriquecimiento N+1** → traer usuarios/tipos en lote por ids, no uno a uno.
- **Discrepancia de constitución sin resolver** → bloquear el "Hecho" hasta confirmarla con el equipo.

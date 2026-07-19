# 010 · Reportes de asistencia

**Estado:** propuesta

**Traza:** HU-09 · RF-12, RF-13 · RF-05 (fuente inmutable), RF-09 · depende de `003-autenticacion-segura`

## Qué hace

Da al **Administrador** un reporte histórico de asistencias filtrable por **rango de fechas** (Fecha Inicio – Fecha Fin) y la posibilidad de **exportarlo a `.XLSX` y `.CSV`**.

## Por qué

Convierte el histórico inmutable de `CheckIn` en información para decisiones de negocio (aforo, conversión de prospectos, uso por plan). Cierra la trazabilidad HU-09 → RF-12/RF-13.

## Criterios de aceptación

- [ ] Un Administrador filtra por Fecha Inicio–Fecha Fin y obtiene una **tabla consolidada** de asistencias (fecha/hora, usuario, resultado, tipo de membresía, titular si es invitado) (RF-12).
- [ ] **La unidad de conteo es "día de asistencia", no "evento de entrada".** Con el modelo `isActive` de `001`, un socio puede tener varios `CheckIn` el mismo día (solo el primero descuenta visita). El reporte cuenta **un `CheckIn` con `isActive = true` por día por usuario** como una asistencia — los reingresos del mismo día (`isActive = false`) **no** suman como asistencias adicionales en el conteo principal, para no inflar métricas como "visitas por socio en el mes".
- [ ] El reporte filtrado se puede **exportar a `.XLSX`** y a **`.CSV`** con los mismos datos mostrados (RF-13).
- [ ] Los datos provienen de `CheckIn` (registro **inmutable**, RF-05) y **no** se alteran al reportar.
- [ ] Solo rol **Administrador** puede acceder (RBAC, RF-09).
- [ ] Un rango sin registros devuelve un reporte vacío coherente (no error).

## Fuera de alcance

- **Dashboards** en tiempo real o gráficos → no está en `docs/` (solo tabla + export).
- **Generación** de los check-ins → `001`/`002`/`005`/`006`.
- **Métrica de "reingresos" (quién entra más de una vez al día)** — es un dato que sí existe en `CheckIn` (todas las filas, no solo `isActive=true`) y podría ser útil a futuro, pero no forma parte de lo que se necesita reportar ahora. Si el equipo lo pide más adelante, es una consulta adicional sobre los mismos datos, no un cambio de modelo.
- **Discrepancia de la constitución (marcar con el equipo):** `tech-stack.md` describe un `reports/repository.py` con "lectura agregada sobre `CheckIn`", pero `CheckIn` es propiedad del módulo `checkin` y el **límite duro** prohíbe "queries cruzadas entre tablas de distintos módulos saltándose el service del módulo dueño". Ver la resolución propuesta en el plan.

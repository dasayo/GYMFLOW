# 013 · Logros por racha de asistencia

**Estado:** propuesta

**Traza:** ⚠️ **Sin HU/RN/RF de origen en `docs/`** — origen visual en el mockup "Achievements" de `Diseño Preliminar.docx`, pero sin ninguna regla de negocio detrás en el Análisis. El equipo decidió construirla con datos reales (no como maqueta estática) porque ya existe la data necesaria: `CheckIn.isActive` (`001`) marca exactamente un registro por día de asistencia real, que es lo único que se necesita para calcular rachas.

## Qué hace

En el portal del socio (`011`), la pantalla de Logros muestra insignias calculadas a partir de su historial real de asistencia (no datos inventados ni hardcodeados): racha actual de días consecutivos, racha más larga histórica, y un total de días asistidos. Se desbloquean insignias al cruzar ciertos umbrales de racha.

## Por qué

Es la única de las 3 pantallas "extra" del mockup (Workouts/Classes/Achievements) que se puede construir con datos que **ya existen** en el sistema (`CheckIn.isActive`) sin inventar un dominio nuevo (a diferencia de Workouts, que necesitaría un registro de ejercicios que nunca existió, o Classes, que necesitaría un sistema de reservas completo). Cierra la brecha entre "lo que muestra el mockup aceptado" y "lo que el sistema puede respaldar de verdad".

## Criterios de aceptación

- [ ] **Racha actual:** cuenta de días consecutivos (hasta hoy o ayer, si hoy aún no ha hecho check-in) con al menos un `CheckIn(isActive=true)` del socio. Un día sin ningún `CheckIn(isActive=true)` rompe la racha a 0.
- [ ] **Racha más larga (histórica):** el máximo de días consecutivos que el socio haya alcanzado alguna vez, calculado sobre todo su historial de `CheckIn`.
- [ ] **Total de días asistidos:** conteo de días distintos (no eventos) con `isActive=true` en todo el historial del socio.
- [ ] Insignias desbloqueadas según umbrales de racha (ver duda abierta para los valores exactos) — ej. "5 días seguidos", "15 días seguidos", "30 días seguidos". Cada insignia muestra si está desbloqueada (`racha_mas_larga >= umbral`) y el progreso hacia la siguiente si no lo está.
- [ ] La consulta es de **solo lectura**: no crea, modifica ni descuenta ningún `CheckIn` ni visita — es una vista derivada de datos que ya existen.
- [ ] Un socio sin ningún `CheckIn` todavía ve el estado inicial (racha 0, ninguna insignia desbloqueada) sin error.
- [ ] El cálculo se hace en el momento de la consulta (no se guarda un `racha_actual` desnormalizado en `User`/`Membership`) — evita que quede desincronizado si se recalcula la lógica más adelante.

## Duda abierta (a confirmar, no invento la respuesta)

- **Umbrales exactos de las insignias:** no hay dato de origen (el mockup mostraba "Early Bird", "Consistency King", "Class Hero" — nombres de una app de fitness genérica, no aplican literal a GymFlow). Propuesta razonable para el demo: **5, 15 y 30 días de racha** con nombres propios de GymFlow (ej. "Primera semana", "Constancia", "Hierro"). Confirmar nombres/umbrales finales con el equipo antes de hardcodearlos.
- **¿Qué pasa si el socio falta un día por causa de fuerza mayor (ej. el gimnasio cerrado)?** No hay concepto de "día no hábil" en el sistema — cualquier día sin check-in rompe la racha, incluso si el gimnasio no abrió. Fuera de alcance por ahora; si importa, se necesitaría un calendario de días operativos que no existe en ningún otro spec.

## Fuera de alcance

- **Workouts y Classes** — cortadas del alcance completo (ver decisión en `mission.md` y en la nota de `011`), no se construyen ni como UI estática.
- Notificaciones push/email cuando se desbloquea una insignia — no está en `docs/`, ni se pidió.
- Compartir logros en redes sociales u otra funcionalidad social — no está en `docs/`.

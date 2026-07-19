# 001 · Check-in con membresía activa

**Estado:** implementada

**Traza:** HU-01 · RN-01, RN-02, RN-08, RN-10 · RF-01, RF-04, RF-05, RF-06, RF-08 · RNF rendimiento (≤3s, ≥10 concurrencia), RNF usabilidad táctil (≥48×48px, legible a 1m)

## Qué hace

En el kiosko táctil (o por QR, ver `012`), un miembro se identifica. El sistema resuelve el check-in con este **orden de filtros**, tal como lo definiste:

1. **¿Ya tiene un `CheckIn` con `isActive = true` de **hoy** (mismo día calendario)?** Si sí → **Exitoso** directo, sin tocar `visitas_restantes` ni volver a validar RN-01. El torniquete abre.
2. **Si no** → recién ahí se evalúa RN-01 (membresía activa + `visitas_restantes > 0`). Si pasa → se crea el `CheckIn` con `isActive = true`, se descuenta 1 visita. Si no pasa → Denegado (`002`).

Mensaje objetivo (Propuesta): *"ACCESO PERMITIDO. Bienvenido/a {nombre}. Visitas restantes: {X}"*.

## Por qué

Contiene el **motor de validación** que resuelve si un check-in es exitoso — ese motor es compartido y lo reutiliza también `012-checkin-qr-dinamico`. **Nota de priorización (ver `roadmap.md`):** originalmente esta feature (HU-01, cédula) se trataba como "el flujo central del producto". El equipo confirmó que la esencia real del producto es HU-03 (identificación por QR, sin contacto, sin tarjetas) — `001` sigue siendo imprescindible como motor de reglas, pero la **identificación por cédula en sí** pasa a ser el camino de respaldo, no el que se espera que use la mayoría de los socios. Ver `012` para el camino esperado.

## Criterios de aceptación

- [x] **Filtro 1 — `isActive` de hoy:** dado un miembro que **ya tiene** un `CheckIn(usuario_id=X, isActive=true)` cuya `fecha_hora` cae en el **día calendario actual**, cuando intenta ingresar de nuevo, entonces el resultado es **Exitoso** directo — **no se reevalúa RN-01** (ni membresía ni saldo), **no se descuenta visita**, el torniquete abre igual. *Importante:* la consulta debe filtrar explícitamente por fecha (`WHERE usuario_id = X AND isActive = true AND DATE(fecha_hora) = HOY`), no confiar solo en el booleano — un `isActive=true` de ayer **no** debe contar como válido hoy, porque nadie lo resetea automáticamente a `false` al cambiar de día. *Verificado: `checkin/repository.py::exists_successful_checkin_today` filtra por `DATE(fecha_hora AT TIME ZONE 'America/Bogota')`; test `test_segundo_checkin_mismo_dia_no_descuenta_de_nuevo`.*
- [x] **Filtro 2 — sin `isActive` de hoy:** dado un miembro **sin** ningún `CheckIn(isActive=true)` de hoy, se evalúa RN-01 (hoy ≤ `fecha_vencimiento` y `visitas_restantes > 0`). Si pasa → **Exitoso**, se crea `CheckIn(resultado=Exitoso, fecha_hora, usuario_id, isActive=true)` y se descuenta **exactamente 1** de `visitas_restantes` (RF-05). Si no pasa → **Denegado**, sin crear `isActive=true` → `002-acceso-denegado`. *Verificado: tests `test_checkin_exitoso_descuenta_exactamente_una_visita`, `test_sin_visitas_restantes_deniega_sin_crear_checkin_activo`, `test_membresia_vencida_deniega`.*
- [x] La validación, el registro del `CheckIn` y el descuento (Filtro 2) ocurren en **una única transacción** (RN-10). *Comprobable con un test que fuerza un fallo a mitad de la transacción. Verificado: `test_rollback_no_descuenta_si_falla_a_mitad_de_transaccion`.*
- [x] **Restricción de unicidad:** a lo sumo un `CheckIn` con `isActive=true` por `usuario_id` y día calendario — se recomienda un **índice único parcial** en base de datos (`UNIQUE(usuario_id, DATE(fecha_hora)) WHERE isActive = true`) para blindar el Filtro 1 contra condiciones de carrera (dos check-ins simultáneos del mismo socio no deben poder crear dos registros `isActive=true` el mismo día, ni descontar dos visitas). *Verificado: migración `adc852f8fca8`, índice `ix_checkins_usuario_dia_activo` confirmado con `\d checkins`.*
- [x] El flujo resuelve en ≤3s bajo condiciones normales y soporta ≥10 check-ins concurrentes sin descontar de más (RNF rendimiento + RN-10). *Verificado: `test_diez_checkins_concurrentes_no_descuentan_de_mas` (10 hilos, exactamente 1 descuento; violaciones del índice único se resuelven como Filtro 1 en `checkin/service.py`, no como error).*
- [x] Los elementos accionables del kiosko miden ≥48×48px y el mensaje es legible a 1m (RNF usabilidad). *Verificado visualmente: `NumericKeypad` usa botones de 80px (`h-20`) con texto grande.*
- [x] El backend expone `GET /health` — endpoint trivial, **sin autenticación**, que responde `200 OK` si el proceso está arriba (no valida conexión a base de datos ni ninguna regla de negocio, solo confirma que el servidor responde). Usado por el `healthcheck` de `docker-compose.yml` y el smoke test de CI (ver `spec/constitution/ci-cd.md`) — vive aquí y no en `core/` sin spec porque el equipo decidió agruparlo con el check-in en vez de dejarlo suelto. *Verificado con `curl` contra uvicorn real.*

## Duda abierta (decisión de negocio deliberada, no ambigüedad de lectura)

- **RN-02 y RN-08 se reinterpretan respecto al texto literal del Análisis original.** RN-02 decía "no se permite más de un check-in por día"; RN-08 decía "cada check-in exitoso descuenta 1 visita". Tal como estaban escritas, un segundo ingreso el mismo día quedaba **denegado** (así lo tenía `002-acceso-denegado`, con `razon_denegacion = YA_INGRESO_HOY`). El equipo confirmó que esto no es el comportamiento deseado: un socio debe poder entrar y salir las veces que quiera el día que pagó. Esto es un cambio de negocio explícito, no una corrección de un error de redacción — queda documentado aquí para que sea trazable si alguien (ej. la profesora) pregunta por qué el spec no coincide textualmente con el Análisis.
- **Campo nuevo en `CheckIn`:** `isActive: bool` (reemplaza la propuesta anterior de `visita_descontada`, este diseño es más simple y es el que definió el equipo). No estaba en el modelo original (`tech-stack.md` listaba `id, usuario_id, fecha_hora, resultado, razon_denegacion, titular_id`).

## Fuera de alcance

- Mensajería y flujo de **denegación** (membresía vencida / sin visitas) y bloqueo de dispositivo → `002-acceso-denegado`.
- Identificación por **QR o nombre** → `008-busqueda-multiples-criterios` (aquí solo por cédula, RF-01).
- **Cortesía de primer día** para cédulas no registradas → `005-cortesia-primer-dia`.
- **Invitados** → `006-checkin-invitado`.
- Panel de **resumen** ampliado de membresía → `007-resumen-membresia` (aquí solo el mínimo del semáforo).

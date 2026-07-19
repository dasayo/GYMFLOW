# 005 · Cortesía de primer día

**Estado:** propuesta

**Traza:** HU-04 · RF-07 · RN-10, RF-05

> **Nota de trazabilidad:** en `Analisis.docx` los criterios de aceptación de HU-04 están copiados de HU-03 (mismo defecto, ver la nota en `008-busqueda-multiples-criterios`). Esta spec usa la descripción correcta de la Propuesta (§2.A) y de RF-07.
>
> **Cambio de canal (decisión del equipo):** la cortesía **no se autoservicia en el kiosko táctil**. La persona llega, habla con el **Staff**, le da sus datos (el staff puede verificar su identidad en persona), y el staff registra la cortesía desde el backoffice/panel de staff — no desde el kiosko con solo digitar una cédula. Razón: un kiosko self-service sin verificación de identidad sería trivialmente abusable (cualquiera inventa una cédula nueva cada vez y obtiene entradas gratis indefinidamente). Esto también resuelve qué pasa con RN-02 en este contexto — no aplica, ya no es self-service.

## Qué hace

Cuando una persona nueva llega al gimnasio, el **Staff** toma sus datos (cédula, nombre) y registra en el sistema un acceso gratuito único. El sistema crea un `User` marcado como **Prospecto** y un `CheckIn` **Exitoso** de cortesía, e impide que esa misma cédula reciba una segunda cortesía. Si la persona luego decide afiliarse, el Staff reutiliza esos mismos datos para crear su membresía completa (`004`), sin tener que volver a capturarlos.

## Por qué

Convierte el "primer día gratis" (hoy gestionado con papel/memoria) en un flujo controlado y contabilizado, habilitando la conversión de prospectos a miembros (problemática §1 de la Propuesta) — y al hacerlo vía Staff, además resuelve el riesgo de abuso que tendría un kiosko 100% self-service sin verificación de identidad.

## Criterios de aceptación

- [ ] Un Staff autenticado, dada una cédula **no registrada**, la ingresa en el panel de staff (no en el kiosko) y el sistema crea un `User` marcado como **Prospecto** y registra un `CheckIn` **Exitoso** de cortesía (RF-07).
- [ ] La creación del prospecto y el registro del `CheckIn` ocurren en **una única transacción** (RN-10): si algo falla, no queda un prospecto "a medias" ni un check-in huérfano.
- [ ] Un **segundo** intento con una cédula que **ya usó** su cortesía → **no** concede otra cortesía; el sistema lo indica claramente al Staff (p. ej. "cortesía de primer día ya utilizada") e invita a afiliarse.
- [ ] Un prospecto que **ya usó** la cortesía no puede volver a entrar gratis — su siguiente ingreso requiere afiliarse (`004`), momento en el que sus datos de Prospecto se reutilizan para crear el `User`/`Membership` completos sin volver a digitarlos.
- [ ] Endpoint requiere rol Staff autenticado (RBAC, mismo patrón que `004`/`009`).

## Fuera de alcance

- **Afiliación / asignación de membresía** al prospecto → `004-gestion-usuarios`.
- **Invitado de un socio** (cupos) → `006-checkin-invitado` (flujo distinto).
- **Dudas abiertas:**
  - El enum `rol` de `User` es `Invitado/Miembro/Empleado/Administrador` y **no incluye "Prospecto"**. Se propone marcar la cortesía con un `estado`/flag `cortesia_usada` (o rol `Invitado` + flag) en lugar de añadir un valor de enum, para no romper el modelo. Confirmar con el equipo.
  - **¿El check-in de cortesía cuenta hacia el contador de bloqueo de dispositivo (RN-03)?** Con este cambio ya no aplica directamente — RN-03 es del kiosko, y la cortesía ahora la registra el Staff desde otro panel. Confirmar que no hay una superficie de abuso equivalente en el panel de Staff (ej. ¿tiene su propio límite de intentos?).

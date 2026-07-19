# 006 · Check-in de invitado

**Estado:** propuesta

**Traza:** HU-05 · **RN-04**, **RN-09**, **RN-10** · RF-05, RF-08

> **Decisión sobre RN-04 ("justo después del anfitrión"):** el sistema no tiene registro de salida (`checkout`), así que "el titular sigue adentro" se aproxima con una **ventana de tiempo** desde el check-in del titular (no hay forma más precisa sin checkout). Dos caminos:
> 1. **Dentro de la ventana:** el invitado puede hacer check-in de forma independiente (kiosko/staff), sin que el titular tenga que estar presente en ese instante exacto — se asume que sigue en las instalaciones.
> 2. **Fuera de la ventana (venció el tiempo):** el invitado **ya no puede entrar solo** — el titular tiene que venir en persona y hacerlo entrar él mismo (check-in acoplado, en la misma interacción del titular). Esto cubre el caso de un invitado que llega tarde sin depender de una ventana más larga y más fácil de abusar.

## Qué hace

**Camino 1 (dentro de la ventana):** el titular hace su check-in (`001`/`012`). Dentro de los minutos siguientes (ver duda abierta sobre duración), su invitado puede identificarse por su cuenta (cédula) en el kiosko. El sistema valida que el titular tenga membresía activa, `cupo_invitados_restantes > 0`, y que su check-in exitoso esté dentro de la ventana vigente; si todo pasa, descuenta **exactamente 1 cupo** y registra el ingreso del invitado.

**Camino 2 (venció la ventana):** el invitado ya no puede iniciar su propio check-in. El titular debe volver al kiosko y, en la misma interacción, hacer entrar a su invitado directamente (mismo mecanismo que un check-in acoplado) — mismas validaciones de cupo, mismo descuento.

Mensaje objetivo (Propuesta): *"Bienvenido {nombre}. El socio {socio} tiene ahora {X} invitaciones restantes."*.

## Por qué

Convierte los "días de invitado" (hoy en papel/memoria) en un flujo con contabilidad real de cupos y aforo (problemática §1), evitando abuso del cupo cuando el titular no está presente (RN-04), sin bloquear al invitado por completo si el titular efectivamente sigue en el gimnasio.

## Criterios de aceptación

- [ ] Dado un titular con membresía **activa**, `cupo_invitados_restantes > 0`, y un check-in exitoso suyo **dentro de la ventana vigente**, cuando su invitado se identifica por su cuenta, entonces el acceso es **Exitoso**, se descuenta **exactamente 1** cupo del titular (RN-09) y se registra `CheckIn(Exitoso, usuario_id=invitado, titular_id=titular)` (RF-05).
- [ ] Si la ventana **ya venció** (no hay check-in del titular dentro del rango vigente) y el invitado intenta entrar **por su cuenta** → **Denegado**, motivo "el titular debe acompañarlo" — no se le indica al invitado que puede simplemente esperar o reintentar, el mensaje debe ser claro sobre que necesita al titular presente.
- [ ] El titular puede, en cualquier momento, hacer entrar a su invitado **en persona** (check-in acoplado al suyo propio, mismo kiosko/QR) sin depender de la ventana — este camino siempre está disponible como respaldo.
- [ ] El descuento del cupo y el registro del `CheckIn` ocurren en **una única transacción** (RN-10) en ambos caminos: si falla el descuento, no hay acceso exitoso y se revierte todo.
- [ ] Si el titular está **inactivo/vencido** o `cupo_invitados_restantes = 0` → **Denegado** en ambos caminos, sin descontar (RN-04).
- [ ] El mensaje muestra los cupos restantes del titular tras el ingreso.

## Duda abierta (a confirmar, no invento la respuesta)

- **Duración de la ventana:** la doc original no la especifica. Se propone **configurable, por defecto ≤10 min** desde el check-in exitoso del titular, igual que en la versión anterior de este spec. Confirmar valor con el equipo — probablemente vale la pena hacerla más generosa que 10 min dado que ahora existe el Camino 2 como respaldo si se vence (menos presión para acertarle al valor exacto).
- **¿Ventana por dispositivo o global?** Si el titular entra en el kiosko A, ¿su invitado puede entrar por el kiosko B dentro de la ventana, o tiene que ser el mismo dispositivo? Se propone global (por `usuario_id` del titular, no por dispositivo) ya que un gimnasio puede tener más de un punto de acceso. Confirmar.
- **Dueño de la entidad `Guest`**: la constitución no la asigna explícitamente a un módulo. Se propone que la gestione `checkin` (su ciclo de vida está atado a eventos de check-in). Confirmar con el equipo.

## Fuera de alcance

- **Cortesía de primer día** (persona sin titular) → `005-cortesia-primer-dia`.
- Gestión del catálogo de cupos por tipo → definido en `009` (`cupo_invitados` del `MembershipType`).

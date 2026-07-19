# 004 · Gestión de usuarios y membresías

**Estado:** propuesta

**Traza:** HU-07 · RN-07, RN-12 · RF-10, RF-09 · depende de `003-autenticacion-segura`

> **Fusión (decisión del equipo):** esta feature originalmente solo cubría el CRUD de `User`. Se le fusionó lo que iba a ser una feature aparte ("013 · Renovación de membresía") porque, técnicamente, **asignar la primera membresía a alguien** y **renovarle una nueva** son la misma operación de fondo (crear una fila `Membership`) — no tenía sentido separarlas en dos specs distintas. Queda todo aquí, distinguiendo los dos casos de uso donde sí difieren.
>
> **Sin HU de origen para la parte de renovación** — el equipo confirmó que nunca se pensó una historia de usuario para "quién cobra y renueva" ("no tenemos historias de usuario, no pensamos lo suficiente en eso"). Esta parte llena un hueco real: **RN-06** ("los cambios de un tipo de membresía... aplican al **siguiente ciclo**") asume que existe un mecanismo para crear ese siguiente ciclo, y antes de esta fusión ningún RF/HU lo definía.

## Qué hace

Da al **Staff** (Empleado/Administrador) un CRUD de usuarios, y dos formas de que un usuario tenga una `Membership`:

1. **Primera asignación** — un usuario (Prospecto recién afiliado, o Miembro nuevo) no tiene ninguna `Membership` previa; el Staff le crea la primera, vinculando un `MembershipType`.
2. **Renovación** — un socio con `Membership` anterior (vigente o vencida) paga en ventanilla; el Staff confirma el pago (fuera del sistema — GymFlow no procesa pagos, ver `mission.md`) y crea una **`Membership` nueva** (fila distinta, no se edita la anterior — ver decisión abajo), usando los valores del `MembershipType` **vigentes en el momento de renovar** (RN-06: pueden ser distintos a los del ciclo anterior, porque los tipos y precios cambian con el tiempo).

Incluye también el borrado de usuarios respetando la preservación del histórico de check-ins.

## Por qué

Sin altas manuales no hay miembros que validar en el kiosko; es la base operativa del Sprint 1 (HU-07) y prerrequisito real de los flujos de check-in. La renovación, además, es la operación más frecuente de un gimnasio real (cada socio la usa mensual/trimestral/anualmente) y sin ella RN-06 no tiene forma de dispararse nunca.

> **No confundir con el flujo de entrada diario:** la renovación es una transacción de pago, ocasional (una vez por ciclo). El check-in del día a día (`001`/`012`) sigue siendo 100% self-service — escanea QR (o cédula de respaldo), pasa los filtros, entra. El staff no interviene ahí; solo aparece en esta feature porque alguien tiene que recibir el pago.

## Decisiones ya confirmadas (por el equipo, en conversación)

- **Renovar crea una `Membership` nueva, no sobreescribe la existente.** La fila anterior queda intacta como histórico (`estado = Vencida` cuando corresponda). Razón: los tipos de membresía y sus precios cambian con el tiempo (RN-06) — sobreescribir perdería el registro de qué precio/plan tenía el socio en cada ciclo pasado. Consistente con RN-07 (preservar histórico) y con lo que `010` necesita para reportar por ciclo.
- **Pago en ventanilla.** El pago ocurre en un punto de atención física, fuera del sistema.
- **Borrado de usuario (RN-07): anonimización, no borrado físico.** Se vacía `cédula/nombre/email`, se marca `estado = Inactivo`, se conserva el `id`. Los `CheckIn` existentes siguen apuntando a ese `id` intacto. Consistente con que `User.cedula/nombre/email` ya son `nullable` en el modelo actual pensando en este caso.
- **Upgrade/downgrade permitido al renovar.** El Staff puede elegir cualquier `MembershipType` vigente al renovar, sea el mismo que tenía el socio u otro distinto.
- **Fecha de inicio en renovación anticipada:** si la `Membership` anterior **todavía está vigente** al momento de renovar, la nueva `fecha_inicio` = `fecha_vencimiento` de la anterior **+ 1 día** (no se pierden días pagados). Si la anterior ya venció, la nueva `fecha_inicio` = hoy.
- **Permiso de renovación: individual, no solo por rol.** Se crea el permiso `membership.renovar` (catálogo `permisos`, mismo mecanismo de `003`). Un Empleado necesita que se lo otorguen explícitamente para renovar membresías; `administrador` lo tiene implícito. Como hoy no existe forma de otorgar permisos fuera de un script de desarrollo, **004 agrega el endpoint para que un Administrador otorgue/quite permisos a un usuario específico** (alcance ya señalado en `roadmap.md`, ausente hasta ahora del spec — se incorpora aquí).
- **Registro de pago en la renovación:** se agrega `monto` (`Numeric(10,2)`, obligatorio) y `nota` (texto libre, opcional) a la operación de renovación/asignación, para dejar trazabilidad de qué se cobró.
- **Quién puede crear/ascender a qué rol (hallazgo posterior a la implementación inicial, probado por el equipo):** el RBAC general (Empleado/Administrador, RF-09) no bastaba — cualquier Empleado podía crear otro Administrador. Se agrega una restricción más fina, aplicada tanto a **crear** un usuario como a **editar el rol** de uno existente:
  - Rol `administrador`: reservado exclusivamente a otro `administrador`. Ningún permiso individual lo habilita.
  - Rol `empleado`: `administrador`, o un `empleado` con el permiso individual nuevo `members.asignar_rol_empleado` (mismo mecanismo que `membership.renovar`).
  - Rol `miembro`/`invitado`: cualquier Staff autenticado, sin restricción adicional (como ya era).
- **CRUD básico de usuarios también gateado por permiso individual (segundo hallazgo, probado por el equipo con un Empleado sin permisos):** el criterio original de esta sección ("Todos los endpoints exigen rol Empleado/Administrador") no distinguía entre autenticación (RF-09) y autorización fina — cualquier Empleado podía crear/listar/editar/eliminar usuarios sin nada más que el rol. Se agrega el permiso individual `members.gestionar_usuarios`: sin él, un Empleado no puede usar `POST/GET/PUT/DELETE /usuarios` en absoluto (403), independientemente de `members.asignar_rol_empleado` (ese solo decide a qué rol se puede crear/ascender, no si se puede gestionar usuarios). `administrador` lo tiene implícito. Los sub-recursos de membresía (asignar primera vez, ver historial) **no** quedaron detrás de este permiso — siguen abiertos a cualquier Staff, como decía el criterio original; solo renovar ya tenía su propio permiso (`membership.renovar`).

## Criterios de aceptación

### CRUD de usuarios
- [ ] Un Staff autenticado con el permiso individual `members.gestionar_usuarios` puede **crear** un usuario (`cédula`, `nombre`, `email`, `rol`, `estado`) y el perfil queda persistido (RF-10). Sin ese permiso (y sin ser `administrador`), el intento devuelve 403.
- [ ] Un Staff con `members.gestionar_usuarios` puede **leer, listar y editar** usuarios; sin él, 403 en los cuatro endpoints (`POST/GET/PUT/DELETE /usuarios`).
- [ ] Al **eliminar** un usuario, su información personal (`cédula`, `nombre`, `email`) se borra de forma irreversible, **pero** sus registros de `CheckIn` históricos se preservan (RN-07). *Comprobable: tras el borrado, los `CheckIn` del usuario siguen existiendo para estadística.*
- [ ] Si se crea un usuario Empleado/Administrador con credenciales, la contraseña se guarda **hasheada** (RN-12).
- [ ] Todos los endpoints exigen rol Empleado/Administrador (RBAC, RF-09); sin token válido → 401/403.
- [ ] Un Empleado **sin** el permiso `members.asignar_rol_empleado` no puede crear ni ascender a nadie a `empleado` o `administrador` (403) — ni creando un usuario nuevo con ese rol, ni editando el rol de uno existente. Con el permiso, puede crear/ascender a `empleado`, pero **nunca** a `administrador`.

### Primera asignación de membresía
- [ ] Un Staff puede **asignar una membresía** a un usuario **sin `Membership` previa**, vinculando un `MembershipType` existente y creando su `Membership` con saldos iniciales (`visitas_restantes`, `cupo_invitados_restantes` = totales del tipo), registrando `monto` (obligatorio) y `nota` (opcional).

### Renovación de membresía
- [ ] Un Staff busca un socio existente (reutiliza `008`) y ve su membresía actual (vigente o vencida) y su historial de membresías anteriores.
- [ ] Renovar requiere el permiso individual `membership.renovar` (o rol `administrador`, que lo tiene implícito) — no basta con el rol `Empleado` genérico.
- [ ] El Staff confirma la renovación indicando el `MembershipType` a aplicar (puede ser el mismo que tenía o uno distinto — upgrade/downgrade permitido), el `monto` cobrado (obligatorio) y una `nota` opcional.
- [ ] Al confirmar, el sistema crea una **`Membership` nueva** (fila distinta): `fecha_vencimiento` = `fecha_inicio + duracion_dias`, `visitas_restantes` = `visitas_totales` del tipo, `cupo_invitados_restantes` = `cupo_invitados` del tipo, `estado` = Activa, tomando los valores del `MembershipType` **vigentes en el momento de renovar**.
  - `fecha_inicio` = **hoy**, salvo que la `Membership` anterior siga vigente (no vencida) al momento de renovar, en cuyo caso `fecha_inicio` = `fecha_vencimiento` de la anterior **+ 1 día**.
- [ ] La `Membership` anterior **no se modifica** — queda como registro histórico, consultable en reportes (`010`) y en el historial del socio.
- [ ] Ambas operaciones (primera asignación y renovación) son **atómicas** (RN-10): si falla, no queda una `Membership` a medias.
- [ ] El historial de `CheckIn` del socio **no se altera** por ninguna de las dos operaciones.

### Permisos individuales (otorgar/quitar)
- [ ] Un Administrador puede **otorgar** un permiso (ej. `membership.renovar`) a un usuario Empleado específico.
- [ ] Un Administrador puede **quitar** un permiso previamente otorgado a un usuario.
- [ ] Un Administrador puede **listar** los permisos actuales de un usuario.
- [ ] Estos endpoints exigen rol `administrador` (no basta ser Empleado).

## Fuera de alcance

- **Autenticación** (login, emisión de JWT, RBAC) → `003-autenticacion-segura`.
- **CRUD de tipos de membresía** (`MembershipType`) → `009-configuracion-tipos-membresia` (aquí se **usan**, no se definen).
- **Procesamiento de pagos** — no hay pasarela, no se factura (misión). El staff confirma el pago fuera del sistema; `monto`/`nota` son solo trazabilidad interna, no una integración de cobro.
- **Renovación automática** (cron/recurrente) — manual, iniciada por el staff.
- **CRUD del catálogo de permisos** (crear/eliminar códigos de permiso nuevos) — el catálogo (`permisos`) se sigue sembrando por migración, como en `003`. `004` solo agrega la relación usuario↔permiso (`usuario_permisos`).

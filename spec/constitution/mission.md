# Misión

## Qué construimos

GymFlow es un sistema de control de acceso físico y gestión de membresías para gimnasios pequeños y medianos, que reemplaza la validación manual (planillas/Excel) en recepción por un motor de reglas de negocio que valida en tiempo real.

1. **Check-in por QR (esencia del producto)** — el socio llega al gimnasio, escanea con su celular el QR que muestra el kiosko y entra. Sin tarjetas, sin contacto humano, sin digitar nada en el kiosko. Este es el flujo que el sistema está pensado para resolver.
2. **Check-in manual (respaldo)** — búsqueda por cédula/nombre en el kiosko, para cuando el socio no tiene celular a mano, no tiene señal/batería, o el staff necesita resolver una incidencia. No es el camino que se espera que use la mayoría de los socios día a día, pero debe seguir funcionando siempre como plan B.
3. **Feedback visual** — pantalla de semáforo (permitido/denegado) con mensaje claro para el usuario y el staff, sin ambigüedad sobre el motivo de un rechazo. Aplica igual sin importar si el check-in fue por QR o manual.
4. **Cortesía de primer día e invitados** — check-in de invitados con descuento atómico de cupos.
5. **Backoffice (Administración)** — CRUD de usuarios y tipos de membresía, reportes de asistencia con exportación a XLSX/CSV.
6. **Portal del socio (web)** — el Miembro inicia sesión con correo/contraseña para ver su resumen de membresía, estadísticas de asistencia y logros por racha (ver mockups en `docs/` y decisión de alcance en `011`/`013`), y desde ahí escanea con la cámara del celular el QR del kiosko. Este login es el prerrequisito técnico del punto 1, no una feature aparte que compite con él. **Workouts y Classes** (calorías, reserva de clases con recomendaciones) del mockup **quedan fuera del alcance** — no tienen ninguna regla de negocio de origen, son de una plantilla de app de fitness genérica, no de GymFlow.

## Para quién

- **Miembro (socio)** — usuario con membresía activa. El camino esperado es: inicia sesión una vez en el portal web (sesión larga, no vuelve a loguearse seguido) y de ahí en adelante su check-in diario es **escanear el QR del kiosko y entrar**, sin fricción. La identificación por cédula/nombre en el kiosko sigue existiendo, pero como respaldo — no es la experiencia que el producto busca dar por defecto.
- **Invitado** — persona sin membresía propia que ingresa con el cupo de un socio, o accede una única vez por cortesía de primer día. No tiene portal ni login; su check-in siempre es manual/asistido.
- **Empleado / Staff (recepción)** — resuelve incidencias del kiosko y registra usuarios manualmente.
- **Administrador / Dueño** — accede a reportes y configura parámetros globales (tipos de membresía, límites de invitados).

## Principios

- **Real time y sin fricción** — el flujo de check-in debe resolver en ≤3s (RNF de rendimiento), sea por QR o manual; nada de pasos innecesarios ni contacto humano en el camino esperado (QR).
- **Atomicidad ante todo** — cualquier operación que descuente visitas o cupos de invitado debe ser ACID: si el descuento falla, el check-in no se registra como exitoso (RN-10).
- **Modularidad por dominio, no por capa técnica** — el monolito se organiza en módulos (`auth`, `members`, `checkin`, `membership`, `reports`) con dueño claro, no en una carpeta gigante de controllers/services mezclados. Esto también da ownership natural a los 5 integrantes del equipo.
- **Mensajes claros antes que "elegantes"** — el usuario no debe quedar en duda de por qué se le negó el acceso, sea que lo vea en el kiosko (check-in manual) o en su celular (check-in por QR); siempre se explica el motivo (RN sobre feedback visual).
- **Táctil primero, para el camino de respaldo** — el check-in manual en el kiosko (para cuando el QR no es posible) prioriza pantalla táctil (botones ≥48x48px, legibilidad a 1m). El check-in por QR no usa esta pantalla del kiosko para nada más que mostrar el QR mismo; toda la interacción del socio ocurre en su celular. El backoffice puede ser más denso.

## Qué NO es

- No es un sistema de facturación/cobro en línea — no hay pasarela de pagos ni checkout, solo se registra `precio_base` como dato de referencia.
- No es multi-sede con sincronización entre gimnasios — se diseña para una sede; si el alcance real incluye varias sedes, hay que replantear esta constitución antes de seguir.
- No es una app móvil nativa — es una PWA responsive (kiosko en tablet + panel admin en navegador Chromium).
- No requiere Authorization Server ni login federado (Google/GitHub) — la autenticación es JWT propio y simple. **Decisión revisada (ver `012-checkin-qr-dinamico` y `011-portal-miembro-autenticacion`):** el Miembro *puede* iniciar sesión con correo/contraseña en el portal web (no en el kiosko) para ver su cuenta y habilitar el check-in por QR desde su celular. Esto no contradice el principio "sin fricción en el kiosko": el kiosko en sí nunca pide login, y el check-in por cédula/nombre en el kiosko sigue funcionando sin sesión. Lo que cambia es que ahora existe un canal adicional (web) donde sí hay login, igual que Staff/Administrador. El Invitado sigue sin ningún tipo de login.

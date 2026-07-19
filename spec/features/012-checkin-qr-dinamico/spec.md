# 012 · Check-in por QR dinámico

**Estado:** propuesta

**Traza:** **HU-03** (identificación por QR — flujo esencial del producto, ver `roadmap.md`) · **RF-02** (del documento original: "QR dinámico generado desde la sesión del Miembro") · RN-01, RN-02, RN-08, RN-10 (mismo motor de reglas de `001`, solo cambia el método de identificación) · Depende de `011-portal-miembro-autenticacion`

## Qué hace

1. El kiosko muestra en pantalla un **QR que rota periódicamente** (no es el mismo QR todo el día — evita que alguien lo capture con foto y lo reuse más tarde).
2. El Miembro, ya logueado en el portal web (`011`), abre la cámara desde un botón en la web y escanea ese QR.
3. El QR codifica una URL/endpoint del backend con un identificador de ese kiosko + un valor de un solo uso (nonce). El navegador del socio hace la petición a ese endpoint enviando su **sesión activa** (access token de `011`) junto con esos datos del QR.
4. El backend valida: sesión del socio válida → identifica al Miembro; nonce válido, no usado y no expirado → evita reuso; aplica las mismas reglas de negocio que el check-in normal (membresía activa, visitas disponibles, no duplicado el mismo día — RN-01, RN-02, RN-08, RN-10).
5. El backend resuelve el resultado (Exitoso/Denegado) y lo **empuja al kiosko por WebSocket** (el kiosko mantiene una conexión abierta esperando el evento correspondiente a su QR activo — así se decidió con el equipo, no polling).
6. El kiosko muestra el mismo semáforo verde/rojo que en `001`/`002`, con el nombre y las visitas restantes del socio.

## Por qué

Es el **flujo esencial del producto** (HU-03, ver `roadmap.md`): el equipo confirmó que la idea original siempre fue "el socio llega, escanea y entra", sin tarjetas ni contacto humano. Reutiliza el motor de validación de `001` (mismas reglas de negocio), pero la identificación por QR — no por cédula — es el camino que se espera que use la mayoría de los socios día a día.

## Criterios de aceptación

- [ ] El kiosko muestra un QR que **cambia periódicamente** (frecuencia exacta: ver duda abierta).
- [ ] El QR codifica al menos: identificador del kiosko (`device_id`) + un nonce de un solo uso.
- [ ] El navegador del socio, al escanear, envía su sesión (access token de `011`) + los datos del QR al backend.
- [ ] Un nonce **ya usado** o **expirado** es rechazado (no se puede reusar el mismo QR escaneado dos veces).
- [ ] Con nonce válido y sesión válida, se aplican las **mismas reglas de negocio** que `001`/`002` (membresía activa, visitas disponibles, no duplicado el mismo día, atomicidad del descuento — RN-10).
- [ ] El resultado (Exitoso/Denegado) se **empuja al kiosko por WebSocket** — el kiosko no pregunta activamente, espera el evento de su conexión abierta.
- [ ] El kiosko muestra el semáforo correspondiente (reutiliza el mismo componente visual de `001`/`002`, no uno nuevo).
- [ ] Un check-in exitoso por QR descuenta visita igual que un check-in por cédula (no se descuenta dos veces si además el socio hace check-in manual el mismo día — RN-02 sigue aplicando sin importar el método de identificación).
- [ ] Si el socio no tiene datos/wifi al momento de escanear, el fallo se comunica claramente en su celular (no en el kiosko, que sigue esperando).

## Duda abierta (a confirmar, no soy quien decide el valor exacto)

- **Frecuencia de rotación del QR/nonce:** no hay dato de origen para esto. Propuesta razonable: **cada 20-30 segundos**, suficiente para que el socio alcance a escanear pero corto para minimizar la ventana de reuso por foto. Confirmar con el equipo antes de fijarlo en `plan.md`.
- **Identidad del kiosko en el WebSocket:** ¿el kiosko se autentica con el mismo `X-Device-Id` que ya se usa en `002-acceso-denegado` para el bloqueo por intentos fallidos? Parece lo más consistente (reusar el mismo mecanismo en vez de inventar uno nuevo), pero se deja como confirmación antes de implementar.
- **Método de respaldo sin cámara/datos:** los mockups y `docs/` no contemplan un plan B si el socio no puede escanear (sin batería, sin señal). El camino de `001` (cédula/nombre en el kiosko) sigue disponible como alternativa siempre, así que probablemente no se necesita un tercer método — pero vale confirmarlo explícitamente con el equipo para que quede en la spec, no asumido.

## Fuera de alcance

- Login y manejo de sesión del Miembro → `011`.
- Generación del semáforo visual en sí (se reutiliza el de `001`/`002`, no se rediseña aquí).
- Emisión de QR **estático** de carnet/membresía → sigue siendo tema de `008` (no se toca en esta feature).

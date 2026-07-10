# 011 · Portal del socio y autenticación de Miembro

**Estado:** propuesta

**Traza:** Origen en **`docs/Diseño Preliminar.docx`** (mockups de Dashboard, Workouts, Classes, Achievements, Account) — el portal personalizado del socio (saludo por nombre, membership status, stats) ya estaba en el diseño visual original del equipo, aunque nunca se redactó como Historia de Usuario formal en la Propuesta/Análisis. **No confundir con "sin origen":** sí tiene origen en `docs/`, solo le falta la HU numerada correspondiente (ver nota abajo). Referencia parcial a **RF-04** (resumen de membresía, ya cubierto por `007`) y prepara el terreno para **RF-02** (QR dinámico, sí numerado, resuelto en `012`).

> **Decisión de alcance (equipo, no ambigüedad):** de las pantallas del mockup, solo **Dashboard**, **Account** y **Achievements** (ver `013-logros-rachas`) entran al entregable — todas tienen datos reales detrás (`007`, esta feature, `013`). **Workouts** y **Classes** (calorías, reserva de clases con recomendaciones) se cortan del alcance: no tienen ninguna regla de negocio de origen en `docs/Analisis.docx`, son contenido de una plantilla de app de fitness genérica que se coló en el mockup. No se construyen ni como UI estática — si la profesora pregunta, la respuesta es que se identificaron como fuera del alcance real del proyecto durante la revisión de dominio.

> **Nota para el equipo:** esta feature está justificada por el diseño visual (`docs/`), pero no tiene una HU-NN asignada en el catálogo de historias de usuario de la Propuesta. Si quieren que la trazabilidad quede completa para la entrega, redacten una HU corta (ej. *"Como socio quiero ver mis estadísticas y datos de membresía desde una cuenta propia"*) y añádanla al catálogo — no la invento yo porque esa decisión de negocio le corresponde al equipo/profesora, no a mí.

## Qué hace

Un Miembro puede crear una cuenta y luego iniciar sesión con **correo + contraseña** en un portal web (distinto del kiosko físico). Una vez logueado, ve un dashboard con su resumen de membresía (reutilizando el endpoint de `007-resumen-membresia`) y estadísticas de actividad. La sesión es de **larga duración** (no se desloguea a los 30 min como Staff/Administrador): usa un **access token** de corta vida + un **refresh token** que la renueva automáticamente mientras el socio siga usando la web, y expira solo si pasa un período largo sin actividad.

## Por qué

Prerrequisito de `012-checkin-qr-dinamico`: para que el socio pueda escanear el QR del kiosko desde su celular sin fricción, necesita ya estar identificado. Sin esto, cada escaneo tendría que pedir login en el momento, que es justo la fricción que se quería evitar.

## Criterios de aceptación

- [ ] Un Miembro con correo/contraseña válidos recibe un **access token** (JWT, vida corta, ej. 15 min) y un **refresh token** (vida larga).
- [ ] El refresh token se puede usar para obtener un access token nuevo sin volver a pedir credenciales, **mientras el socio siga activo** dentro de la ventana de inactividad definida (ver duda abierta de duración).
- [ ] Si pasa más tiempo que esa ventana sin que el socio use la web, el refresh token deja de ser válido y debe loguearse de nuevo con correo/contraseña.
- [ ] El refresh token se renueva ("rota") cada vez que se usa, para reducir el riesgo de que un token robado siga siendo válido indefinidamente.
- [ ] Credenciales inválidas → error claro sin revelar si el correo existe (mismo criterio que `003` para Staff/Admin).
- [ ] Contraseñas del Miembro se almacenan **hasheadas** (mismo mecanismo que RN-12 para Staff/Admin — no se inventa un segundo esquema de hashing).
- [ ] Logueado, el Miembro ve su resumen de membresía (reutiliza `007`) sin poder modificar visitas/cupos (sigue siendo solo lectura).
- [ ] Un usuario con rol Invitado o sin cuenta de Miembro **no puede** crear cuenta en este portal (el registro es exclusivo de Miembro).

## Duda abierta (a confirmar, no soy quien decide el valor exacto)

- **Duración de la ventana de inactividad del refresh token:** en la conversación se acordó "días, no minutos" (ejemplo dado: 3 días a 1 semana), con renovación automática mientras haya uso. Falta fijar el número exacto — propuesta razonable para un proyecto académico: **7 días de inactividad** como corte, renovando la ventana en cada uso (sliding). Confirmar con el equipo antes de implementarlo como definitivo.
- **Dónde se guarda el refresh token en el navegador:** recomendado `httpOnly` cookie (no `localStorage`, por seguridad ante XSS) — confirmar que el equipo puede manejar cookies cross-origin si el frontend y backend quedan en dominios/puertos distintos en desarrollo.
- **Registro (sign-up):** ¿el Miembro se autorregistra con correo/contraseña, o la cuenta la crea el staff (en `004-gestion-usuarios`) y el Miembro solo "activa" su contraseña la primera vez? Los mockups no muestran una pantalla de registro, solo login/cuenta ya creada. **No se asume una respuesta** — queda para confirmar con el equipo antes de escribir `plan.md`.

## Fuera de alcance

- Check-in por QR en sí (usa esta sesión, pero el flujo de escaneo/validación vive en `012`).
- Recuperación de contraseña / MFA — mismo límite que `003`, no está en `docs/`.
- Edición de perfil, notificaciones, billing (aparecen en el mockup de "Account" pero no hay RF que las respalde en `docs/`; no se especifican aquí para no inventar alcance).

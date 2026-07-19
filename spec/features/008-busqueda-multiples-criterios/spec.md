# 008 · Búsqueda por múltiples criterios

**Estado:** propuesta

**Traza:** HU-03 · RF-01, RF-02, RF-03

> **Nota de trazabilidad (defecto en el documento original):** el criterio de aceptación de HU-03 en `Análisis.docx` dice *"Cuando el empleado realiza la búsqueda..."*, lo cual contradice la frase de intención de la misma HU-03 (*"Como miembro, quiero identificarme por cédula, QR o nombre..."*). Es el mismo tipo de error de copy-paste que el equipo ya marcó para HU-04 en `005-cortesia-primer-dia` (ambos criterios son casi idénticos). Esta spec sigue la frase de intención (identificación por el propio socio), no el criterio Gherkin roto — consistente con lo que el equipo confirmó en conversación. Señalado para que el equipo lo corrija en `docs/` si quiere trazabilidad literal para la entrega.

## Qué hace

Permite identificar/buscar a un usuario por **cédula**, **código QR** o **nombre** (coincidencias parciales), tanto en el kiosko como en el backoffice, para que un miembro pueda ingresar aunque olvide alguno de sus datos y para que el staff resuelva incidencias.

## Por qué

Reduce la fricción del check-in y las incidencias de recepción (ej. "el usuario olvidó su número de cédula", §3 de la Propuesta). Alimenta la identificación de los flujos `001`, `002` y `006`.

## Criterios de aceptación

- [ ] Búsqueda por **cédula** exacta → devuelve el usuario correspondiente (RF-01).
- [ ] Búsqueda por **nombre parcial** → devuelve la lista de coincidencias para que el staff seleccione (RF-03).
- [ ] Lectura de **QR** → decodifica el payload e identifica al miembro (RF-02).
- [ ] Los resultados pueden encadenarse al flujo de check-in (identificación → validación).
- [ ] La búsqueda por nombre/documento admite coincidencias **parciales** (no solo exactas).

## Fuera de alcance

- Validación de acceso y descuentos → `001`/`002`/`006`.
- **Resuelto (antes era duda abierta):** RF-02 pedía un "QR dinámico generado desde la sesión del Miembro", lo cual chocaba con la misión original ("el miembro no inicia sesión"). Se revisó la misión: el Miembro ahora puede loguearse en un **portal web nuevo** (`011-portal-miembro-autenticacion`) sin que el kiosko en sí requiera login. El QR dinámico por sesión queda implementado en `012-checkin-qr-dinamico`, que **reemplaza** el plan de "QR estático emitido por staff" que se había propuesto aquí como parche temporal. Esta feature (`008`) sigue cubriendo la búsqueda por cédula/nombre/QR **estático** (el QR físico del carnet, si existe) como camino alterno; el QR **dinámico** del kiosko vive en `012`.

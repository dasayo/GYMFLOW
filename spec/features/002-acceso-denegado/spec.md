# 002 · Acceso denegado

**Estado:** implementada

**Traza:** HU-02 · RN-01 (condición inversa), **RN-03**, RN-10 · RF-05, RF-06 · RNF usabilidad (mensaje claro), principio "mensajes claros" · **Nota:** RN-02 ya no traza aquí — el reingreso el mismo día es Exitoso, no Denegado (ver `001`).

> **Decisión de alcance (RN-03):** el bloqueo de dispositivo tras 3 intentos fallidos vive aquí, no en una feature aparte. Justificación: RN-03 se dispara exactamente sobre **intentos de check-in denegados**, que es el dominio de esta feature. Alternativa considerada (feature independiente) anotada en `roadmap.md`. **Duda abierta:** identidad del dispositivo (ver Fuera de alcance / Decisiones del plan).

## Qué hace

Cuando la validación de un check-in falla, el kiosko muestra un semáforo **rojo** con el motivo exacto del rechazo (membresía vencida o sin visitas) y la fecha del próximo pago, sin ambigüedad. Además, tras **3 intentos fallidos consecutivos en ≤5 min** desde el mismo dispositivo, el kiosko queda **bloqueado 20 min** (RN-03) como control anti-abuso.

Mensaje objetivo (ajustado — "próximo pago" no aplicaba aquí, ver `007`): *"ACCESO DENEGADO. Tu membresía venció el {fecha_vencimiento}."* (para `MEMBRESIA_VENCIDA`) o *"ACCESO DENEGADO. Alcanzaste el límite de visitas de tu ciclo actual."* (para `SIN_VISITAS`).

## Por qué

El usuario del kiosko no debe quedar en duda de por qué se le negó el acceso (principio de la misión). Y sin un límite de intentos, el kiosko queda expuesto a tanteo de cédulas; RN-03 lo mitiga.

## Criterios de aceptación

- [x] Dado un miembro con membresía **vencida** (hoy > `fecha_vencimiento`) o `visitas_restantes = 0`, cuando intenta check-in, entonces el resultado es **Denegado**, semáforo rojo, con motivo claro según el mensaje objetivo de arriba (RN-01 inversa). *Verificado: `checkin/service.py::_razon_rn01`, tests `test_membresia_vencida_deniega_con_razon_y_persiste_checkin`/`test_sin_visitas_restantes_deniega_con_razon_y_persiste_checkin`, y probado end-to-end en Docker.*
- [x] Un intento denegado **no** altera `visitas_restantes` ni ningún saldo (RN-10: sin efectos colaterales) y **sí** persiste `CheckIn(resultado=Denegado, razon_denegacion)` (RF-05). *Verificado en los mismos tests.*
- [x] La `razon_denegacion` distingue al menos: `MEMBRESIA_VENCIDA`, `SIN_VISITAS`, `DISPOSITIVO_BLOQUEADO`, `CEDULA_NO_ENCONTRADA` (formato inválido, ej. muy corta/con letras — **no** aplica a una cédula válida simplemente no registrada, eso activa la cortesía de primer día en `005`, que ahora es un flujo de staff, no del kiosko). **Cambio respecto a la versión anterior:** `YA_INGRESO_HOY` **ya no es una razón de denegación** — un reingreso el mismo día es **Exitoso** sin descuento adicional, no Denegado. Ver la corrección de RN-02/RN-08 en `001-checkin-membresia-activa`. *Verificado: enum `RazonDenegacion` en `checkin/schemas.py`.*
- [x] 3 intentos fallidos consecutivos desde el mismo dispositivo en ≤5 min → dispositivo **bloqueado 20 min**; durante el bloqueo el kiosko muestra mensaje de bloqueo y **no** procesa check-ins (RN-03). **Ajuste sobre qué cuenta como "intento fallido" para este contador (propuesta del equipo, no está en el Análisis original):** solo cuentan las denegaciones por `CEDULA_NO_ENCONTRADA` (probable tanteo de números al azar) — **no** cuentan `MEMBRESIA_VENCIDA` ni `SIN_VISITAS`, porque esas son socios reales y conocidos con un motivo de negocio legítimo, no un patrón de ataque. Sin este ajuste, un día de vencimientos masivos bloquearía el kiosko para todos por una razón que no es abuso. *Verificado: `checkin/repository.py::CheckinDeviceLockRepository`, dependencia `enforce_device_not_locked` (423), tests `test_tres_fallos_de_cedula_invalida_bloquean_el_dispositivo`/`test_denegacion_por_membresia_no_cuenta_para_bloqueo_de_dispositivo`/`test_ventana_de_cinco_minutos_expira_el_conteo`, y probado end-to-end en Docker (pantalla de cuenta regresiva en el kiosko).*
- [x] Un check-in **exitoso reinicia** el contador de intentos fallidos consecutivos del dispositivo. *Verificado: `test_checkin_exitoso_resetea_contador_de_fallos`.*
- [x] Los mensajes son legibles a 1m y sin jerga técnica (RNF usabilidad). *Verificado visualmente: mismo estilo tipográfico grande del semáforo de `001`.*

## Fuera de alcance

- Cálculo/registro del **camino feliz** (éxito + descuento) → `001-checkin-membresia-activa`.
- Denegación específica del **invitado** (titular inactivo / sin cupos / fuera de ventana) → `006-checkin-invitado`.
- **Regla de formato de cédula para `CEDULA_NO_ENCONTRADA` (decisión provisional, no confirmada con equipo/profesora):** solo dígitos, 5 a 15 caracteres (`^\d{5,15}$`). Elegida por ser permisiva con cédulas colombianas y de otros países sin un dato exacto del rango real — ajustar si alguien confirma el rango correcto.
- **Identidad de dispositivo — resuelto para esta implementación (2026-07-09), no confirmado con el equipo/profesora:** header `X-Device-Id` (UUID que el kiosko genera y persiste en `localStorage`) con fallback a IP de origen si falta el header. Ver `checkin/router.py::enforce_device_not_locked` y `frontend/src/api/checkin.ts::getDeviceId`.
- **Endpoint de desbloqueo manual sin guard de rol todavía:** `POST /checkin/desbloquear/{device_id}` está implementado pero sin autenticación — depende de `003-autenticacion-segura` (JWT de Staff), que todavía no existe. Pendiente explícito en `tasks.md` (`# TODO(003)` en el código).

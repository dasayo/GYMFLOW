# 008 · Búsqueda por múltiples criterios — Plan

## Enfoque

La búsqueda vive en el módulo **`members`** (dueño de `User`). El kiosko y el backoffice consumen `members.service`. La **decodificación de QR** es una utilidad que traduce el payload a una cédula/id y luego reutiliza la misma búsqueda por cédula.

## Implementación

1. `members/repository.py`: `find_by_cedula(cedula)` y `search_by_name_or_doc(q)` (coincidencia parcial `ILIKE`, con índice; opcional `pg_trgm`).
2. `members/service.py`: `search(query, db)` que decide por tipo de entrada (cédula numérica exacta vs. texto parcial) y `get_by_cedula(cedula, db)`.
3. `core/qr.py` (o util en `members`): `decode_qr(payload)` → cédula/id → `members.service.get_by_cedula`.
4. `members/router.py`: `GET /users/search?q=` (staff, con RBAC) y una entrada de identificación para el kiosko (por cédula/QR, sin login).
5. Frontend: campo de búsqueda en backoffice (resultados en tabla) y lector de QR/entrada de cédula en el kiosko.

## Decisiones

- **Búsqueda centralizada en `members`** — evita que `checkin` consulte `User`; respeta la regla de módulos.
- **QR = cédula/id codificado (MVP)** — resuelve la contradicción con la misión (sin sesión de miembro). El "QR dinámico por sesión" queda marcado como duda abierta.
- **Coincidencia parcial con `ILIKE`/`pg_trgm`** — suficiente para el volumen de una sede; se descarta motor de búsqueda externo (fuera de alcance).

## Riesgos

- **Ambigüedad de nombres** (homónimos) → devolver lista y que el staff seleccione; nunca autoseleccionar para descuentos.
- **QR malformado/falsificado** → validar formato y existencia del usuario antes de continuar.
- **Rendimiento de `ILIKE`** en tablas grandes → índice `pg_trgm` si hace falta (poco probable a escala de una sede).

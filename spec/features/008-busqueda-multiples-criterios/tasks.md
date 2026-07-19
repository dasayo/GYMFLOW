# 008 · Búsqueda por múltiples criterios — Tareas

- [ ] `members/repository.py`: `find_by_cedula` y `search_by_name_or_doc` (parcial `ILIKE`).
- [ ] `members/service.py`: `search(query)` (discrimina cédula vs. nombre) y `get_by_cedula`.
- [ ] `core/qr.py`: `decode_qr(payload)` → cédula/id (MVP: cédula codificada).
- [ ] `members/router.py`: `GET /users/search` (RBAC) + entrada de identificación del kiosko.
- [ ] Frontend: búsqueda en backoffice + lector QR / entrada de cédula en kiosko.
- [ ] Encadenar identificación → flujo de check-in (001/002/006).
- [ ] Tests: cédula exacta, nombre parcial (varias coincidencias), QR válido/ inválido.
- [ ] Registrar la duda RF-02 (QR dinámico vs. misión) para la profesora.
- [ ] Validar contra los criterios de aceptación de `spec.md`.
- [ ] Mover la feature a "Hecho" en `../../constitution/roadmap.md`.

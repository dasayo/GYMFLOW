"""
Registro en memoria de conexiones WebSocket del kiosko
(012-checkin-qr-dinamico): un solo proceso uvicorn (sin `--workers`, ver
Dockerfile), así que es seguro mantener esto en memoria — a diferencia de
`CheckinDeviceLock`/`CheckinQrNonce`, que sí viven en tabla porque asumen
múltiples workers. Si algún día se corre con más de un worker, un `push` a
un `device_id` conectado a OTRO proceso se perdería en silencio; queda
documentado como límite conocido, no resuelto aquí.
"""
from fastapi import WebSocket


class ConnectionManager:
    def __init__(self) -> None:
        self._conexiones: dict[str, WebSocket] = {}

    async def connect(self, device_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        anterior = self._conexiones.get(device_id)
        if anterior is not None and anterior is not websocket:
            await anterior.close()
        self._conexiones[device_id] = websocket

    def disconnect(self, device_id: str, websocket: WebSocket) -> None:
        if self._conexiones.get(device_id) is websocket:
            del self._conexiones[device_id]

    async def push(self, device_id: str, payload: dict) -> None:
        websocket = self._conexiones.get(device_id)
        if websocket is None:
            return
        try:
            await websocket.send_json(payload)
        except Exception:
            self.disconnect(device_id, websocket)


manager = ConnectionManager()

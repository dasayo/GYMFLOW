"""
Router de checkin (HU-01 — Check-in con membresía activa y HU-02 — Acceso
denegado). Validación de entrada con Pydantic (checkin/schemas.py), nunca a
mano aquí (convención del proyecto).
"""
import asyncio
from typing import Literal

from fastapi import (
    APIRouter,
    Depends,
    Header,
    HTTPException,
    Request,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from sqlalchemy.orm import Session

import members.service as members_service
from auth.dependencies import require_member, require_permission
from checkin.repository import CheckinDeviceLockRepository
from checkin.schemas import (
    AttendanceConsistencyOut,
    CheckinRequest,
    CheckinResponse,
    CortesiaRequest,
    DispositivoAutorizadoInfo,
    DispositivoAutorizarRequest,
    DispositivoBloqueadoInfo,
    GuestCheckinRequest,
    QrNonceOut,
    QrScanRequest,
)
from checkin.service import (
    NonceInvalidoError,
    UsuarioNoEncontradoError,
    autorizar_dispositivo,
    checkin_guest,
    checkin_member,
    checkin_via_qr,
    dispositivo_autorizado,
    first_day_courtesy,
    generar_qr_nonce,
    get_member_attendance_consistency,
    listar_dispositivos_autorizados,
    revocar_dispositivo,
)
from checkin.ws_manager import manager as ws_manager
from core.config import now as _now, settings
from core.database import SessionLocal, get_db

router = APIRouter(prefix="/checkin", tags=["checkin"])


def _resolve_device_id(request: Request, x_device_id: str | None) -> str:
    """Id estable que manda el kiosko, con fallback a IP si falta el header
    (decisión del equipo, HU-02)."""
    return x_device_id or (request.client.host if request.client else "desconocido")


def enforce_device_not_locked(
    request: Request,
    db: Session = Depends(get_db),
    x_device_id: str | None = Header(default=None),
) -> str:
    """RN-03 (HU-02 — Acceso denegado)."""
    device_id = _resolve_device_id(request, x_device_id)
    lock_repo = CheckinDeviceLockRepository(db)
    momento = _now()
    if lock_repo.is_locked(device_id, momento):
        bloqueado_hasta = lock_repo.bloqueado_hasta(device_id)
        raise HTTPException(
            status_code=423,
            detail={
                "mensaje": "Dispositivo bloqueado temporalmente. Intenta de nuevo más tarde.",
                "bloqueado_hasta": bloqueado_hasta.isoformat() if bloqueado_hasta else None,
            },
        )
    return device_id


def enforce_device_authorized(
    request: Request,
    db: Session = Depends(get_db),
    x_device_id: str | None = Header(default=None),
) -> str:
    """012-checkin-qr-dinamico: lista blanca de kioscos. Con el QR, un
    dispositivo no autorizado ya no es solo "alguien tantea cédulas" (RN-03)
    — puede generar nonces y quedar a la espera de que un socio real
    escanee. Se aplica también al check-in por cédula/invitado: ninguno
    debería poder operar desde un kiosko que el admin no autorizó."""
    device_id = _resolve_device_id(request, x_device_id)
    if not dispositivo_autorizado(device_id, db):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Dispositivo no autorizado")
    return device_id


@router.post("", response_model=CheckinResponse)
def post_checkin(
    payload: CheckinRequest,
    db: Session = Depends(get_db),
    _autorizado: str = Depends(enforce_device_authorized),
    device_id: str = Depends(enforce_device_not_locked),
) -> CheckinResponse:
    try:
        resultado, mensaje, nombre, visitas_restantes, razon = checkin_member(
            payload.cedula, device_id, db
        )
    except UsuarioNoEncontradoError:
        raise HTTPException(status_code=404, detail="Cédula no registrada")
    return CheckinResponse(
        resultado=resultado,
        mensaje=mensaje,
        nombre=nombre,
        visitas_restantes=visitas_restantes,
        razon=razon,
    )


@router.post("/guest", response_model=CheckinResponse)
def post_checkin_guest(
    payload: GuestCheckinRequest,
    db: Session = Depends(get_db),
    _autorizado: str = Depends(enforce_device_authorized),
    device_id: str = Depends(enforce_device_not_locked),
) -> CheckinResponse:
    """HU-05: el titular presente hace entrar a su invitado desde el kiosko.
    Mismo guard de dispositivo que el check-in normal (RN-03). El descuento de
    cupo y el registro del CheckIn son atómicos (RN-10)."""
    resultado, mensaje, nombre, visitas_restantes, razon = checkin_guest(
        payload.cedula_titular, payload.cedula_invitado, payload.nombre_invitado, db
    )
    return CheckinResponse(
        resultado=resultado,
        mensaje=mensaje,
        nombre=nombre,
        visitas_restantes=visitas_restantes,
        razon=razon,
    )


@router.post("/cortesia", response_model=CheckinResponse)
def post_cortesia(
    payload: CortesiaRequest,
    db: Session = Depends(get_db),
    _permiso: dict = Depends(require_permission("members.gestionar_usuarios")),
) -> CheckinResponse:
    """HU-04: el Staff registra la cortesía de primer día de un prospecto. Gateado
    con `members.gestionar_usuarios` (crea un User, mismo permiso que el CRUD de
    004). No usa el guard de dispositivo del kiosko: es un flujo de backoffice."""
    resultado, mensaje, nombre, visitas_restantes, razon = first_day_courtesy(
        payload.cedula, payload.nombre, db
    )
    return CheckinResponse(
        resultado=resultado,
        mensaje=mensaje,
        nombre=nombre,
        visitas_restantes=visitas_restantes,
        razon=razon,
    )


@router.get("/me/constancia", response_model=AttendanceConsistencyOut)
def get_mi_constancia(
    period: Literal["semana", "mes"] = "semana",
    db: Session = Depends(get_db),
    member=Depends(require_member),
) -> AttendanceConsistencyOut:
    return get_member_attendance_consistency(int(member["sub"]), db, period)


@router.get("/dispositivos-bloqueados", response_model=list[DispositivoBloqueadoInfo])
def get_dispositivos_bloqueados(
    db: Session = Depends(get_db),
    _permiso: dict = Depends(require_permission("checkin.ver_dispositivos_bloqueados")),
) -> list[DispositivoBloqueadoInfo]:
    bloqueados = CheckinDeviceLockRepository(db).listar_bloqueados(_now())
    return [DispositivoBloqueadoInfo.model_validate(b) for b in bloqueados]


@router.post("/desbloquear/{device_id}")
def post_desbloquear_dispositivo(
    device_id: str,
    db: Session = Depends(get_db),
    _permiso: dict = Depends(require_permission("checkin.desbloquear_dispositivo")),
) -> dict:
    CheckinDeviceLockRepository(db).reset_attempts(device_id)
    db.commit()
    return {"mensaje": f"Dispositivo {device_id} desbloqueado."}


# --- 012-checkin-qr-dinamico: check-in por QR ---


@router.post("/qr/nonce", response_model=QrNonceOut)
def post_qr_nonce(
    db: Session = Depends(get_db),
    device_id: str = Depends(enforce_device_authorized),
) -> QrNonceOut:
    """El kiosko pide esto al montar la pantalla de QR (y de nuevo si se le
    cae el WebSocket) — la rotación posterior la empuja `/ws/{device_id}`."""
    fila = generar_qr_nonce(device_id, db)
    return QrNonceOut(nonce=fila.nonce, expira_en=fila.expira_en)


@router.post("/qr/scan", response_model=CheckinResponse)
async def post_qr_scan(
    payload: QrScanRequest,
    db: Session = Depends(get_db),
    member: dict = Depends(require_member),
) -> CheckinResponse:
    """El socio escanea el QR desde el portal (ya logueado, `011`) y este
    endpoint valida el nonce + corre el motor de check-in. El resultado se
    empuja también al kiosko por WebSocket — el socio recibe el mismo
    resultado en su celular por si el kiosko no está a la vista."""
    try:
        resultado, mensaje, nombre, visitas_restantes, razon = checkin_via_qr(
            int(member["sub"]), payload.device_id, payload.nonce, db
        )
    except NonceInvalidoError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Código QR inválido o expirado")
    except members_service.UsuarioNoEncontradoError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuario no encontrado")

    response = CheckinResponse(
        resultado=resultado,
        mensaje=mensaje,
        nombre=nombre,
        visitas_restantes=visitas_restantes,
        razon=razon,
    )
    await ws_manager.push(
        payload.device_id, {"tipo": "resultado", **response.model_dump(mode="json")}
    )

    # El nonce que se acaba de escanear ya quedó `usado_en` — no se puede
    # esperar a la rotación programada (`qr_nonce_seconds`) para tener un QR
    # válido de nuevo, o cualquiera que intente escanear mientras tanto ve
    # "código inválido". Se genera y empuja uno nuevo de inmediato.
    nueva_fila = generar_qr_nonce(payload.device_id, db)
    await ws_manager.push(
        payload.device_id,
        {
            "tipo": "nonce",
            "nonce": nueva_fila.nonce,
            "expira_en": nueva_fila.expira_en.isoformat(),
        },
    )
    return response


@router.websocket("/ws/{device_id}")
async def ws_kiosko(websocket: WebSocket, device_id: str) -> None:
    """Conexión que mantiene abierta el kiosko: recibe la rotación del QR y
    el resultado del check-in (012-checkin-qr-dinamico). Sesión de BD de
    vida corta por operación (no `Depends(get_db)`) — a diferencia de un
    request normal, este socket puede quedar abierto por horas y no debería
    retener una conexión del pool todo ese tiempo."""
    db = SessionLocal()
    try:
        autorizado = dispositivo_autorizado(device_id, db)
    finally:
        db.close()
    if not autorizado:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await ws_manager.connect(device_id, websocket)
    try:
        while True:
            try:
                await asyncio.wait_for(
                    websocket.receive_text(), timeout=settings.qr_nonce_seconds
                )
            except asyncio.TimeoutError:
                db = SessionLocal()
                try:
                    fila = generar_qr_nonce(device_id, db)
                    # Leer los campos DENTRO del try: `db.close()` en el
                    # `finally` deja la instancia detached (SQLAlchemy expira
                    # los atributos tras commit) y acceder a `fila.nonce`
                    # después lanza DetachedInstanceError.
                    nonce_payload = {
                        "tipo": "nonce",
                        "nonce": fila.nonce,
                        "expira_en": fila.expira_en.isoformat(),
                    }
                finally:
                    db.close()
                await ws_manager.push(device_id, nonce_payload)
    except WebSocketDisconnect:
        pass
    finally:
        ws_manager.disconnect(device_id, websocket)


# --- 012-checkin-qr-dinamico: lista blanca de dispositivos autorizados ---


@router.post("/dispositivos/autorizar")
def post_autorizar_dispositivo(
    payload: DispositivoAutorizarRequest,
    db: Session = Depends(get_db),
    staff: dict = Depends(require_permission("checkin.autorizar_dispositivo")),
) -> dict:
    autorizar_dispositivo(payload.device_id, payload.etiqueta, int(staff["sub"]), db)
    return {"mensaje": f"Dispositivo {payload.device_id} autorizado."}


@router.get("/dispositivos/autorizados", response_model=list[DispositivoAutorizadoInfo])
def get_dispositivos_autorizados(
    db: Session = Depends(get_db),
    _permiso: dict = Depends(require_permission("checkin.autorizar_dispositivo")),
) -> list[DispositivoAutorizadoInfo]:
    return [DispositivoAutorizadoInfo.model_validate(d) for d in listar_dispositivos_autorizados(db)]


@router.delete("/dispositivos/autorizar/{device_id}")
def delete_autorizar_dispositivo(
    device_id: str,
    db: Session = Depends(get_db),
    _permiso: dict = Depends(require_permission("checkin.autorizar_dispositivo")),
) -> dict:
    revocar_dispositivo(device_id, db)
    return {"mensaje": f"Dispositivo {device_id} revocado."}

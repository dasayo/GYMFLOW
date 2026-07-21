"""
Router de checkin (HU-01 — Check-in con membresía activa y HU-02 — Acceso
denegado). Validación de entrada con Pydantic (checkin/schemas.py), nunca a
mano aquí (convención del proyecto).
"""
from typing import Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from auth.dependencies import require_member, require_permission
from checkin.repository import CheckinDeviceLockRepository
from checkin.schemas import (
    AttendanceConsistencyOut,
    CheckinRequest,
    CheckinResponse,
    CortesiaRequest,
    DispositivoBloqueadoInfo,
    GuestCheckinRequest,
)
from checkin.service import (
    UsuarioNoEncontradoError,
    checkin_guest,
    checkin_member,
    first_day_courtesy,
    get_member_attendance_consistency,
)
from core.config import now as _now
from core.database import get_db

router = APIRouter(prefix="/checkin", tags=["checkin"])


def enforce_device_not_locked(
    request: Request,
    db: Session = Depends(get_db),
    x_device_id: str | None = Header(default=None),
) -> str:
    """RN-03 (HU-02 — Acceso denegado): id estable que manda el kiosko, con
    fallback a IP si falta el header (decisión del equipo)."""
    device_id = x_device_id or (request.client.host if request.client else "desconocido")
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


@router.post("", response_model=CheckinResponse)
def post_checkin(
    payload: CheckinRequest,
    db: Session = Depends(get_db),
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

"""
Router de checkin (spec/features/001-checkin-membresia-activa,
002-acceso-denegado). Validación de entrada con Pydantic
(checkin/schemas.py), nunca a mano aquí (AGENTS.md).
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
    DispositivoBloqueadoInfo,
)
from checkin.service import UsuarioNoEncontradoError, checkin_member, get_member_attendance_consistency
from core.config import now as _now
from core.database import get_db

router = APIRouter(prefix="/checkin", tags=["checkin"])


def enforce_device_not_locked(
    request: Request,
    db: Session = Depends(get_db),
    x_device_id: str | None = Header(default=None),
) -> str:
    """RN-03 (002-acceso-denegado): id estable que manda el kiosko, con
    fallback a IP si falta el header (duda abierta de spec.md, resuelta así)."""
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

"""
Router de membership. Endpoints se agregan al implementar spec/features/001,
007, 009/ — `GET /membresias/tipos` es lectura mínima para 004 (elegir tipo
al asignar/renovar), no el CRUD completo de tipos (eso es 009).
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

import membership.service as membership_service
from auth.dependencies import require_member, require_role
from core.database import get_db
from membership.schemas import MembershipSummaryOut, MembershipTypeOut
from models import RolUsuario

router = APIRouter(prefix="/membresias", tags=["membership"])


@router.get("/tipos", response_model=list[MembershipTypeOut])
def get_tipos_activos(
    db: Session = Depends(get_db),
    _staff=Depends(require_role(RolUsuario.empleado, RolUsuario.administrador)),
) -> list[MembershipTypeOut]:
    return [MembershipTypeOut.model_validate(t) for t in membership_service.list_active_types(db)]


@router.get("/me/resumen", response_model=MembershipSummaryOut)
def get_mi_resumen(
    db: Session = Depends(get_db),
    member=Depends(require_member),
) -> MembershipSummaryOut:
    """007 (RF-04): resumen del propio Miembro logueado en el portal (011).
    El user_id sale del JWT — nunca de un parámetro, así un socio no puede
    consultar el resumen de otro."""
    return membership_service.get_membership_summary_detail(int(member["sub"]), db)

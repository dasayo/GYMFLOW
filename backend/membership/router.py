"""
Router de membership. `GET /membresias/tipos` es lectura mínima para HU-07
(elegir tipo al asignar/renovar); el CRUD completo del catálogo (HU-08) vive
bajo el mismo prefijo pero exige rol Administrador (RF-09).
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

import membership.service as membership_service
from auth.dependencies import require_member, require_role
from core.database import get_db
from membership.schemas import (
    MembershipSummaryOut,
    MembershipTypeAdminOut,
    MembershipTypeCreate,
    MembershipTypeOut,
    MembershipTypeUpdate,
)
from membership.service import (
    MembershipTypeConHistorialError,
    MembershipTypeConMembresiaActivaError,
    MembershipTypeNoEncontradoError,
)
from models import RolUsuario

router = APIRouter(prefix="/membresias", tags=["membership"])

_ADMIN = Depends(require_role(RolUsuario.administrador))


@router.get("/tipos", response_model=list[MembershipTypeOut])
def get_tipos_activos(
    db: Session = Depends(get_db),
    _staff=Depends(require_role(RolUsuario.empleado, RolUsuario.administrador)),
) -> list[MembershipTypeOut]:
    return [MembershipTypeOut.model_validate(t) for t in membership_service.list_active_types(db)]


@router.get("/tipos/admin", response_model=list[MembershipTypeAdminOut])
def get_tipos_admin(db: Session = Depends(get_db), _admin=_ADMIN) -> list[MembershipTypeAdminOut]:
    """009 (RF-09): catálogo completo (activos e inactivos) para el CRUD del
    Administrador. Declarado antes de `/tipos/{tipo_id}` para que "admin" no se
    capture como un id."""
    return [MembershipTypeAdminOut.model_validate(t) for t in membership_service.list_all_types(db)]


@router.post("/tipos", response_model=MembershipTypeAdminOut, status_code=status.HTTP_201_CREATED)
def post_tipo(
    payload: MembershipTypeCreate, db: Session = Depends(get_db), _admin=_ADMIN
) -> MembershipTypeAdminOut:
    tipo = membership_service.create_type(
        payload.nombre, payload.precio_base, payload.visitas_totales,
        payload.cupo_invitados, payload.duracion_dias, payload.activo, db,
    )
    db.commit()
    return MembershipTypeAdminOut.model_validate(tipo)


@router.put("/tipos/{tipo_id}", response_model=MembershipTypeAdminOut)
def put_tipo(
    tipo_id: int, payload: MembershipTypeUpdate, db: Session = Depends(get_db), _admin=_ADMIN
) -> MembershipTypeAdminOut:
    try:
        tipo = membership_service.update_type(
            tipo_id, db, **payload.model_dump(exclude_unset=True)
        )
    except MembershipTypeNoEncontradoError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tipo de membresía no encontrado")
    except MembershipTypeConMembresiaActivaError:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "No se puede desactivar: el tipo tiene membresías activas vinculadas (RN-05)",
        )
    db.commit()
    return MembershipTypeAdminOut.model_validate(tipo)


@router.delete("/tipos/{tipo_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tipo(tipo_id: int, db: Session = Depends(get_db), _admin=_ADMIN) -> None:
    try:
        membership_service.delete_type(tipo_id, db)
    except MembershipTypeNoEncontradoError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tipo de membresía no encontrado")
    except MembershipTypeConHistorialError:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Este tipo tiene historial de membresías; desactívalo en vez de eliminarlo",
        )
    db.commit()


@router.get("/me/resumen", response_model=MembershipSummaryOut)
def get_mi_resumen(
    db: Session = Depends(get_db),
    member=Depends(require_member),
) -> MembershipSummaryOut:
    """HU-06 (RF-04): resumen del propio Miembro logueado en el portal.
    El user_id sale del JWT — nunca de un parámetro, así un socio no puede
    consultar el resumen de otro."""
    return membership_service.get_membership_summary_detail(int(member["sub"]), db)

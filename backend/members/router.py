"""
Router de members (HU-07 — Gestión de usuarios, RF-10). Validación de entrada
con Pydantic (members/schemas.py), nunca a mano aquí (convención del proyecto).
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

import auth.service as auth_service
import members.service as members_service
from auth.dependencies import require_permission, require_role
from core.config import now as _now
from core.database import get_db
from members.schemas import (
    MembershipActionRequest,
    MembershipHistoryItem,
    UserCreate,
    UserOut,
    UserUpdate,
)
from members.service import (
    CedulaYaRegistradaError,
    EmailYaRegistradoError,
    UsuarioNoEncontradoError,
)
from membership.service import (
    MembershipNoExisteError,
    MembershipTypeNoEncontradoError,
    MembershipYaExisteError,
)
from models import RolUsuario

router = APIRouter(prefix="/usuarios", tags=["members"])

_STAFF = Depends(require_role(RolUsuario.empleado, RolUsuario.administrador))
# CRUD básico de usuarios: gateado con un permiso individual propio, no solo
# el rol Empleado/Administrador (RF-09) — decisión del equipo posterior al
# alcance original de HU-07, distinta de members.asignar_rol_empleado (ese
# controla A QUÉ ROL se puede crear/ascender, no si se puede gestionar
# usuarios en general). Los sub-recursos de membresías (asignar/historial)
# siguen con el guard de rol genérico, sin cambios.
_GESTIONAR_USUARIOS = Depends(require_permission("members.gestionar_usuarios"))


def _validar_rol_permitido(actor_payload: dict, rol_objetivo: RolUsuario, db: Session) -> None:
    """HU-07: quién puede crear/ascender un usuario a `rol_objetivo` — ver
    members.service.puede_asignar_rol. `administrador` nunca necesita
    permisos individuales para esto."""
    actor_rol = RolUsuario(actor_payload["rol"])
    actor_permisos = (
        set()
        if actor_rol == RolUsuario.administrador
        else auth_service.get_user_permissions(int(actor_payload["sub"]), db)
    )
    if not members_service.puede_asignar_rol(actor_rol, actor_permisos, rol_objetivo):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No tienes permiso para asignar ese rol")


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def post_usuario(
    payload: UserCreate, db: Session = Depends(get_db), _staff=_GESTIONAR_USUARIOS
) -> UserOut:
    _validar_rol_permitido(_staff, payload.rol, db)
    try:
        user = members_service.create_user(
            payload.cedula, payload.nombre, payload.email, payload.rol, payload.estado,
            payload.password, db,
        )
    except CedulaYaRegistradaError:
        raise HTTPException(status.HTTP_409_CONFLICT, "Ya existe un usuario con esa cédula")
    except EmailYaRegistradoError:
        raise HTTPException(status.HTTP_409_CONFLICT, "Ya existe un usuario con ese email")
    return UserOut.model_validate(user)


@router.get("", response_model=list[UserOut])
def get_usuarios(db: Session = Depends(get_db), _staff=_GESTIONAR_USUARIOS) -> list[UserOut]:
    return [UserOut.model_validate(u) for u in members_service.list_users(db)]


# OJO: esta ruta va declarada ANTES de "/{user_id}". FastAPI resuelve por
# orden de declaración, así que si estuviera después, "buscar" se intentaría
# parsear como `user_id: int` y el endpoint respondería 422.
@router.get("/buscar", response_model=list[UserOut])
def get_buscar_usuarios(
    q: str = Query(..., max_length=150),
    db: Session = Depends(get_db),
    _staff=_GESTIONAR_USUARIOS,
) -> list[UserOut]:
    """HU-03: búsqueda por coincidencia parcial de nombre O cédula en un
    solo campo. Gateada con el mismo permiso que el listado porque devuelve
    los mismos datos."""
    return [UserOut.model_validate(u) for u in members_service.search_users(q, db)]


@router.get("/{user_id}", response_model=UserOut)
def get_usuario(user_id: int, db: Session = Depends(get_db), _staff=_GESTIONAR_USUARIOS) -> UserOut:
    try:
        user = members_service.get_user(user_id, db)
    except UsuarioNoEncontradoError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuario no encontrado")
    return UserOut.model_validate(user)


@router.put("/{user_id}", response_model=UserOut)
def put_usuario(
    user_id: int, payload: UserUpdate, db: Session = Depends(get_db), _staff=_GESTIONAR_USUARIOS
) -> UserOut:
    if payload.rol is not None:
        _validar_rol_permitido(_staff, payload.rol, db)
    try:
        user = members_service.update_user(
            user_id, db, **payload.model_dump(exclude_unset=True)
        )
    except UsuarioNoEncontradoError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuario no encontrado")
    except CedulaYaRegistradaError:
        raise HTTPException(status.HTTP_409_CONFLICT, "Ya existe un usuario con esa cédula")
    except EmailYaRegistradoError:
        raise HTTPException(status.HTTP_409_CONFLICT, "Ya existe un usuario con ese email")
    return UserOut.model_validate(user)


@router.delete("/{user_id}", response_model=UserOut)
def delete_usuario(
    user_id: int, db: Session = Depends(get_db), _staff=_GESTIONAR_USUARIOS
) -> UserOut:
    """RN-07: anonimiza (no borra físicamente) — ver members/service.py."""
    try:
        user = members_service.anonymize_user(user_id, db)
    except UsuarioNoEncontradoError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuario no encontrado")
    return UserOut.model_validate(user)


def _to_history_item(membership) -> MembershipHistoryItem:
    hoy = _now().date()
    return MembershipHistoryItem(
        id=membership.id,
        tipo_id=membership.tipo_id,
        monto=membership.monto,
        nota=membership.nota,
        fecha_inicio=membership.fecha_inicio,
        fecha_vencimiento=membership.fecha_vencimiento,
        visitas_restantes=membership.visitas_restantes,
        cupo_invitados_restantes=membership.cupo_invitados_restantes,
        vigente=membership.fecha_inicio <= hoy <= membership.fecha_vencimiento,
    )


@router.get("/{user_id}/membresias", response_model=list[MembershipHistoryItem])
def get_historial_membresias(
    user_id: int, db: Session = Depends(get_db), _staff=_STAFF
) -> list[MembershipHistoryItem]:
    try:
        historial = members_service.get_membership_history(user_id, db)
    except UsuarioNoEncontradoError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuario no encontrado")
    return [_to_history_item(m) for m in historial]


@router.post("/{user_id}/membresias", response_model=MembershipHistoryItem)
def post_asignar_membresia(
    user_id: int, payload: MembershipActionRequest, db: Session = Depends(get_db), _staff=_STAFF
) -> MembershipHistoryItem:
    try:
        membership = members_service.assign_membership(
            user_id, payload.tipo_id, payload.monto, payload.nota, db
        )
    except UsuarioNoEncontradoError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuario no encontrado")
    except MembershipTypeNoEncontradoError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tipo de membresía no encontrado")
    except MembershipYaExisteError:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "El usuario ya tiene una membresía — usa renovar en su lugar",
        )
    return _to_history_item(membership)


@router.post("/{user_id}/membresias/renovar", response_model=MembershipHistoryItem)
def post_renovar_membresia(
    user_id: int,
    payload: MembershipActionRequest,
    db: Session = Depends(get_db),
    _permiso=Depends(require_permission("membership.renovar")),
) -> MembershipHistoryItem:
    try:
        membership = members_service.renew_membership(
            user_id, payload.tipo_id, payload.monto, payload.nota, db
        )
    except UsuarioNoEncontradoError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuario no encontrado")
    except MembershipTypeNoEncontradoError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tipo de membresía no encontrado")
    except MembershipNoExisteError:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "El usuario no tiene ninguna membresía previa — usa asignar en su lugar",
        )
    return _to_history_item(membership)

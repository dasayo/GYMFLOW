"""
Router de auth.
"""
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

import auth.service as auth_service
from auth.dependencies import require_role
from auth.schemas import (
    LoginRequest,
    LoginResponse,
    PermisoGrantRequest,
    PermisoOut,
    PortalActivateRequest,
    PortalLoginRequest,
    PortalSessionResponse,
)
from auth.service import (
    ActivacionInvalidaError,
    CredencialesInvalidasError,
    PermisoInexistenteError,
    SesionInvalidaError,
)
from auth.service import login as login_service
from core.config import settings
from core.database import get_db
from members.service import UsuarioNoEncontradoError
from models import RolUsuario

router = APIRouter(prefix="/auth", tags=["auth"])

_ADMIN = Depends(require_role(RolUsuario.administrador))

# Cookie httpOnly del refresh token del portal (011). path="/" y no
# "/auth/portal" porque el navegador ve la API detrás del proxy con prefijo
# /api (nginx/Vite lo recortan antes de llegar aquí) — un path del lado del
# backend nunca coincidiría con la URL que ve el navegador.
_REFRESH_COOKIE = "gymflow_refresh"


def _set_refresh_cookie(response: Response, raw_token: str) -> None:
    response.set_cookie(
        key=_REFRESH_COOKIE,
        value=raw_token,
        max_age=settings.member_refresh_days * 24 * 60 * 60,
        httponly=True,
        samesite="lax",
        secure=settings.environment == "production",
        path="/",
    )


@router.post("/portal/login", response_model=PortalSessionResponse)
def post_portal_login(
    payload: PortalLoginRequest, response: Response, db: Session = Depends(get_db)
) -> PortalSessionResponse:
    try:
        access_token, raw_refresh, user = auth_service.login_member(
            payload.email, payload.password, db
        )
    except CredencialesInvalidasError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Credenciales inválidas")
    _set_refresh_cookie(response, raw_refresh)
    return PortalSessionResponse(access_token=access_token, nombre=user.nombre)


def _respuesta_sesion_invalida() -> JSONResponse:
    """401 que además borra la cookie muerta. No se usa HTTPException porque
    su handler arma una respuesta nueva y descartaría el Set-Cookie puesto en
    el Response inyectado."""
    respuesta = JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED, content={"detail": "Sesión inválida"}
    )
    respuesta.delete_cookie(_REFRESH_COOKIE, path="/")
    return respuesta


@router.post("/portal/refresh", response_model=PortalSessionResponse)
def post_portal_refresh(
    response: Response,
    db: Session = Depends(get_db),
    refresh_token: Annotated[str | None, Cookie(alias=_REFRESH_COOKIE)] = None,
):
    if refresh_token is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sesión inválida")
    try:
        access_token, raw_refresh, user = auth_service.refresh_member_session(refresh_token, db)
    except SesionInvalidaError:
        return _respuesta_sesion_invalida()
    _set_refresh_cookie(response, raw_refresh)
    return PortalSessionResponse(access_token=access_token, nombre=user.nombre)


@router.post("/portal/activar", status_code=status.HTTP_204_NO_CONTENT)
def post_portal_activar(payload: PortalActivateRequest, db: Session = Depends(get_db)) -> None:
    try:
        auth_service.activate_member_account(
            payload.cedula, payload.email, payload.password, db
        )
    except ActivacionInvalidaError:
        # Mensaje único: no se revela si la cédula existe, si el correo no
        # coincide o si la cuenta ya estaba activada (spec 011).
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No se pudo activar la cuenta")


@router.post("/portal/logout", status_code=status.HTTP_204_NO_CONTENT)
def post_portal_logout(
    response: Response,
    db: Session = Depends(get_db),
    refresh_token: Annotated[str | None, Cookie(alias=_REFRESH_COOKIE)] = None,
) -> None:
    if refresh_token is not None:
        auth_service.logout_member(refresh_token, db)
    response.delete_cookie(_REFRESH_COOKIE, path="/")


@router.post("/login", response_model=LoginResponse)
def post_login(payload: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    try:
        token, rol, permisos = login_service(payload.email, payload.password, db)
    except CredencialesInvalidasError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Credenciales inválidas")
    return LoginResponse(access_token=token, rol=rol, permisos=sorted(permisos))


@router.get("/permisos", response_model=list[PermisoOut])
def get_catalogo_permisos(db: Session = Depends(get_db), _admin=_ADMIN) -> list[PermisoOut]:
    return [PermisoOut.model_validate(p) for p in auth_service.list_permissions_catalog(db)]


@router.get("/usuarios/{user_id}/permisos", response_model=list[PermisoOut])
def get_permisos_usuario(
    user_id: int, db: Session = Depends(get_db), _admin=_ADMIN
) -> list[PermisoOut]:
    try:
        permisos = auth_service.list_permissions(user_id, db)
    except UsuarioNoEncontradoError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuario no encontrado")
    return [PermisoOut.model_validate(p) for p in permisos]


@router.post("/usuarios/{user_id}/permisos", status_code=status.HTTP_204_NO_CONTENT)
def post_otorgar_permiso(
    user_id: int, payload: PermisoGrantRequest, db: Session = Depends(get_db), _admin=_ADMIN
) -> None:
    try:
        auth_service.grant_permission(user_id, payload.codigo, db)
    except UsuarioNoEncontradoError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuario no encontrado")
    except PermisoInexistenteError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Código de permiso no existe")


@router.delete("/usuarios/{user_id}/permisos/{codigo}", status_code=status.HTTP_204_NO_CONTENT)
def delete_quitar_permiso(
    user_id: int, codigo: str, db: Session = Depends(get_db), _admin=_ADMIN
) -> None:
    try:
        auth_service.revoke_permission(user_id, codigo, db)
    except UsuarioNoEncontradoError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuario no encontrado")
    except PermisoInexistenteError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Código de permiso no existe")

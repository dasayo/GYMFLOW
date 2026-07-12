"""
Dependencias FastAPI de auth: quién es el usuario autenticado (RN-11) y qué
puede hacer (RBAC por rol y permisos individuales, RF-09). La lógica de
negocio vive aquí, no en core/security.py (que solo tiene primitivas técnicas
de hash/JWT, según su propio docstring).
"""
import jwt
from fastapi import Depends, HTTPException, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

import auth.service as auth_service
from core.database import get_db
from core.security import create_access_token, decode_access_token
from models import RolUsuario

# HTTPBearer, no OAuth2PasswordBearer: solo extrae el header "Authorization:
# Bearer <token>", sin ninguna semántica de flujo OAuth2 (límite duro de
# AGENTS.md: "no OAuth2 Authorization Server").
_bearer_scheme = HTTPBearer(auto_error=True)


def get_current_user(
    response: Response,
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
) -> dict:
    """RN-11: valida el JWT y, si sigue vigente, lo reemite con `exp`
    renovado a +30min en el header de respuesta `X-New-Token` (expiración
    deslizante — no hay sesión server-side que renovar)."""
    try:
        payload = decode_access_token(credentials.credentials)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sesión expirada")
    except jwt.InvalidTokenError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token inválido")

    nuevo_token = create_access_token({"sub": payload["sub"], "rol": payload["rol"]})
    response.headers["X-New-Token"] = nuevo_token
    return payload


def get_current_member(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
) -> dict:
    """011: valida el access token del portal del Miembro. Exige el claim
    `kind=member` (los JWT de staff de 003 no lo llevan, así una población de
    tokens no sirve en la otra). Sin expiración deslizante: la renovación del
    portal es por refresh token (rotación), no por reemisión silenciosa."""
    try:
        payload = decode_access_token(credentials.credentials)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sesión expirada")
    except jwt.InvalidTokenError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token inválido")

    if payload.get("kind") != "member" or payload.get("rol") != RolUsuario.miembro.value:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Solo para Miembros del portal")
    return payload


def require_member(payload: dict = Depends(get_current_member)) -> dict:
    """Alias declarativo, simétrico a require_role: Depends(require_member)."""
    return payload


def require_role(*roles: RolUsuario):
    """RBAC declarativo por rol (RF-09): Depends(require_role(RolUsuario.administrador))."""
    permitidos = {r.value for r in roles}

    def _verificar(payload: dict = Depends(get_current_user)) -> dict:
        if payload.get("rol") not in permitidos:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Rol insuficiente")
        return payload

    return _verificar


def require_permission(*codigos: str):
    """RBAC fino por permiso individual (spec/features/003): el rol
    `administrador` tiene implícitamente todos los permisos, sin necesidad de
    filas en `usuario_permisos`. Cualquier otro rol necesita al menos uno de
    los códigos requeridos otorgado explícitamente."""
    requeridos = set(codigos)

    def _verificar(
        payload: dict = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> dict:
        if payload.get("rol") == RolUsuario.administrador.value:
            return payload
        otorgados = auth_service.get_user_permissions(int(payload["sub"]), db)
        if not (requeridos & otorgados):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Permiso insuficiente")
        return payload

    return _verificar

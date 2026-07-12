"""
Schemas Pydantic de auth (entrada/salida de API). Toda validación de entrada
vive aquí, nunca a mano en el router (AGENTS.md).
"""
from pydantic import BaseModel, Field

from models import RolUsuario


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    rol: RolUsuario
    permisos: list[str]


class PortalLoginRequest(BaseModel):
    """011: login del Miembro en el portal."""

    email: str
    password: str


class PortalSessionResponse(BaseModel):
    """011: respuesta de login/refresh del portal. El refresh token NO va
    aquí — viaja solo en la cookie httpOnly. `nombre` alimenta el saludo
    del Dashboard."""

    access_token: str
    token_type: str = "bearer"
    nombre: str | None


class PortalActivateRequest(BaseModel):
    """011: activación de cuenta creada por el staff (dudas resueltas en
    spec.md). Contraseña no vacía — mismo criterio que el alta de staff
    (004 no fija un mínimo de longitud; no se inventa uno aquí)."""

    cedula: str
    email: str
    password: str = Field(min_length=1)


class PermisoGrantRequest(BaseModel):
    """004-gestion-usuarios: otorgar un permiso individual a un usuario."""

    codigo: str


class PermisoOut(BaseModel):
    codigo: str
    descripcion: str | None

    model_config = {"from_attributes": True}

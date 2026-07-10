"""
Schemas Pydantic de auth (entrada/salida de API). Toda validación de entrada
vive aquí, nunca a mano en el router (AGENTS.md).
"""
from pydantic import BaseModel

from models import RolUsuario


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    rol: RolUsuario

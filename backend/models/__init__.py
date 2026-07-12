"""
Modelos SQLAlchemy centralizados (backend/models/, según AGENTS.md y tech-stack.md).
Un archivo por entidad. Se importan todos aquí para que Alembic los detecte
en autogenerate (ver backend/alembic/env.py).
"""
from models.user import User, RolUsuario, EstadoUsuario
from models.membership_type import MembershipType
from models.membership import Membership, EstadoMembresia
from models.checkin import CheckIn, ResultadoCheckin
from models.checkin_device_lock import CheckinDeviceLock
from models.guest import Guest
from models.permiso import Permiso, usuario_permisos
from models.refresh_token import RefreshToken

__all__ = [
    "User",
    "RolUsuario",
    "EstadoUsuario",
    "MembershipType",
    "Membership",
    "EstadoMembresia",
    "CheckIn",
    "ResultadoCheckin",
    "CheckinDeviceLock",
    "Guest",
    "Permiso",
    "usuario_permisos",
    "RefreshToken",
]

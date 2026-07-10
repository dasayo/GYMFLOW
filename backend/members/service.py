"""
Servicio de members.

Regla de módulos (no negociable, AGENTS.md): este service es el ÚNICO punto de
entrada que otros módulos pueden llamar para leer/mutar datos de members.
Ningún otro módulo debe importar members/repository.py directamente.
"""
from sqlalchemy.orm import Session

from members.repository import MembersRepository
from models import User


def get_user_by_cedula(cedula: str, db: Session) -> User | None:
    return MembersRepository(db).get_by_cedula(cedula)


def get_user_by_email(email: str, db: Session) -> User | None:
    return MembersRepository(db).get_by_email(email)

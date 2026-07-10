"""
Repository de members — único punto de acceso a la tabla `usuarios` (AGENTS.md).
Métodos concretos se agregan al implementar spec/features/001, 004, 005, 006.
"""
from sqlalchemy.orm import Session

from models import User


class MembersRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_cedula(self, cedula: str) -> User | None:
        return self.db.query(User).filter(User.cedula == cedula).first()

    def get_by_email(self, email: str) -> User | None:
        return self.db.query(User).filter(User.email == email).first()

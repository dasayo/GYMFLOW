"""
Repository de auth — único punto de acceso a las tablas `permisos` y
`usuario_permisos` (spec/features/003-autenticacion-segura). `auth` sigue
sin repository para `usuarios`: eso sigue siendo de members (AGENTS.md).
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from models import Permiso, usuario_permisos


class AuthRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_permission_codes(self, usuario_id: int) -> set[str]:
        query = (
            select(Permiso.codigo)
            .join(usuario_permisos, usuario_permisos.c.permiso_id == Permiso.id)
            .where(usuario_permisos.c.usuario_id == usuario_id)
        )
        return set(self.db.scalars(query).all())

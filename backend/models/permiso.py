"""
Tablas `permisos` y `usuario_permisos` — dueño: auth (spec/features/003-autenticacion-segura).
Permisos individuales por usuario, independientes del rol. `administrador`
tiene implícitamente todos los permisos (ver auth/dependencies.py), no
necesita filas en `usuario_permisos`.
"""
from sqlalchemy import Column, ForeignKey, Integer, String, Table

from core.database import Base

usuario_permisos = Table(
    "usuario_permisos",
    Base.metadata,
    Column("usuario_id", Integer, ForeignKey("usuarios.id"), primary_key=True),
    Column("permiso_id", Integer, ForeignKey("permisos.id"), primary_key=True),
)


class Permiso(Base):
    __tablename__ = "permisos"

    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String(100), unique=True, nullable=False, index=True)
    descripcion = Column(String(255), nullable=True)

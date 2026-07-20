"""
Tabla `usuarios` — dueño: members (ver tech-stack.md).
"""
import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class RolUsuario(str, enum.Enum):
    invitado = "invitado"
    miembro = "miembro"
    empleado = "empleado"
    administrador = "administrador"


class EstadoUsuario(str, enum.Enum):
    activo = "activo"
    inactivo = "inactivo"


class User(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    # nullable=True: RN-07 anonimiza (borra PII) preservando la fila para el
    # histórico de CheckIn (FK usuario_id). Ver duda abierta en 004-gestion-usuarios.
    cedula: Mapped[str | None] = mapped_column(String(20), unique=True, index=True)
    nombre: Mapped[str | None] = mapped_column(String(150))
    email: Mapped[str | None] = mapped_column(String(150), unique=True)
    rol: Mapped[RolUsuario] = mapped_column(default=RolUsuario.miembro)
    estado: Mapped[EstadoUsuario] = mapped_column(default=EstadoUsuario.activo)
    # Solo Empleado/Administrador tienen credenciales (HU-10, RN-12). Nunca texto plano.
    password_hash: Mapped[str | None] = mapped_column(String(255))
    creado_en: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    # 005: marca que esta cédula ya usó su cortesía de primer día (RF-07). Un
    # "Prospecto" es un User con rol=invitado y este flag en True (decisión del
    # equipo sobre la duda abierta del spec: flag, no un valor de enum nuevo).
    # Impide una segunda cortesía; se conserva al afiliarse (004) para no
    # concederla de nuevo aunque el rol pase a miembro.
    cortesia_usada: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

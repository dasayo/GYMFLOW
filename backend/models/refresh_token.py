"""
Tabla `refresh_tokens` — dueño: auth (spec/features/011-portal-miembro-autenticacion).
Sesión larga del Miembro: se guarda el SHA-256 del token opaco, nunca el token
en claro. Rotación: al usarse se marca `revocado_en` y se emite uno nuevo con
la ventana deslizante de 7 días renovada.
"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expira_en: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    creado_en: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    revocado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

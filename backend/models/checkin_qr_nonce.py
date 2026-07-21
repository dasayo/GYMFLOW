"""
Tabla `checkin_qr_nonces` — dueño: el módulo checkin (HU-03 — 012-checkin-qr-dinamico).
En tabla, no en memoria, mismo criterio que `checkin_device_locks` (correcto
con múltiples workers de uvicorn).
"""
from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class CheckinQrNonce(Base):
    __tablename__ = "checkin_qr_nonces"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    device_id: Mapped[str] = mapped_column(String(100), index=True)
    nonce: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expira_en: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    # None mientras el nonce sigue vigente; un socio solo puede consumirlo una vez.
    usado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

"""
Tabla `checkins` — dueño: el módulo checkin (RF-05). Registro inmutable.
"""
import enum
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class ResultadoCheckin(str, enum.Enum):
    exitoso = "exitoso"
    denegado = "denegado"


class CheckIn(Base):
    __tablename__ = "checkins"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), index=True)
    fecha_hora: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    resultado: Mapped[ResultadoCheckin]
    # Distingue al menos: MEMBRESIA_VENCIDA, SIN_VISITAS, YA_INGRESO_HOY,
    # DISPOSITIVO_BLOQUEADO (HU-02 — Acceso denegado).
    razon_denegacion: Mapped[str | None] = mapped_column(String(50))
    # Solo se llena en check-in de invitado (HU-05 — Check-in de invitado).
    titular_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"))
    # true = acceso ya concedido para el día calendario de fecha_hora (HU-01):
    # un reingreso exitoso el mismo día no crea otro is_active=true ni
    # descuenta visita. La query siempre filtra también por fecha (ver
    # checkin/repository.py) — un is_active=true de un día anterior no cuenta.
    is_active: Mapped[bool] = mapped_column(default=False)

    # Índice único parcial (usuario_id, DATE(fecha_hora)) WHERE is_active=true
    # se agrega en la migración de Alembic de HU-01 (anti doble
    # check-in concurrente, RN-02).

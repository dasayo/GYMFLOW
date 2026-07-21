"""
Tabla `dispositivos_autorizados` — dueño: el módulo checkin (012-checkin-qr-dinamico).
Lista blanca de kioscos: con el check-in por QR, un dispositivo no
autorizado ya no es solo "alguien tantea cédulas" (RN-03) — puede generar
nonces y esperar a que un socio real escanee. Identidad = `X-Device-Id`
(mismo UUID persistido en el navegador que ya usa RN-03): un navegador no
puede leer IP ni MAC del equipo, así que es la única identidad estable
disponible del lado del cliente.
"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class DispositivoAutorizado(Base):
    __tablename__ = "dispositivos_autorizados"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    device_id: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    etiqueta: Mapped[str | None] = mapped_column(String(100))
    autorizado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    autorizado_por_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))

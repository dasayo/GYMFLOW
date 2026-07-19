"""
Repository de checkin — único punto de acceso a la tabla `checkins` (AGENTS.md).
Métodos concretos se agregan al implementar spec/features/001, 002, 005, 006.
"""
from datetime import date, datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from core.config import settings
from models import CheckIn, CheckinDeviceLock

VENTANA_INTENTOS = timedelta(minutes=5)
DURACION_BLOQUEO = timedelta(minutes=20)
MAX_INTENTOS = 3


class CheckinRepository:
    def __init__(self, db: Session):
        self.db = db

    def exists_successful_checkin_today(self, user_id: int, hoy: date) -> bool:
        """RN-02 (Filtro 1): filtra explícitamente por día calendario (zona
        horaria del gimnasio) además de `is_active` — un `is_active=true` de
        un día anterior no cuenta (ver spec.md de 001)."""
        dia_gimnasio = func.date(func.timezone(settings.timezone, CheckIn.fecha_hora))
        return (
            self.db.query(CheckIn)
            .filter(
                CheckIn.usuario_id == user_id,
                CheckIn.is_active.is_(True),
                dia_gimnasio == hoy,
            )
            .first()
            is not None
        )

    def insert(self, checkin: CheckIn) -> CheckIn:
        self.db.add(checkin)
        self.db.flush()
        return checkin

    def list_attendances_in_range(self, fecha_inicio: date, fecha_fin: date) -> list[CheckIn]:
        """010 (RF-12): asistencias en el rango [fecha_inicio, fecha_fin] (días
        calendario del gimnasio, ambos inclusive). Solo filas `is_active=true`
        —la "unidad de conteo es día de asistencia", así los reingresos del
        mismo día (`is_active=false`) no inflan el reporte (ver spec.md de 010).
        Ordenado por `fecha_hora` ascendente. Consulta sobre la tabla propia."""
        dia_gimnasio = func.date(func.timezone(settings.timezone, CheckIn.fecha_hora))
        return (
            self.db.query(CheckIn)
            .filter(
                CheckIn.is_active.is_(True),
                dia_gimnasio >= fecha_inicio,
                dia_gimnasio <= fecha_fin,
            )
            .order_by(CheckIn.fecha_hora.asc(), CheckIn.id.asc())
            .all()
        )

    def list_successful_by_user_in_range(
        self, user_id: int, fecha_inicio: date, fecha_fin: date
    ) -> list[CheckIn]:
        """Consulta de solo lectura de asistencias exitosas del usuario en el
        rango de fechas solicitado para mostrar constancia en el portal."""
        dia_gimnasio = func.date(func.timezone(settings.timezone, CheckIn.fecha_hora))
        return (
            self.db.query(CheckIn)
            .filter(
                CheckIn.usuario_id == user_id,
                CheckIn.is_active.is_(True),
                dia_gimnasio >= fecha_inicio,
                dia_gimnasio <= fecha_fin,
            )
            .order_by(CheckIn.fecha_hora.asc(), CheckIn.id.asc())
            .all()
        )


class CheckinDeviceLockRepository:
    """RN-03 (002-acceso-denegado): contador de intentos fallidos por
    dispositivo en tabla, no en memoria (varios workers de uvicorn)."""

    def __init__(self, db: Session):
        self.db = db

    def _get_or_create(self, device_id: str) -> CheckinDeviceLock:
        lock = (
            self.db.query(CheckinDeviceLock)
            .filter(CheckinDeviceLock.device_id == device_id)
            .with_for_update()
            .first()
        )
        if lock is None:
            lock = CheckinDeviceLock(device_id=device_id, intentos_fallidos=0)
            self.db.add(lock)
            self.db.flush()
        return lock

    def is_locked(self, device_id: str, momento: datetime) -> bool:
        lock = (
            self.db.query(CheckinDeviceLock)
            .filter(CheckinDeviceLock.device_id == device_id)
            .first()
        )
        return bool(lock and lock.bloqueado_hasta and lock.bloqueado_hasta > momento)

    def bloqueado_hasta(self, device_id: str) -> datetime | None:
        lock = (
            self.db.query(CheckinDeviceLock)
            .filter(CheckinDeviceLock.device_id == device_id)
            .first()
        )
        return lock.bloqueado_hasta if lock else None

    def register_failed_attempt(self, device_id: str, momento: datetime) -> None:
        """Solo se llama para denegaciones por CEDULA_NO_ENCONTRADA (RN-03,
        spec.md de 002) — MEMBRESIA_VENCIDA/SIN_VISITAS no cuentan."""
        lock = self._get_or_create(device_id)
        if lock.ventana_inicio is None or momento - lock.ventana_inicio > VENTANA_INTENTOS:
            lock.ventana_inicio = momento
            lock.intentos_fallidos = 1
        else:
            lock.intentos_fallidos += 1
        if lock.intentos_fallidos >= MAX_INTENTOS:
            lock.bloqueado_hasta = momento + DURACION_BLOQUEO
        self.db.flush()

    def reset_attempts(self, device_id: str) -> None:
        """Un check-in exitoso reinicia el contador (spec.md de 002)."""
        lock = self._get_or_create(device_id)
        lock.intentos_fallidos = 0
        lock.ventana_inicio = None
        lock.bloqueado_hasta = None
        self.db.flush()

    def listar_bloqueados(self, momento: datetime) -> list[CheckinDeviceLock]:
        """Para que Staff sepa qué `device_id` desbloquear manualmente — hoy
        no hay forma de verlo salvo consultando esto (sin panel todavía)."""
        return (
            self.db.query(CheckinDeviceLock)
            .filter(CheckinDeviceLock.bloqueado_hasta.isnot(None))
            .filter(CheckinDeviceLock.bloqueado_hasta > momento)
            .all()
        )

"""
Schemas Pydantic de checkin (entrada/salida de API) — HU-01, HU-02, HU-04 y
HU-05. Toda validación de entrada vive aquí, nunca a mano en el router
(convención del proyecto).
"""
import enum
from datetime import date, datetime
from typing import Literal, Self

from pydantic import BaseModel, field_validator, model_validator

# Mismo criterio de cédula que checkin.service (HU-02): solo dígitos, 5 a 15.
_CEDULA_MIN = 5
_CEDULA_MAX = 15


class CheckinResultado(str, enum.Enum):
    exitoso = "exitoso"
    denegado = "denegado"


class RazonDenegacion(str, enum.Enum):
    """HU-02 — sin `YA_INGRESO_HOY`: un reingreso el mismo día es
    Exitoso (HU-01, RN-02), no una razón de denegación."""

    membresia_vencida = "MEMBRESIA_VENCIDA"
    sin_visitas = "SIN_VISITAS"
    cedula_no_encontrada = "CEDULA_NO_ENCONTRADA"
    dispositivo_bloqueado = "DISPOSITIVO_BLOQUEADO"
    # HU-04: la cédula ya usó su cortesía de primer día — no se concede otra.
    cortesia_ya_utilizada = "CORTESIA_YA_UTILIZADA"
    # HU-04: se intentó dar cortesía a una cédula ya registrada (socio/staff);
    # esa persona no es un prospecto nuevo, debe hacer check-in normal.
    ya_registrado = "YA_REGISTRADO"
    # HU-05: el titular indicado no existe en el sistema.
    titular_no_encontrado = "TITULAR_NO_ENCONTRADO"
    # HU-05: el titular no tiene una membresía activa/vigente que avale invitados.
    titular_sin_membresia = "TITULAR_SIN_MEMBRESIA"
    # HU-05: el titular ya agotó su cupo de invitados de este ciclo (RN-04).
    sin_cupo_invitados = "SIN_CUPO_INVITADOS"


class CheckinRequest(BaseModel):
    cedula: str


class CortesiaRequest(BaseModel):
    """HU-04: registro de cortesía por el Staff (no self-service en kiosko).
    El Staff verifica la identidad en persona, por eso el nombre es obligatorio."""

    cedula: str
    nombre: str

    @field_validator("cedula")
    @classmethod
    def cedula_valida(cls, v: str) -> str:
        v = v.strip()
        if not (v.isdigit() and _CEDULA_MIN <= len(v) <= _CEDULA_MAX):
            raise ValueError("La cédula debe tener entre 5 y 15 dígitos.")
        return v

    @field_validator("nombre")
    @classmethod
    def nombre_no_vacio(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("El nombre es obligatorio.")
        return v


class GuestCheckinRequest(BaseModel):
    """HU-05: el titular (presente en el kiosko) hace entrar a su invitado.
    Se piden ambas cédulas + el nombre del invitado (para el mensaje de
    bienvenida y para registrar su identidad)."""

    cedula_titular: str
    cedula_invitado: str
    nombre_invitado: str

    @field_validator("cedula_titular", "cedula_invitado")
    @classmethod
    def cedula_valida(cls, v: str) -> str:
        v = v.strip()
        if not (v.isdigit() and _CEDULA_MIN <= len(v) <= _CEDULA_MAX):
            raise ValueError("La cédula debe tener entre 5 y 15 dígitos.")
        return v

    @field_validator("nombre_invitado")
    @classmethod
    def nombre_no_vacio(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("El nombre del invitado es obligatorio.")
        return v

    @model_validator(mode="after")
    def titular_e_invitado_distintos(self) -> Self:
        if self.cedula_titular == self.cedula_invitado:
            raise ValueError("El invitado y el titular no pueden ser la misma persona.")
        return self


class CheckinResponse(BaseModel):
    resultado: CheckinResultado
    mensaje: str
    nombre: str | None = None
    visitas_restantes: int | None = None
    razon: RazonDenegacion | None = None


class AttendancePointOut(BaseModel):
    fecha: date
    asistencias: int


class AttendanceConsistencyOut(BaseModel):
    periodo: Literal["semana", "mes"]
    total: int
    puntos: list[AttendancePointOut]


class DispositivoBloqueadoResponse(BaseModel):
    mensaje: str
    bloqueado_hasta: datetime


class DispositivoBloqueadoInfo(BaseModel):
    """Para que Staff sepa qué `device_id` pasarle al endpoint de desbloqueo
    manual — sin esto no hay forma de saber cuál dispositivo es cuál."""

    device_id: str
    intentos_fallidos: int
    bloqueado_hasta: datetime

    model_config = {"from_attributes": True}


class QrNonceOut(BaseModel):
    """012-checkin-qr-dinamico: el kiosko codifica esto en el QR que muestra."""

    nonce: str
    expira_en: datetime


class QrScanRequest(BaseModel):
    """012-checkin-qr-dinamico: lo que el portal manda al escanear el QR del
    kiosko — decodificado del propio QR, no lo escribe el socio a mano."""

    device_id: str
    nonce: str


class DispositivoAutorizarRequest(BaseModel):
    device_id: str
    etiqueta: str | None = None


class DispositivoAutorizadoInfo(BaseModel):
    device_id: str
    etiqueta: str | None
    autorizado_en: datetime

    model_config = {"from_attributes": True}

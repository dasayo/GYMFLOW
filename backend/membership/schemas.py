"""
Schemas Pydantic de membership (entrada/salida de API) — HU-01, HU-06 y
HU-08. Toda validación de entrada vive aquí, nunca a mano en el router
(convención del proyecto).
"""
from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class MembershipSummary(BaseModel):
    """Mínimo del semáforo (HU-01); el detalle completo lo amplía HU-06."""

    tipo: str
    visitas_restantes: int
    fecha_vencimiento: date


class MembershipSummaryOut(BaseModel):
    """Resumen completo del portal del socio (HU-06, RF-04). Solo datos de
    membresía, sin PII. `dias_restantes` se calcula en cada consulta
    (`fecha_vencimiento - hoy`), nunca se almacena; es `None` cuando no hay
    membresía vigente (ya venció: no aplica contar días)."""

    estado: Literal["activa", "vencida", "sin_plan"]
    tipo: str | None
    fecha_vencimiento: date | None
    visitas_restantes: int | None
    cupo_invitados_restantes: int | None
    dias_restantes: int | None


class MembershipTypeOut(BaseModel):
    """Lectura mínima de `MembershipType` para elegir un tipo al
    asignar/renovar (HU-07) — el CRUD completo es de HU-08."""

    id: int
    nombre: str
    precio_base: Decimal
    visitas_totales: int
    cupo_invitados: int
    duracion_dias: int

    model_config = {"from_attributes": True}


class MembershipTypeAdminOut(MembershipTypeOut):
    """Lectura completa para el CRUD del Administrador (HU-08): añade `activo`,
    que el `GET /membresias/tipos` de empleado (solo activos) no expone."""

    activo: bool


class MembershipTypeCreate(BaseModel):
    """Alta de un tipo de membresía (HU-08, RF-11). Validaciones aquí, nunca a
    mano en el router (convención del proyecto)."""

    nombre: str = Field(min_length=1, max_length=100)
    precio_base: Decimal = Field(ge=0)
    visitas_totales: int = Field(ge=0)
    cupo_invitados: int = Field(ge=0)
    duracion_dias: int = Field(gt=0)
    activo: bool = True


class MembershipTypeUpdate(BaseModel):
    """Edición parcial de un tipo (HU-08). Todos los campos opcionales; solo se
    aplican los enviados (`exclude_unset`). RN-06: editar aquí nunca recalcula
    los saldos de `Membership` ya vendidas (son snapshot)."""

    nombre: str | None = Field(default=None, min_length=1, max_length=100)
    precio_base: Decimal | None = Field(default=None, ge=0)
    visitas_totales: int | None = Field(default=None, ge=0)
    cupo_invitados: int | None = Field(default=None, ge=0)
    duracion_dias: int | None = Field(default=None, gt=0)
    activo: bool | None = None

    model_config = ConfigDict(extra="forbid")

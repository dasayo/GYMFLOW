"""
Schemas Pydantic de membership (entrada/salida de API). Se agregan al implementar
spec/features/001, 007, 009/. Toda validación de entrada vive aquí, nunca a
mano en el router (AGENTS.md).
"""
from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel


class MembershipSummary(BaseModel):
    """Mínimo del semáforo (001); el detalle completo lo amplía 007."""

    tipo: str
    visitas_restantes: int
    fecha_vencimiento: date


class MembershipSummaryOut(BaseModel):
    """Resumen completo del portal del socio (007, RF-04). Solo datos de
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
    asignar/renovar (004) — el CRUD completo es de `009`."""

    id: int
    nombre: str
    precio_base: Decimal
    visitas_totales: int
    cupo_invitados: int
    duracion_dias: int

    model_config = {"from_attributes": True}

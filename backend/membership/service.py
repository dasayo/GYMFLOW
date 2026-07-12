"""
Servicio de membership.

Regla de módulos (no negociable, AGENTS.md): este service es el ÚNICO punto de
entrada que otros módulos pueden llamar para leer/mutar datos de membership.
Ningún otro módulo debe importar membership/repository.py directamente.
"""
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from core.config import now as _now
from membership.repository import MembershipRepository, MembershipTypeRepository
from membership.schemas import MembershipSummary, MembershipSummaryOut
from models import EstadoMembresia, Membership, MembershipType


class MembershipTypeNoEncontradoError(Exception):
    """El `tipo_id` pedido no existe (004: asignar/renovar)."""


class MembershipYaExisteError(Exception):
    """Asignar (primera vez) cuando el usuario ya tiene alguna Membership —
    debe usarse renovar en su lugar (004)."""


class MembershipNoExisteError(Exception):
    """Renovar cuando el usuario no tiene ninguna Membership previa — debe
    usarse asignar en su lugar (004)."""


def hoy() -> date:
    return _now().date()


def get_membership_for_user(user_id: int, db: Session) -> Membership | None:
    """Fila vigente (ventana de fechas + estado=activa) sin validar visitas —
    para que quien llame (ej. checkin.service, RN-01 inversa de 002) determine
    la razón exacta de por qué RN-01 no se cumple."""
    return MembershipRepository(db).get_active_by_user(user_id, hoy())


def get_active_membership(user_id: int, db: Session) -> Membership | None:
    """RN-01: membresía con estado activa, no vencida (hoy <= fecha_vencimiento)
    y con visitas_restantes > 0. No confía solo en `estado`, revalida la fecha."""
    membership = MembershipRepository(db).get_active_by_user(user_id, hoy())
    if membership is None:
        return None
    if membership.fecha_vencimiento < hoy():
        return None
    if membership.visitas_restantes <= 0:
        return None
    return membership


def list_membership_history(user_id: int, db: Session) -> list[Membership]:
    """Historial completo (004), más reciente primero."""
    return MembershipRepository(db).list_by_user(user_id)


def list_active_types(db: Session) -> list[MembershipType]:
    """Tipos disponibles para elegir al asignar/renovar (004)."""
    return MembershipTypeRepository(db).list_active()


def create_membership(
    user_id: int, tipo_id: int, monto: Decimal, nota: str | None, db: Session
) -> Membership:
    """Primera asignación (004): el usuario no debe tener ninguna Membership
    previa (ni vigente ni vencida) — si la tiene, es una renovación."""
    repo = MembershipRepository(db)
    if repo.get_latest_by_user(user_id) is not None:
        raise MembershipYaExisteError()
    tipo = MembershipTypeRepository(db).get_by_id(tipo_id)
    if tipo is None:
        raise MembershipTypeNoEncontradoError()

    inicio = hoy()
    membership = Membership(
        miembro_id=user_id,
        tipo_id=tipo_id,
        visitas_restantes=tipo.visitas_totales,
        cupo_invitados_restantes=tipo.cupo_invitados,
        fecha_inicio=inicio,
        fecha_vencimiento=inicio + timedelta(days=tipo.duracion_dias),
        estado=EstadoMembresia.activa,
        monto=monto,
        nota=nota,
    )
    return repo.create(membership)


def renew_membership(
    user_id: int, tipo_id: int, monto: Decimal, nota: str | None, db: Session
) -> Membership:
    """Renovación (004): crea una Membership nueva, no modifica la anterior.
    Si la anterior sigue vigente (no vencida), la nueva empieza el día
    siguiente a su vencimiento (no se pierden días pagados); si ya venció,
    empieza hoy. Permite upgrade/downgrade: `tipo_id` puede ser distinto al
    de la anterior."""
    repo = MembershipRepository(db)
    anterior = repo.get_latest_by_user(user_id)
    if anterior is None:
        raise MembershipNoExisteError()
    tipo = MembershipTypeRepository(db).get_by_id(tipo_id)
    if tipo is None:
        raise MembershipTypeNoEncontradoError()

    hoy_ = hoy()
    inicio = (
        anterior.fecha_vencimiento + timedelta(days=1)
        if anterior.fecha_vencimiento >= hoy_
        else hoy_
    )
    membership = Membership(
        miembro_id=user_id,
        tipo_id=tipo_id,
        visitas_restantes=tipo.visitas_totales,
        cupo_invitados_restantes=tipo.cupo_invitados,
        fecha_inicio=inicio,
        fecha_vencimiento=inicio + timedelta(days=tipo.duracion_dias),
        estado=EstadoMembresia.activa,
        monto=monto,
        nota=nota,
    )
    return repo.create(membership)


def consume_visit(membership_id: int, db: Session) -> Membership:
    """RN-08: descuenta exactamente 1 visita. `SELECT ... FOR UPDATE` serializa
    descuentos concurrentes (RNF ≥10 concurrencia, plan.md de 001). No hace
    commit — el orquestador (checkin.service) confirma la transacción completa."""
    membership = MembershipRepository(db).get_for_update(membership_id)
    membership.visitas_restantes -= 1
    return membership


def get_membership_summary(user_id: int, db: Session) -> MembershipSummary | None:
    """Mínimo del semáforo reutilizado por checkin (001) y resumen (007)."""
    membership = MembershipRepository(db).get_active_by_user(user_id, hoy())
    if membership is None:
        return None
    tipo = MembershipTypeRepository(db).get_by_id(membership.tipo_id)
    return MembershipSummary(
        tipo=tipo.nombre if tipo else "",
        visitas_restantes=membership.visitas_restantes,
        fecha_vencimiento=membership.fecha_vencimiento,
    )


def get_membership_summary_detail(user_id: int, db: Session) -> MembershipSummaryOut:
    """Resumen completo del portal (007, RF-04). Solo lectura: no descuenta
    visitas/cupos ni registra CheckIn. Nunca falla por falta de membresía —
    devuelve un DTO coherente con estado vencida/sin_plan (criterio del spec).
    Si hay una renovación futura ya pagada, manda la fila vigente HOY (la
    renovación se informará cuando empiece su ventana)."""
    repo = MembershipRepository(db)
    hoy_ = hoy()

    # get_active_by_user no filtra por fecha_vencimiento a propósito (checkin
    # la usa para distinguir la razón de RN-01) — aquí sí hay que revalidarla,
    # igual que hace get_active_membership.
    vigente = repo.get_active_by_user(user_id, hoy_)
    if vigente is not None and vigente.fecha_vencimiento < hoy_:
        vigente = None
    if vigente is not None:
        tipo = MembershipTypeRepository(db).get_by_id(vigente.tipo_id)
        return MembershipSummaryOut(
            estado="activa",
            tipo=tipo.nombre if tipo else None,
            fecha_vencimiento=vigente.fecha_vencimiento,
            visitas_restantes=vigente.visitas_restantes,
            cupo_invitados_restantes=vigente.cupo_invitados_restantes,
            dias_restantes=(vigente.fecha_vencimiento - hoy_).days,
        )

    ultima = repo.get_latest_by_user(user_id)
    if ultima is None:
        return MembershipSummaryOut(
            estado="sin_plan",
            tipo=None,
            fecha_vencimiento=None,
            visitas_restantes=None,
            cupo_invitados_restantes=None,
            dias_restantes=None,
        )

    tipo = MembershipTypeRepository(db).get_by_id(ultima.tipo_id)
    return MembershipSummaryOut(
        estado="vencida",
        tipo=tipo.nombre if tipo else None,
        fecha_vencimiento=ultima.fecha_vencimiento,
        visitas_restantes=ultima.visitas_restantes,
        cupo_invitados_restantes=ultima.cupo_invitados_restantes,
        dias_restantes=None,
    )

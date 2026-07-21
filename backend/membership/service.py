"""
Servicio de membership.

Regla de módulos del proyecto (no negociable): este service es el ÚNICO punto de
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
    """El ``tipo_id`` pedido no existe."""


class MembershipYaExisteError(Exception):
    """Se intentó asignar (primera vez) a un usuario que ya tiene alguna
    Membership — debe usarse renovar en su lugar."""


class MembershipNoExisteError(Exception):
    """Se intentó renovar a un usuario sin ninguna Membership previa — debe
    usarse asignar en su lugar."""


class MembershipTypeConMembresiaActivaError(Exception):
    """RN-05: no se puede desactivar un tipo con ≥1 Membership activa
    vinculada."""


class MembershipTypeConHistorialError(Exception):
    """No se puede eliminar físicamente un tipo que tiene cualquier
    Membership vinculada (activa o histórica) — solo desactivarlo."""


def hoy() -> date:
    """Fecha actual en la zona horaria del gimnasio."""
    return _now().date()


def get_membership_for_user(user_id: int, db: Session) -> Membership | None:
    """Fila vigente (ventana de fechas + ``estado=activa``) sin validar
    visitas — para que quien llame (p. ej. ``checkin.service``, HU-02)
    determine la razón exacta de por qué RN-01 no se cumple.

    Args:
        user_id: ID del socio.
        db: Sesión de base de datos activa.

    Returns:
        La Membership vigente, o ``None`` si no tiene ninguna.
    """
    return MembershipRepository(db).get_active_by_user(user_id, hoy())


def get_active_membership(user_id: int, db: Session) -> Membership | None:
    """Membresía que cumple RN-01: no vencida (``hoy <= fecha_vencimiento``)
    y con ``visitas_restantes > 0``. No confía solo en ``estado``, revalida
    la fecha.

    Args:
        user_id: ID del socio.
        db: Sesión de base de datos activa.

    Returns:
        La Membership activa, o ``None`` si no cumple RN-01.
    """
    membership = MembershipRepository(db).get_active_by_user(user_id, hoy())
    if membership is None:
        return None
    if membership.fecha_vencimiento < hoy():
        return None
    if membership.visitas_restantes <= 0:
        return None
    return membership


def list_membership_history(user_id: int, db: Session) -> list[Membership]:
    """Historial completo de Membership del socio, más reciente primero."""
    return MembershipRepository(db).list_by_user(user_id)


def list_active_types(db: Session) -> list[MembershipType]:
    """Tipos de membresía activos, disponibles para asignar/renovar."""
    return MembershipTypeRepository(db).list_active()


def list_all_types(db: Session) -> list[MembershipType]:
    """Catálogo completo (activos e inactivos) para el CRUD del
    Administrador (HU-08)."""
    return MembershipTypeRepository(db).list_all()


def get_type(tipo_id: int, db: Session) -> MembershipType:
    """Busca un tipo de membresía por ID.

    Raises:
        MembershipTypeNoEncontradoError: si ``tipo_id`` no existe.
    """
    tipo = MembershipTypeRepository(db).get_by_id(tipo_id)
    if tipo is None:
        raise MembershipTypeNoEncontradoError()
    return tipo


def create_type(
    nombre: str,
    precio_base: Decimal,
    visitas_totales: int,
    cupo_invitados: int,
    duracion_dias: int,
    activo: bool,
    db: Session,
) -> MembershipType:
    """Crea una plantilla de tipo de membresía (HU-08, RF-11).

    No hace commit — el router cierra la transacción.
    """
    tipo = MembershipType(
        nombre=nombre,
        precio_base=precio_base,
        visitas_totales=visitas_totales,
        cupo_invitados=cupo_invitados,
        duracion_dias=duracion_dias,
        activo=activo,
    )
    return MembershipTypeRepository(db).create(tipo)


def update_type(tipo_id: int, db: Session, **campos) -> MembershipType:
    """Edita los parámetros de un tipo de membresía (HU-08).

    RN-06: no toca las Membership ya creadas (sus saldos/fechas son
    snapshot). RN-05: desactivar (``activo=False``) se rechaza si el tipo
    tiene ≥1 Membership activa.

    Args:
        tipo_id: ID del tipo a editar.
        db: Sesión de base de datos activa.
        **campos: Campos a modificar.

    Raises:
        MembershipTypeNoEncontradoError: si ``tipo_id`` no existe.
        MembershipTypeConMembresiaActivaError: si se intenta desactivar un
            tipo con Membership activas vinculadas.
    """
    repo = MembershipTypeRepository(db)
    tipo = repo.get_by_id(tipo_id)
    if tipo is None:
        raise MembershipTypeNoEncontradoError()

    if (
        campos.get("activo") is False
        and tipo.activo
        and repo.count_active_memberships_by_type(tipo_id) > 0
    ):
        raise MembershipTypeConMembresiaActivaError()

    for campo, valor in campos.items():
        setattr(tipo, campo, valor)
    db.flush()
    return tipo


def delete_type(tipo_id: int, db: Session) -> None:
    """Borra físicamente un tipo de membresía (HU-08).

    Permitido solo si el tipo nunca tuvo ninguna Membership (ni activa ni
    histórica). Si tiene historial, la única opción es desactivarlo
    (preserva la trazabilidad de precios/planes).

    Raises:
        MembershipTypeNoEncontradoError: si ``tipo_id`` no existe.
        MembershipTypeConHistorialError: si el tipo tiene alguna Membership
            vinculada, activa o histórica.
    """
    repo = MembershipTypeRepository(db)
    tipo = repo.get_by_id(tipo_id)
    if tipo is None:
        raise MembershipTypeNoEncontradoError()
    if repo.count_any_memberships_by_type(tipo_id) > 0:
        raise MembershipTypeConHistorialError()
    repo.delete(tipo)


def get_type_names_by_user_ids(user_ids: list[int], db: Session) -> dict[int, str]:
    """Para cada usuario, el nombre del tipo de su Membership más reciente,
    en lote (evita N+1 al enriquecer el reporte de asistencias, HU-09).
    Punto de entrada del módulo dueño de ``membresias``/``tipos_membresia``
    para que ``reports`` no cruce esas tablas directamente.

    Se reporta el plan MÁS RECIENTE del socio, no el vigente en la fecha
    exacta de cada asistencia (snapshot pragmático).

    Args:
        user_ids: IDs de los socios a resolver.
        db: Sesión de base de datos activa.

    Returns:
        Diccionario ``{user_id: nombre_del_tipo}``.
    """
    repo = MembershipRepository(db)
    latest = repo.list_latest_by_user_ids(user_ids)
    type_repo = MembershipTypeRepository(db)
    nombres = type_repo.get_names_by_ids([m.tipo_id for m in latest.values()])
    return {
        user_id: nombres.get(m.tipo_id, "")
        for user_id, m in latest.items()
    }


def create_membership(
    user_id: int, tipo_id: int, monto: Decimal, nota: str | None, db: Session
) -> Membership:
    """Primera asignación de membresía a un socio (HU-07).

    El usuario no debe tener ninguna Membership previa (ni vigente ni
    vencida) — si la tiene, es una renovación.

    Args:
        user_id: ID del socio.
        tipo_id: ID del tipo de membresía a asignar.
        monto: Monto pagado (trazabilidad del pago en ventanilla).
        nota: Nota libre opcional.
        db: Sesión de base de datos activa.

    Raises:
        MembershipYaExisteError: si el usuario ya tiene alguna Membership.
        MembershipTypeNoEncontradoError: si ``tipo_id`` no existe.
    """
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
    """Renueva la membresía de un socio (HU-07): crea una Membership nueva,
    no modifica la anterior.

    Si la anterior sigue vigente (no vencida), la nueva empieza el día
    siguiente a su vencimiento (no se pierden días pagados); si ya venció,
    empieza hoy. Permite upgrade/downgrade: ``tipo_id`` puede ser distinto
    al de la anterior.

    Args:
        user_id: ID del socio.
        tipo_id: ID del tipo de membresía a asignar (puede diferir del
            anterior).
        monto: Monto pagado.
        nota: Nota libre opcional.
        db: Sesión de base de datos activa.

    Raises:
        MembershipNoExisteError: si el usuario no tiene ninguna Membership
            previa.
        MembershipTypeNoEncontradoError: si ``tipo_id`` no existe.
    """
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
    """Descuenta exactamente 1 visita (RN-08).

    ``SELECT ... FOR UPDATE`` serializa descuentos concurrentes (RNF de
    rendimiento: ≥10 check-ins simultáneos). No hace commit — el
    orquestador (``checkin.service``) confirma la transacción completa.

    Args:
        membership_id: ID de la Membership a descontar.
        db: Sesión de base de datos activa.

    Returns:
        La Membership con la visita ya descontada, sin comitear.
    """
    membership = MembershipRepository(db).get_for_update(membership_id)
    membership.visitas_restantes -= 1
    return membership


def get_membership_for_guest(titular_id: int, db: Session) -> Membership | None:
    """HU-05: membresía del titular que puede avalar a un invitado — activa, en
    ventana de fechas y NO vencida. A diferencia de `get_active_membership`,
    NO exige `visitas_restantes > 0`: el invitado descuenta `cupo_invitados`,
    no las visitas del titular (RN-04). El cupo se valida aparte para poder
    distinguir la razón de la denegación."""
    membership = MembershipRepository(db).get_active_by_user(titular_id, hoy())
    if membership is None or membership.fecha_vencimiento < hoy():
        return None
    return membership


def consume_guest_slot(membership_id: int, db: Session) -> Membership:
    """RN-09: descuenta exactamente 1 cupo de invitado. `SELECT ... FOR UPDATE`
    serializa descuentos concurrentes (evita descontar el mismo cupo dos veces).
    No hace commit — el orquestador (checkin.service) confirma la transacción."""
    membership = MembershipRepository(db).get_for_update(membership_id)
    membership.cupo_invitados_restantes -= 1
    return membership


def get_membership_summary(user_id: int, db: Session) -> MembershipSummary | None:
    """Resumen mínimo (tipo, visitas restantes, vencimiento) reutilizado por
    ``checkin`` (HU-01) y por el resumen del portal (HU-06)."""
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
    """Resumen completo de membresía para el dashboard del portal (HU-06,
    RF-04).

    Solo lectura: no descuenta visitas/cupos ni registra CheckIn. Nunca
    falla por falta de membresía — devuelve un DTO coherente con estado
    ``vencida``/``sin_plan``. Si hay una renovación futura ya pagada, manda
    la fila vigente HOY (la renovación se informará cuando empiece su
    ventana).

    Args:
        user_id: ID del socio.
        db: Sesión de base de datos activa.

    Returns:
        DTO con ``estado`` en ``{"activa", "vencida", "sin_plan"}`` y los
        campos correspondientes.
    """
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

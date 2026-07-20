"""
Servicio de checkin — orquesta el motor de validación de RN-01/RN-02/RN-03/
RN-08/RN-10 (spec/features/001-checkin-membresia-activa,
002-acceso-denegado). Resuelve al usuario vía members.service y valida/
descuenta la membresía vía membership.service; nunca consulta sus tablas
directamente (regla de módulos, AGENTS.md).

Regla de módulos (no negociable, AGENTS.md): este service es el ÚNICO punto de
entrada que otros módulos pueden llamar para leer/mutar datos de checkin.
Ningún otro módulo debe importar checkin/repository.py directamente.
"""
import re
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import membership.service as membership_service
import members.service as members_service
from checkin.repository import CheckinDeviceLockRepository, CheckinRepository
from checkin.schemas import AttendanceConsistencyOut, AttendancePointOut, CheckinResultado, RazonDenegacion
from core.config import now as _now, settings
from membership.schemas import MembershipSummary
from models import CheckIn, ResultadoCheckin

# spec.md de 002 (decisión provisional, no confirmada con equipo/profesora):
# solo dígitos, 5 a 15 caracteres — permisivo con cédulas de varios países.
_CEDULA_VALIDA = re.compile(r"^\d{5,15}$")


class UsuarioNoEncontradoError(Exception):
    """Cédula con formato válido pero sin usuario registrado. La cortesía de
    primer día (005) es un flujo de Staff, no del kiosko, así que por ahora
    esto se trata como error 404 en el router — no es una decisión de
    negocio, es un límite explícito de alcance de 001/002 (ver "Fuera de
    alcance" en sus spec.md). No cuenta para el bloqueo de dispositivo (RN-03):
    solo CEDULA_NO_ENCONTRADA (formato inválido) cuenta."""


def checkin_member(cedula: str, device_id: str, db: Session):
    """Devuelve (CheckinResultado, mensaje, nombre, visitas_restantes, razon)."""
    lock_repo = CheckinDeviceLockRepository(db)

    if not _CEDULA_VALIDA.match(cedula):
        lock_repo.register_failed_attempt(device_id, _now())
        db.commit()
        return _respuesta_denegada(
            RazonDenegacion.cedula_no_encontrada, "ACCESO DENEGADO. Cédula inválida.", None
        )

    user = members_service.get_user_by_cedula(cedula, db)
    if user is None:
        raise UsuarioNoEncontradoError(cedula)

    repo = CheckinRepository(db)
    hoy = membership_service.hoy()

    # Filtro 1: ya tiene un CheckIn is_active=true de hoy → éxito directo,
    # sin reevaluar RN-01 ni descontar visita (spec.md de 001, "Filtro 1").
    if repo.exists_successful_checkin_today(user.id, hoy):
        lock_repo.reset_attempts(device_id)
        db.commit()
        resumen = membership_service.get_membership_summary(user.id, db)
        return _respuesta_exitosa(user.nombre, resumen)

    # Filtro 2: RN-01 (membresía activa + visitas_restantes > 0).
    membresia_activa = membership_service.get_active_membership(user.id, db)
    if membresia_activa is None:
        razon, mensaje = _razon_rn01(user.id, db)
        # RN-10: la denegación no toca saldos, pero sí queda registrada.
        # No cuenta para el bloqueo (RN-03): son socios reales y conocidos,
        # no tanteo de cédulas (spec.md de 002).
        repo.insert(
            CheckIn(
                usuario_id=user.id,
                resultado=ResultadoCheckin.denegado,
                razon_denegacion=razon.value,
                is_active=False,
            )
        )
        db.commit()
        return _respuesta_denegada(razon, mensaje, user.nombre)

    # Transacción única (RN-10): descuenta la visita e inserta el CheckIn, o
    # revierte ambos si algo falla. El commit/rollback lo hace este orquestador.
    try:
        membership_service.consume_visit(membresia_activa.id, db)
        repo.insert(
            CheckIn(
                usuario_id=user.id,
                resultado=ResultadoCheckin.exitoso,
                is_active=True,
            )
        )
        lock_repo.reset_attempts(device_id)
        db.commit()
    except IntegrityError:
        # Condición de carrera: otro check-in concurrente del mismo socio ya
        # ganó el índice único parcial (usuario_id, día) para hoy — se resuelve
        # como Filtro 1 (éxito, sin volver a descontar), no como error.
        db.rollback()
        lock_repo.reset_attempts(device_id)
        db.commit()
        resumen = membership_service.get_membership_summary(user.id, db)
        return _respuesta_exitosa(user.nombre, resumen)
    except Exception:
        db.rollback()
        raise

    resumen = membership_service.get_membership_summary(user.id, db)
    return _respuesta_exitosa(user.nombre, resumen)


def first_day_courtesy(cedula: str, nombre: str, db: Session):
    """005: registra la cortesía de primer día de un prospecto. Es un flujo de
    Staff desde el backoffice (NO self-service en kiosko — decisión del equipo,
    ver spec.md de 005), por eso no toca el contador de bloqueo de dispositivo
    (RN-03). Devuelve la misma tupla que `checkin_member`:
    (CheckinResultado, mensaje, nombre, visitas_restantes, razon)."""
    user = members_service.get_user_by_cedula(cedula, db)
    repo = CheckinRepository(db)

    if user is not None:
        if user.cortesia_usada:
            # Segunda cortesía: denegada y registrada (rastro auditable, mismo
            # criterio que 002 para las denegaciones).
            razon = RazonDenegacion.cortesia_ya_utilizada
            repo.insert(
                CheckIn(
                    usuario_id=user.id,
                    resultado=ResultadoCheckin.denegado,
                    razon_denegacion=razon.value,
                    is_active=False,
                )
            )
            db.commit()
            return _respuesta_denegada(
                razon,
                "CORTESÍA YA UTILIZADA. Esta persona ya usó su primer día gratis "
                "— invítala a afiliarse.",
                user.nombre,
            )
        # La cédula existe pero nunca usó cortesía: es un usuario ya registrado
        # (socio/staff), no un prospecto nuevo. No se persiste CheckIn — no es
        # un intento de abuso, simplemente la cortesía no aplica.
        return _respuesta_denegada(
            RazonDenegacion.ya_registrado,
            "CÉDULA YA REGISTRADA. Esta persona ya tiene una cuenta — debe hacer "
            "check-in normal, no aplica cortesía.",
            user.nombre,
        )

    # Cédula nueva → transacción única (RN-10): crea el prospecto y el CheckIn
    # exitoso de cortesía juntos, o revierte ambos.
    try:
        prospecto = members_service.create_prospect(cedula, nombre, db)
        repo.insert(
            CheckIn(
                usuario_id=prospecto.id,
                resultado=ResultadoCheckin.exitoso,
                is_active=True,
            )
        )
        db.commit()
    except IntegrityError:
        # Carrera: otro registro ganó el índice único de `usuarios.cedula`
        # entre la comprobación y el insert. Ya no es un prospecto nuevo.
        db.rollback()
        return _respuesta_denegada(
            RazonDenegacion.ya_registrado,
            "CÉDULA YA REGISTRADA. Intenta de nuevo.",
            None,
        )
    except Exception:
        db.rollback()
        raise

    return _respuesta_cortesia(prospecto.nombre)


def checkin_guest(cedula_titular: str, cedula_invitado: str, nombre_invitado: str, db: Session):
    """006: el titular (presente en el kiosko) hace entrar a su invitado.
    Valida que el titular tenga membresía activa y cupo de invitados, descuenta
    exactamente 1 cupo (RN-09) y registra el CheckIn del invitado, todo en una
    transacción única (RN-10). SIN ventana temporal: la presencia del titular es
    siempre requerida (decisión del equipo — solo "Camino 2" del spec de 006).
    Devuelve la misma tupla que `checkin_member`."""
    titular = members_service.get_user_by_cedula(cedula_titular, db)
    if titular is None:
        return _respuesta_denegada(
            RazonDenegacion.titular_no_encontrado,
            "ACCESO DENEGADO. El socio titular no está registrado.",
            None,
        )

    # No se usa get_active_membership: exige visitas del titular, que el
    # invitado NO consume. El invitado descuenta cupo_invitados (RN-04).
    membresia = membership_service.get_membership_for_guest(titular.id, db)
    if membresia is None:
        return _respuesta_denegada(
            RazonDenegacion.titular_sin_membresia,
            f"ACCESO DENEGADO. El socio {titular.nombre} no tiene una membresía activa.",
            titular.nombre,
        )
    if membresia.cupo_invitados_restantes <= 0:
        return _respuesta_denegada(
            RazonDenegacion.sin_cupo_invitados,
            f"ACCESO DENEGADO. El socio {titular.nombre} no tiene cupos de invitado disponibles.",
            titular.nombre,
        )

    invitado = members_service.get_or_create_guest_user(cedula_invitado, nombre_invitado, db)
    repo = CheckinRepository(db)
    hoy = membership_service.hoy()

    # Filtro 1 (análogo a 001): si el invitado ya ingresó hoy, no se descuenta
    # otro cupo — reingreso idempotente del día.
    if repo.exists_successful_checkin_today(invitado.id, hoy):
        db.commit()
        return _respuesta_invitado_ya_ingreso(
            invitado.nombre, titular.nombre, membresia.cupo_invitados_restantes
        )

    # Transacción única (RN-10): descuenta el cupo e inserta el CheckIn, o
    # revierte ambos.
    try:
        membership_service.consume_guest_slot(membresia.id, db)
        repo.insert(
            CheckIn(
                usuario_id=invitado.id,
                titular_id=titular.id,
                resultado=ResultadoCheckin.exitoso,
                is_active=True,
            )
        )
        db.commit()
    except IntegrityError:
        # Carrera: el invitado consiguió otro CheckIn is_active hoy entre el
        # chequeo y el insert. Se revierte (no se descuenta doble cupo).
        db.rollback()
        actual = membership_service.get_membership_for_guest(titular.id, db)
        cupo = actual.cupo_invitados_restantes if actual else None
        return _respuesta_invitado_ya_ingreso(nombre_invitado, titular.nombre, cupo)
    except Exception:
        db.rollback()
        raise

    return _respuesta_invitado_exitoso(
        invitado.nombre, titular.nombre, membresia.cupo_invitados_restantes
    )


def get_attendance(fecha_inicio: date, fecha_fin: date, db: Session) -> list[CheckIn]:
    """010 (RF-12): asistencias (CheckIn `is_active=true`) en el rango dado,
    ambos extremos inclusive. Punto de entrada del módulo dueño de `checkins`
    para que `reports` construya el reporte sin cruzar esta tabla directamente
    (regla de módulos, AGENTS.md). Solo lectura: no toca la fuente inmutable
    (RF-05)."""
    return CheckinRepository(db).list_attendances_in_range(fecha_inicio, fecha_fin)


def get_member_attendance_consistency(
    user_id: int, db: Session, period: str = "semana"
) -> AttendanceConsistencyOut:
    """Devuelve una serie simple de asistencia para la vista del portal del
    socio, ya sea por semana o por mes."""
    periodo = period.lower()
    if periodo not in {"semana", "mes"}:
        periodo = "semana"

    dias = 7 if periodo == "semana" else 30
    fecha_fin = membership_service.hoy()
    fecha_inicio = fecha_fin - timedelta(days=dias - 1)

    registros = CheckinRepository(db).list_successful_by_user_in_range(
        user_id, fecha_inicio, fecha_fin
    )

    puntos = [
        {"fecha": fecha_inicio + timedelta(days=offset), "asistencias": 0}
        for offset in range(dias)
    ]

    for registro in registros:
        if registro.fecha_hora is None:
            continue
        dia_registro = _local_date(registro.fecha_hora)
        if not (fecha_inicio <= dia_registro <= fecha_fin):
            continue
        indice = (dia_registro - fecha_inicio).days
        if 0 <= indice < dias:
            puntos[indice]["asistencias"] += 1

    return AttendanceConsistencyOut(
        periodo=periodo,
        total=sum(punto["asistencias"] for punto in puntos),
        puntos=[
            AttendancePointOut(fecha=punto["fecha"], asistencias=punto["asistencias"])
            for punto in puntos
        ],
    )


def _razon_rn01(user_id: int, db: Session) -> tuple[RazonDenegacion, str]:
    """Distingue MEMBRESIA_VENCIDA de SIN_VISITAS cuando RN-01 no se cumple
    (spec.md de 002). Sin fila `activa` en absoluto se trata como vencida —
    no hay membresía vigente que mostrar."""
    membresia = membership_service.get_membership_for_user(user_id, db)
    if membresia is None or membresia.fecha_vencimiento < membership_service.hoy():
        fecha = membresia.fecha_vencimiento if membresia else None
        mensaje = (
            f"ACCESO DENEGADO. Tu membresía venció el {fecha}."
            if fecha
            else "ACCESO DENEGADO. No tienes una membresía activa."
        )
        return RazonDenegacion.membresia_vencida, mensaje
    return (
        RazonDenegacion.sin_visitas,
        "ACCESO DENEGADO. Alcanzaste el límite de visitas de tu ciclo actual.",
    )


def _respuesta_exitosa(nombre: str | None, resumen: MembershipSummary | None):
    visitas = resumen.visitas_restantes if resumen else None
    return (
        CheckinResultado.exitoso,
        f"ACCESO PERMITIDO. Bienvenido/a {nombre}. Visitas restantes: {visitas}.",
        nombre,
        visitas,
        None,
    )


def _local_date(fecha_hora: 'datetime') -> date:
    if fecha_hora.tzinfo is None:
        fecha_hora = fecha_hora.replace(tzinfo=ZoneInfo('UTC'))
    return fecha_hora.astimezone(ZoneInfo(settings.timezone)).date()


def _respuesta_cortesia(nombre: str | None):
    """005: éxito de cortesía. Sin visitas_restantes — un prospecto no tiene
    membresía, por eso el campo va en None (no es 0)."""
    return (
        CheckinResultado.exitoso,
        f"CORTESÍA CONCEDIDA. Bienvenido/a {nombre}. Primer día gratis "
        "registrado — invítalo a afiliarse.",
        nombre,
        None,
        None,
    )


def _respuesta_invitado_exitoso(nombre_invitado: str | None, nombre_titular: str | None, cupo: int):
    """006: éxito de invitado. `visitas_restantes` va en None (el invitado no
    tiene visitas propias); el cupo restante del titular va en el mensaje, con
    el formato objetivo de la Propuesta."""
    return (
        CheckinResultado.exitoso,
        f"ACCESO PERMITIDO. Bienvenido/a {nombre_invitado}. El socio "
        f"{nombre_titular} tiene ahora {cupo} invitaciones restantes.",
        nombre_invitado,
        None,
        None,
    )


def _respuesta_invitado_ya_ingreso(
    nombre_invitado: str | None, nombre_titular: str | None, cupo: int | None
):
    sufijo = (
        f" El socio {nombre_titular} tiene {cupo} invitaciones restantes."
        if cupo is not None
        else ""
    )
    return (
        CheckinResultado.exitoso,
        f"ACCESO PERMITIDO. {nombre_invitado} ya había ingresado hoy.{sufijo}",
        nombre_invitado,
        None,
        None,
    )


def _respuesta_denegada(razon: RazonDenegacion, mensaje: str, nombre: str | None):
    return (CheckinResultado.denegado, mensaje, nombre, None, razon)

"""
Tests de checkin/service.py contra los criterios de aceptación de
spec/features/001-checkin-membresia-activa/spec.md y
spec/features/002-acceso-denegado/spec.md.
"""
import threading
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy.orm import sessionmaker

from checkin.repository import CheckinDeviceLockRepository
from checkin.schemas import CheckinResultado, RazonDenegacion
from checkin.service import (
    checkin_guest,
    checkin_member,
    first_day_courtesy,
    get_member_attendance_consistency,
)
from core.config import now as _now, settings
from membership.service import hoy
from core.database import engine
from models import (
    CheckIn,
    CheckinDeviceLock,
    EstadoMembresia,
    EstadoUsuario,
    Membership,
    MembershipType,
    ResultadoCheckin,
    RolUsuario,
    User,
)

DEVICE = "kiosko-test-1"


def _crear_socio(db, visitas_restantes=5, dias_vencimiento=30):
    tipo = MembershipType(
        nombre="Mensual",
        precio_base=50000,
        visitas_totales=30,
        cupo_invitados=1,
        duracion_dias=30,
        activo=True,
    )
    db.add(tipo)
    db.flush()

    user = User(
        cedula="1000000001",
        nombre="Ana Pérez",
        rol=RolUsuario.miembro,
        estado=EstadoUsuario.activo,
    )
    db.add(user)
    db.flush()

    membership = Membership(
        miembro_id=user.id,
        tipo_id=tipo.id,
        visitas_restantes=visitas_restantes,
        cupo_invitados_restantes=tipo.cupo_invitados,
        # hoy() de Bogotá (el mismo reloj que usa el servicio), NO date.today():
        # en CI (UTC) difieren entre las 19:00 y medianoche de Bogotá y una
        # membresía "de hoy" quedaría con fecha_inicio en el futuro → denegada.
        fecha_inicio=hoy(),
        fecha_vencimiento=hoy() + timedelta(days=dias_vencimiento),
        estado=EstadoMembresia.activa,
        monto=tipo.precio_base,
    )
    db.add(membership)
    db.commit()
    return user, membership


def test_checkin_exitoso_descuenta_exactamente_una_visita(db):
    user, membership = _crear_socio(db, visitas_restantes=5)

    resultado, mensaje, nombre, visitas_restantes, razon = checkin_member(user.cedula, DEVICE, db)

    assert resultado == CheckinResultado.exitoso
    assert nombre == "Ana Pérez"
    assert visitas_restantes == 4
    assert razon is None
    assert "Ana Pérez" in mensaje

    db.refresh(membership)
    assert membership.visitas_restantes == 4


def test_constancia_usa_fecha_local_correcta_para_checkins_utc(db):
    user, _ = _crear_socio(db, visitas_restantes=5)
    local_hoy = hoy()
    local_time = datetime(local_hoy.year, local_hoy.month, local_hoy.day, 23, 0, tzinfo=ZoneInfo(settings.timezone))
    utc_time = local_time.astimezone(timezone.utc)

    db.add(
        CheckIn(
            usuario_id=user.id,
            fecha_hora=utc_time,
            resultado="exitoso",
            is_active=True,
        )
    )
    db.commit()

    constancia = get_member_attendance_consistency(user.id, db, period="semana")

    assert constancia.total == 1
    assert any(point.fecha == local_hoy and point.asistencias == 1 for point in constancia.puntos)


def test_segundo_checkin_mismo_dia_no_descuenta_de_nuevo(db):
    """Filtro 1: un reingreso el mismo día es exitoso pero no descuenta ni
    reevalúa RN-01, y no crea un segundo CheckIn is_active=true."""
    user, membership = _crear_socio(db, visitas_restantes=5)

    checkin_member(user.cedula, DEVICE, db)
    resultado, _, _, visitas_restantes, _ = checkin_member(user.cedula, DEVICE, db)

    assert resultado == CheckinResultado.exitoso
    assert visitas_restantes == 4

    db.refresh(membership)
    assert membership.visitas_restantes == 4

    activos = (
        db.query(CheckIn)
        .filter(CheckIn.usuario_id == user.id, CheckIn.is_active.is_(True))
        .all()
    )
    assert len(activos) == 1


def test_sin_visitas_restantes_deniega_con_razon_y_persiste_checkin(db):
    user, membership = _crear_socio(db, visitas_restantes=0)

    resultado, mensaje, _, visitas_restantes, razon = checkin_member(user.cedula, DEVICE, db)

    assert resultado == CheckinResultado.denegado
    assert razon == RazonDenegacion.sin_visitas
    assert "límite de visitas" in mensaje
    assert visitas_restantes is None

    db.refresh(membership)
    assert membership.visitas_restantes == 0
    assert db.query(CheckIn).filter(CheckIn.is_active.is_(True)).count() == 0

    denegado = db.query(CheckIn).filter(CheckIn.usuario_id == user.id).one()
    assert denegado.resultado.value == "denegado"
    assert denegado.razon_denegacion == RazonDenegacion.sin_visitas.value


def test_membresia_vencida_deniega_con_razon_y_persiste_checkin(db):
    user, membership = _crear_socio(db, visitas_restantes=5, dias_vencimiento=-1)

    resultado, mensaje, _, _, razon = checkin_member(user.cedula, DEVICE, db)

    assert resultado == CheckinResultado.denegado
    assert razon == RazonDenegacion.membresia_vencida
    assert str(membership.fecha_vencimiento) in mensaje
    db.refresh(membership)
    assert membership.visitas_restantes == 5

    denegado = db.query(CheckIn).filter(CheckIn.usuario_id == user.id).one()
    assert denegado.razon_denegacion == RazonDenegacion.membresia_vencida.value


def test_denegacion_por_membresia_no_cuenta_para_bloqueo_de_dispositivo(db):
    """spec.md de 002: MEMBRESIA_VENCIDA/SIN_VISITAS no cuentan para RN-03,
    a diferencia de CEDULA_NO_ENCONTRADA."""
    user, _ = _crear_socio(db, visitas_restantes=0)

    for _ in range(3):
        checkin_member(user.cedula, DEVICE, db)

    lock = db.query(CheckinDeviceLock).filter_by(device_id=DEVICE).first()
    assert lock is None or lock.bloqueado_hasta is None


def test_cedula_con_formato_invalido_deniega_sin_persistir_checkin(db):
    resultado, mensaje, _, _, razon = checkin_member("abc", DEVICE, db)

    assert resultado == CheckinResultado.denegado
    assert razon == RazonDenegacion.cedula_no_encontrada
    assert "inválida" in mensaje
    assert db.query(CheckIn).count() == 0


def test_tres_fallos_de_cedula_invalida_bloquean_el_dispositivo(db):
    for _ in range(3):
        resultado, _, _, _, razon = checkin_member("xx", DEVICE, db)
        assert resultado == CheckinResultado.denegado
        assert razon == RazonDenegacion.cedula_no_encontrada

    lock_repo = CheckinDeviceLockRepository(db)
    assert lock_repo.is_locked(DEVICE, _now())


def test_listar_bloqueados_muestra_el_device_id_para_desbloquear(db):
    """Sin panel de staff todavía, esto es la única forma de saber qué
    device_id pasarle al endpoint de desbloqueo manual."""
    for _ in range(3):
        checkin_member("xx", DEVICE, db)

    bloqueados = CheckinDeviceLockRepository(db).listar_bloqueados(_now())

    assert len(bloqueados) == 1
    assert bloqueados[0].device_id == DEVICE
    assert bloqueados[0].intentos_fallidos == 3


def test_checkin_exitoso_resetea_contador_de_fallos(db):
    user, _ = _crear_socio(db, visitas_restantes=5)

    for _ in range(2):
        checkin_member("xx", DEVICE, db)

    checkin_member(user.cedula, DEVICE, db)

    lock = db.query(CheckinDeviceLock).filter_by(device_id=DEVICE).one()
    assert lock.intentos_fallidos == 0
    assert lock.bloqueado_hasta is None


def test_ventana_de_cinco_minutos_expira_el_conteo(db):
    lock_repo = CheckinDeviceLockRepository(db)
    momento_viejo = _now() - timedelta(minutes=10)
    lock_repo.register_failed_attempt(DEVICE, momento_viejo)
    lock_repo.register_failed_attempt(DEVICE, momento_viejo + timedelta(seconds=1))
    db.commit()

    # Un tercer fallo, pero fuera de la ventana de 5 min del primero:
    # el conteo se reinicia en vez de sumar (no debe bloquear).
    checkin_member("xx", DEVICE, db)

    assert not lock_repo.is_locked(DEVICE, _now())


def test_rollback_no_descuenta_si_falla_a_mitad_de_transaccion(db, monkeypatch):
    """RN-10: un fallo entre el descuento y el insert no deja la visita
    descontada sin su CheckIn correspondiente."""
    user, membership = _crear_socio(db, visitas_restantes=5)

    def _insert_roto(self, checkin):
        raise RuntimeError("fallo simulado a mitad de la transacción")

    monkeypatch.setattr("checkin.repository.CheckinRepository.insert", _insert_roto)

    with pytest.raises(RuntimeError):
        checkin_member(user.cedula, DEVICE, db)

    db.rollback()
    db.refresh(membership)
    assert membership.visitas_restantes == 5
    assert db.query(CheckIn).count() == 0


def test_diez_checkins_concurrentes_no_descuentan_de_mas(db):
    """RNF concurrencia: ≥10 check-ins simultáneos del mismo socio el mismo
    día descuentan exactamente 1 visita en total (índice único parcial +
    SELECT ... FOR UPDATE)."""
    user, membership = _crear_socio(db, visitas_restantes=5)
    membership_id = membership.id
    cedula = user.cedula

    resultados: list[CheckinResultado] = []
    lock = threading.Lock()

    def _worker():
        Session = sessionmaker(bind=engine)
        session = Session()
        try:
            resultado, *_ = checkin_member(cedula, DEVICE, session)
            with lock:
                resultados.append(resultado)
        finally:
            session.close()

    hilos = [threading.Thread(target=_worker) for _ in range(10)]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join()

    assert len(resultados) == 10
    assert all(r == CheckinResultado.exitoso for r in resultados)

    db.expire_all()
    membership_final = db.get(Membership, membership_id)
    assert membership_final.visitas_restantes == 4

    activos = (
        db.query(CheckIn)
        .filter(CheckIn.usuario_id == user.id, CheckIn.is_active.is_(True))
        .count()
    )
    assert activos == 1


# --- 005: cortesía de primer día (flujo de Staff) ---


def test_cortesia_crea_prospecto_y_checkin_exitoso(db):
    """Criterio 1: cédula no registrada → User Prospecto + CheckIn Exitoso."""
    resultado, mensaje, nombre, visitas, razon = first_day_courtesy("900111222", "Nuevo Prospecto", db)

    assert resultado == CheckinResultado.exitoso
    assert razon is None
    assert nombre == "Nuevo Prospecto"

    prospecto = db.query(User).filter(User.cedula == "900111222").one()
    assert prospecto.rol == RolUsuario.invitado
    assert prospecto.cortesia_usada is True
    assert prospecto.estado == EstadoUsuario.activo

    checkins = db.query(CheckIn).filter(CheckIn.usuario_id == prospecto.id).all()
    assert len(checkins) == 1
    assert checkins[0].resultado == ResultadoCheckin.exitoso
    assert checkins[0].is_active is True


def test_cortesia_es_atomica_prospecto_y_checkin_juntos(db):
    """RN-10: tras la cortesía existen el prospecto Y su CheckIn, ambos
    commiteados en la misma transacción (verificado desde otra sesión)."""
    first_day_courtesy("900111333", "Atómico", db)

    Session = sessionmaker(bind=engine)
    otra = Session()
    try:
        prospecto = otra.query(User).filter(User.cedula == "900111333").one()
        assert otra.query(CheckIn).filter(CheckIn.usuario_id == prospecto.id).count() == 1
    finally:
        otra.close()


def test_cortesia_segundo_intento_denegado_y_registrado(db):
    """Criterio 3: una cédula que YA usó cortesía → denegado + CheckIn de
    denegación con motivo CORTESIA_YA_UTILIZADA, sin crear otro usuario."""
    first_day_courtesy("900111444", "Repite", db)
    resultado, mensaje, nombre, visitas, razon = first_day_courtesy("900111444", "Repite", db)

    assert resultado == CheckinResultado.denegado
    assert razon == RazonDenegacion.cortesia_ya_utilizada

    # Sigue existiendo un solo usuario con esa cédula.
    assert db.query(User).filter(User.cedula == "900111444").count() == 1
    prospecto = db.query(User).filter(User.cedula == "900111444").one()
    resultados = [c.resultado for c in db.query(CheckIn).filter(CheckIn.usuario_id == prospecto.id).all()]
    assert resultados.count(ResultadoCheckin.exitoso) == 1
    assert resultados.count(ResultadoCheckin.denegado) == 1


def test_cortesia_a_usuario_ya_registrado_denegada_sin_checkin(db):
    """Un socio real (registrado, sin cortesía usada) no es un prospecto: la
    cortesía no aplica y no se persiste ningún CheckIn."""
    socio, _ = _crear_socio(db)  # cédula 1000000001, rol miembro
    resultado, mensaje, nombre, visitas, razon = first_day_courtesy(socio.cedula, "X", db)

    assert resultado == CheckinResultado.denegado
    assert razon == RazonDenegacion.ya_registrado
    assert db.query(CheckIn).filter(CheckIn.usuario_id == socio.id).count() == 0


def test_cortesia_no_descuenta_ni_crea_membresia(db):
    """El prospecto no tiene membresía; la cortesía no toca visitas."""
    first_day_courtesy("900111555", "Sin Membresía", db)
    prospecto = db.query(User).filter(User.cedula == "900111555").one()
    assert db.query(Membership).filter(Membership.miembro_id == prospecto.id).count() == 0


# --- 006: check-in de invitado (titular presente, sin ventana) ---


def _set_cupo(db, membership, cupo):
    membership.cupo_invitados_restantes = cupo
    db.commit()


def test_checkin_guest_exitoso_descuenta_un_cupo(db):
    """Criterio 1: titular con cupo → invitado Exitoso, se descuenta 1 cupo y
    se registra CheckIn(usuario_id=invitado, titular_id=titular)."""
    titular, membership = _crear_socio(db)
    _set_cupo(db, membership, 2)

    resultado, mensaje, nombre, visitas, razon = checkin_guest(
        titular.cedula, "700000001", "Invitada Uno", db
    )

    assert resultado == CheckinResultado.exitoso
    assert razon is None
    assert nombre == "Invitada Uno"
    assert "1 invitaciones restantes" in mensaje  # 2 - 1 = 1

    db.refresh(membership)
    assert membership.cupo_invitados_restantes == 1

    invitado = db.query(User).filter(User.cedula == "700000001").one()
    assert invitado.rol == RolUsuario.invitado
    checkin = db.query(CheckIn).filter(CheckIn.usuario_id == invitado.id).one()
    assert checkin.resultado == ResultadoCheckin.exitoso
    assert checkin.titular_id == titular.id
    assert checkin.is_active is True


def test_checkin_guest_atomico(db):
    """RN-10: descuento del cupo y CheckIn commiteados juntos (verificado desde
    otra sesión)."""
    titular, membership = _crear_socio(db)
    _set_cupo(db, membership, 1)

    checkin_guest(titular.cedula, "700000002", "Invitada Dos", db)

    Session = sessionmaker(bind=engine)
    otra = Session()
    try:
        m = otra.query(Membership).filter(Membership.id == membership.id).one()
        assert m.cupo_invitados_restantes == 0
        invitado = otra.query(User).filter(User.cedula == "700000002").one()
        assert otra.query(CheckIn).filter(CheckIn.usuario_id == invitado.id).count() == 1
    finally:
        otra.close()


def test_checkin_guest_sin_cupo_denegado_sin_descontar(db):
    """Criterio 5: cupo_invitados_restantes = 0 → Denegado, sin tocar nada."""
    titular, membership = _crear_socio(db)
    _set_cupo(db, membership, 0)

    resultado, mensaje, nombre, visitas, razon = checkin_guest(
        titular.cedula, "700000003", "Invitada Tres", db
    )

    assert resultado == CheckinResultado.denegado
    assert razon == RazonDenegacion.sin_cupo_invitados
    db.refresh(membership)
    assert membership.cupo_invitados_restantes == 0
    assert db.query(User).filter(User.cedula == "700000003").count() == 0
    assert db.query(CheckIn).count() == 0


def test_checkin_guest_titular_vencido_denegado(db):
    """Criterio 5: titular con membresía vencida → Denegado."""
    titular, membership = _crear_socio(db, dias_vencimiento=-1)
    _set_cupo(db, membership, 5)

    resultado, mensaje, nombre, visitas, razon = checkin_guest(
        titular.cedula, "700000004", "Invitada Cuatro", db
    )

    assert resultado == CheckinResultado.denegado
    assert razon == RazonDenegacion.titular_sin_membresia
    db.refresh(membership)
    assert membership.cupo_invitados_restantes == 5


def test_checkin_guest_titular_no_encontrado(db):
    resultado, mensaje, nombre, visitas, razon = checkin_guest(
        "999888777", "700000005", "Invitada Cinco", db
    )
    assert resultado == CheckinResultado.denegado
    assert razon == RazonDenegacion.titular_no_encontrado


def test_checkin_guest_titular_sin_visitas_pero_con_cupo_ok(db):
    """El invitado descuenta cupo_invitados, NO las visitas del titular: un
    titular con 0 visitas propias pero con cupo SÍ puede avalar un invitado."""
    titular, membership = _crear_socio(db, visitas_restantes=0)
    _set_cupo(db, membership, 1)

    resultado, mensaje, nombre, visitas, razon = checkin_guest(
        titular.cedula, "700000006", "Invitada Seis", db
    )

    assert resultado == CheckinResultado.exitoso
    db.refresh(membership)
    assert membership.cupo_invitados_restantes == 0
    assert membership.visitas_restantes == 0  # intactas


def test_checkin_guest_reingreso_mismo_dia_no_descuenta_doble(db):
    """El mismo invitado dos veces el mismo día → segundo es éxito idempotente
    sin volver a descontar cupo (análogo al Filtro 1 de 001)."""
    titular, membership = _crear_socio(db)
    _set_cupo(db, membership, 2)

    checkin_guest(titular.cedula, "700000007", "Invitada Siete", db)
    resultado, mensaje, _, _, _ = checkin_guest(titular.cedula, "700000007", "Invitada Siete", db)

    assert resultado == CheckinResultado.exitoso
    assert "ya había ingresado hoy" in mensaje
    db.refresh(membership)
    assert membership.cupo_invitados_restantes == 1  # descontado solo una vez

    invitado = db.query(User).filter(User.cedula == "700000007").one()
    activos = db.query(CheckIn).filter(
        CheckIn.usuario_id == invitado.id, CheckIn.is_active.is_(True)
    ).all()
    assert len(activos) == 1

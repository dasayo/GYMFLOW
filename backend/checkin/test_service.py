"""
Tests de checkin/service.py contra los criterios de aceptación de
spec/features/001-checkin-membresia-activa/spec.md y
spec/features/002-acceso-denegado/spec.md.
"""
import threading
from datetime import timedelta

import pytest
from sqlalchemy.orm import sessionmaker

from checkin.repository import CheckinDeviceLockRepository
from checkin.schemas import CheckinResultado, RazonDenegacion
from checkin.service import checkin_member
from core.config import now as _now
from membership.service import hoy
from core.database import engine
from models import (
    CheckIn,
    CheckinDeviceLock,
    EstadoMembresia,
    EstadoUsuario,
    Membership,
    MembershipType,
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

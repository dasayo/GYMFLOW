"""
Tests de membership/service.py contra los criterios de aceptación de
spec/features/004-gestion-usuarios/spec.md (asignación y renovación).
"""
from datetime import timedelta
from decimal import Decimal

import pytest

from membership.service import (
    MembershipNoExisteError,
    hoy,
    MembershipTypeNoEncontradoError,
    MembershipYaExisteError,
    create_membership,
    get_active_membership,
    list_active_types,
    list_membership_history,
    renew_membership,
)
from models import EstadoUsuario, MembershipType, RolUsuario, User


def _crear_tipo(db, **overrides) -> MembershipType:
    defaults = dict(
        nombre="Mensual", precio_base=Decimal("50000"), visitas_totales=30,
        cupo_invitados=1, duracion_dias=30, activo=True,
    )
    defaults.update(overrides)
    tipo = MembershipType(**defaults)
    db.add(tipo)
    db.flush()
    return tipo


def _crear_socio(db) -> User:
    user = User(
        cedula="1000000001", nombre="Ana Pérez", rol=RolUsuario.miembro,
        estado=EstadoUsuario.activo,
    )
    db.add(user)
    db.flush()
    return user


def test_create_membership_primera_asignacion(db):
    tipo = _crear_tipo(db)
    socio = _crear_socio(db)

    membership = create_membership(socio.id, tipo.id, Decimal("50000"), "efectivo", db)
    db.commit()

    assert membership.visitas_restantes == tipo.visitas_totales
    assert membership.cupo_invitados_restantes == tipo.cupo_invitados
    assert membership.fecha_inicio == hoy()
    assert membership.fecha_vencimiento == hoy() + timedelta(days=tipo.duracion_dias)
    assert membership.monto == Decimal("50000")
    assert membership.nota == "efectivo"


def test_create_membership_falla_si_ya_tiene_una(db):
    tipo = _crear_tipo(db)
    socio = _crear_socio(db)
    create_membership(socio.id, tipo.id, Decimal("50000"), None, db)
    db.commit()

    with pytest.raises(MembershipYaExisteError):
        create_membership(socio.id, tipo.id, Decimal("50000"), None, db)


def test_create_membership_tipo_inexistente(db):
    socio = _crear_socio(db)
    with pytest.raises(MembershipTypeNoEncontradoError):
        create_membership(socio.id, 9999, Decimal("50000"), None, db)


def test_renew_membership_falla_si_no_tiene_ninguna(db):
    tipo = _crear_tipo(db)
    socio = _crear_socio(db)
    with pytest.raises(MembershipNoExisteError):
        renew_membership(socio.id, tipo.id, Decimal("50000"), None, db)


def test_renew_membership_anterior_vencida_empieza_hoy(db):
    tipo = _crear_tipo(db)
    socio = _crear_socio(db)
    anterior = create_membership(socio.id, tipo.id, Decimal("50000"), None, db)
    # Simula que ya venció (ej. el socio renueva tarde).
    anterior.fecha_vencimiento = hoy() - timedelta(days=5)
    db.commit()

    nueva = renew_membership(socio.id, tipo.id, Decimal("50000"), None, db)
    db.commit()

    assert nueva.fecha_inicio == hoy()
    assert nueva.fecha_vencimiento == hoy() + timedelta(days=tipo.duracion_dias)
    assert anterior.fecha_vencimiento == hoy() - timedelta(days=5)  # no se modifica


def test_renew_membership_anticipada_empieza_al_vencer_la_anterior(db):
    tipo = _crear_tipo(db)
    socio = _crear_socio(db)
    anterior = create_membership(socio.id, tipo.id, Decimal("50000"), None, db)
    db.commit()
    vencimiento_anterior = anterior.fecha_vencimiento

    nueva = renew_membership(socio.id, tipo.id, Decimal("50000"), None, db)
    db.commit()

    assert nueva.fecha_inicio == vencimiento_anterior + timedelta(days=1)
    assert nueva.fecha_vencimiento == nueva.fecha_inicio + timedelta(days=tipo.duracion_dias)


def test_renew_membership_permite_upgrade_downgrade(db):
    tipo_basico = _crear_tipo(db, nombre="Básico", visitas_totales=10)
    tipo_premium = _crear_tipo(db, nombre="Premium", visitas_totales=100)
    socio = _crear_socio(db)
    create_membership(socio.id, tipo_basico.id, Decimal("30000"), None, db)
    db.commit()

    nueva = renew_membership(socio.id, tipo_premium.id, Decimal("90000"), None, db)
    db.commit()

    assert nueva.tipo_id == tipo_premium.id
    assert nueva.visitas_restantes == 100


def test_renovacion_anticipada_no_deja_doble_activa_para_el_motor_de_checkin(db):
    """Hallazgo de plan.md de 004: si la anterior sigue "vigente" (fecha_inicio
    <= hoy <= fecha_vencimiento) y la nueva empieza en el futuro,
    get_active_membership debe seguir devolviendo LA ANTERIOR (la que
    realmente está en ventana hoy), no la nueva fila futura."""
    tipo = _crear_tipo(db)
    socio = _crear_socio(db)
    anterior = create_membership(socio.id, tipo.id, Decimal("50000"), None, db)
    db.commit()

    renew_membership(socio.id, tipo.id, Decimal("50000"), None, db)
    db.commit()

    activa = get_active_membership(socio.id, db)
    assert activa is not None
    assert activa.id == anterior.id


def test_list_active_types_excluye_inactivos(db):
    _crear_tipo(db, nombre="Activo")
    _crear_tipo(db, nombre="Inactivo", activo=False)

    tipos = list_active_types(db)

    assert [t.nombre for t in tipos] == ["Activo"]


def test_list_membership_history_orden_mas_reciente_primero(db):
    tipo = _crear_tipo(db)
    socio = _crear_socio(db)
    primera = create_membership(socio.id, tipo.id, Decimal("50000"), None, db)
    db.commit()
    primera.fecha_vencimiento = hoy() - timedelta(days=1)
    db.commit()
    segunda = renew_membership(socio.id, tipo.id, Decimal("50000"), None, db)
    db.commit()

    historial = list_membership_history(socio.id, db)

    assert [m.id for m in historial] == [segunda.id, primera.id]

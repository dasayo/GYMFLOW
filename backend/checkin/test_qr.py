"""
Tests de checkin/service.py para 012-checkin-qr-dinamico: nonce del QR
(generación, expiración, un solo uso) y la lista blanca de dispositivos.
"""
from datetime import timedelta

import pytest

from checkin.conftest import autorizar_dispositivo
from checkin.schemas import CheckinResultado
from checkin.service import (
    NonceInvalidoError,
    autorizar_dispositivo as autorizar_dispositivo_service,
    checkin_member_qr,
    checkin_via_qr,
    dispositivo_autorizado,
    generar_qr_nonce,
    listar_dispositivos_autorizados,
    revocar_dispositivo,
)
from checkin.test_service import _crear_socio
from core.config import now as _now
from members.service import UsuarioNoEncontradoError

DEVICE = "kiosko-qr-test"


def test_generar_qr_nonce_persiste_y_expira_segun_config(db, monkeypatch):
    monkeypatch.setattr("checkin.service.settings.qr_nonce_seconds", 30)
    fila = generar_qr_nonce(DEVICE, db)

    assert fila.device_id == DEVICE
    assert fila.usado_en is None
    assert fila.expira_en - fila.creado_en == timedelta(seconds=30)


def test_checkin_member_qr_exitoso_descuenta_visita(db):
    user, membership = _crear_socio(db, visitas_restantes=5)

    resultado, mensaje, nombre, visitas_restantes, razon = checkin_member_qr(user.id, DEVICE, db)

    assert resultado == CheckinResultado.exitoso
    assert nombre == "Ana Pérez"
    assert visitas_restantes == 4
    assert razon is None

    db.refresh(membership)
    assert membership.visitas_restantes == 4


def test_checkin_member_qr_usuario_inexistente_lanza_error(db):
    with pytest.raises(UsuarioNoEncontradoError):
        checkin_member_qr(999999, DEVICE, db)


def test_checkin_via_qr_consume_nonce_vigente(db):
    user, _ = _crear_socio(db, visitas_restantes=5)
    fila = generar_qr_nonce(DEVICE, db)

    resultado, *_ = checkin_via_qr(user.id, DEVICE, fila.nonce, db)

    assert resultado == CheckinResultado.exitoso
    db.refresh(fila)
    assert fila.usado_en is not None


def test_checkin_via_qr_nonce_ya_usado_lanza_error(db):
    user, _ = _crear_socio(db, visitas_restantes=5)
    fila = generar_qr_nonce(DEVICE, db)
    checkin_via_qr(user.id, DEVICE, fila.nonce, db)

    with pytest.raises(NonceInvalidoError):
        checkin_via_qr(user.id, DEVICE, fila.nonce, db)


def test_checkin_via_qr_nonce_expirado_lanza_error(db):
    user, _ = _crear_socio(db, visitas_restantes=5)
    fila = generar_qr_nonce(DEVICE, db)
    fila.expira_en = _now() - timedelta(seconds=1)
    db.commit()

    with pytest.raises(NonceInvalidoError):
        checkin_via_qr(user.id, DEVICE, fila.nonce, db)


def test_checkin_via_qr_nonce_de_otro_dispositivo_lanza_error(db):
    user, _ = _crear_socio(db, visitas_restantes=5)
    fila = generar_qr_nonce(DEVICE, db)

    with pytest.raises(NonceInvalidoError):
        checkin_via_qr(user.id, "otro-kiosko", fila.nonce, db)


def test_checkin_via_qr_nonce_inexistente_lanza_error(db):
    user, _ = _crear_socio(db, visitas_restantes=5)

    with pytest.raises(NonceInvalidoError):
        checkin_via_qr(user.id, DEVICE, "nonce-que-no-existe", db)


def test_dispositivo_autorizado_lista_blanca(db):
    assert dispositivo_autorizado(DEVICE, db) is False

    autorizar_dispositivo(db, DEVICE)
    assert dispositivo_autorizado(DEVICE, db) is True


def test_revocar_dispositivo_lo_quita_de_la_lista(db):
    autorizar_dispositivo(db, DEVICE)
    assert dispositivo_autorizado(DEVICE, db) is True

    revocar_dispositivo(DEVICE, db)
    assert dispositivo_autorizado(DEVICE, db) is False


def test_autorizar_dispositivo_dos_veces_actualiza_no_duplica(db):
    admin, _ = _crear_socio(db)  # cualquier usuario sirve como autorizado_por_id
    autorizar_dispositivo_service(DEVICE, "Tablet 1", admin.id, db)
    autorizar_dispositivo_service(DEVICE, "Tablet 1 renombrada", admin.id, db)

    dispositivos = listar_dispositivos_autorizados(db)
    assert len([d for d in dispositivos if d.device_id == DEVICE]) == 1
    assert next(d for d in dispositivos if d.device_id == DEVICE).etiqueta == "Tablet 1 renombrada"

"""
Tests de auth/service.py contra los criterios de aceptación de
spec/features/003-autenticacion-segura/spec.md.
"""
import pytest

from auth.conftest import PASSWORD, otorgar_permiso
from auth.service import CredencialesInvalidasError, get_user_permissions, login
from core.security import decode_access_token, hash_password
from models import EstadoUsuario, RolUsuario, User


def test_login_credenciales_validas_retorna_token_con_rol_y_exp(db, empleado):
    token, rol = login(empleado.email, PASSWORD, db)

    assert rol == RolUsuario.empleado
    payload = decode_access_token(token)
    assert payload["rol"] == RolUsuario.empleado.value
    assert payload["sub"] == str(empleado.id)
    assert "exp" in payload


def test_login_password_incorrecta_lanza_credenciales_invalidas(db, empleado):
    with pytest.raises(CredencialesInvalidasError):
        login(empleado.email, "otra-clave", db)


def test_login_email_inexistente_lanza_credenciales_invalidas(db):
    with pytest.raises(CredencialesInvalidasError):
        login("no-existe@gymflow.test", PASSWORD, db)


def test_login_rol_miembro_no_puede_loguearse(db):
    miembro = User(
        nombre="Socio Test",
        email="socio@gymflow.test",
        rol=RolUsuario.miembro,
        estado=EstadoUsuario.activo,
        password_hash=hash_password(PASSWORD),
    )
    db.add(miembro)
    db.commit()

    with pytest.raises(CredencialesInvalidasError):
        login(miembro.email, PASSWORD, db)


def test_login_usuario_inactivo_no_puede_loguearse(db, empleado_inactivo):
    with pytest.raises(CredencialesInvalidasError):
        login(empleado_inactivo.email, PASSWORD, db)


def test_password_se_almacena_hasheada(db, empleado):
    assert empleado.password_hash != PASSWORD
    assert empleado.password_hash.startswith("$2b$")


def test_get_user_permissions_devuelve_permisos_otorgados(db, empleado):
    assert get_user_permissions(empleado.id, db) == set()

    otorgar_permiso(db, empleado.id, "checkin.desbloquear_dispositivo")

    assert get_user_permissions(empleado.id, db) == {"checkin.desbloquear_dispositivo"}

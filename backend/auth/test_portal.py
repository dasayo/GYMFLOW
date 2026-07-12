"""
Tests HTTP de la sesión del Miembro en el portal (011): login, refresh con
rotación, activación de cuenta y logout — contra los criterios de aceptación
de spec/features/011-portal-miembro-autenticacion/spec.md.
"""
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from auth.conftest import PASSWORD, _crear_staff
from auth.service import _hash_refresh_token
from core.config import now
from core.security import decode_access_token, hash_password
from main import app
from models import EstadoUsuario, RefreshToken, RolUsuario, User

COOKIE = "gymflow_refresh"


def _client() -> TestClient:
    """Cliente nuevo por test: TestClient persiste cookies entre requests y
    un cliente compartido a nivel de módulo contaminaría los casos de rotación."""
    return TestClient(app)


def _crear_miembro(db, cedula="100200300", email="socio@gymflow.test", password=PASSWORD):
    user = User(
        cedula=cedula,
        nombre="Socio Test",
        email=email,
        rol=RolUsuario.miembro,
        estado=EstadoUsuario.activo,
        password_hash=hash_password(password) if password else None,
    )
    db.add(user)
    db.commit()
    return user


@pytest.fixture
def miembro(db):
    return _crear_miembro(db)


@pytest.fixture
def miembro_sin_password(db):
    return _crear_miembro(db, cedula="400500600", email="nuevo@gymflow.test", password=None)


def _login(client, email, password=PASSWORD):
    return client.post("/auth/portal/login", json={"email": email, "password": password})


# --- Login ---


def test_login_miembro_ok_devuelve_access_token_y_cookie_httponly(db, miembro):
    resp = _login(_client(), miembro.email)

    assert resp.status_code == 200
    body = resp.json()
    payload = decode_access_token(body["access_token"])
    assert payload["kind"] == "member"
    assert payload["sub"] == str(miembro.id)
    assert body["nombre"] == "Socio Test"
    set_cookie = resp.headers["set-cookie"]
    assert COOKIE in set_cookie
    assert "HttpOnly" in set_cookie


def test_login_credenciales_invalidas_mensaje_generico(db, miembro):
    client = _client()
    resp_password = _login(client, miembro.email, "incorrecta")
    resp_email = _login(client, "no-existe@gymflow.test")

    assert resp_password.status_code == resp_email.status_code == 401
    assert resp_password.json() == resp_email.json()


def test_login_portal_rechaza_staff_e_inactivos(db):
    staff = _crear_staff(db, RolUsuario.empleado, "empleado-portal@gymflow.test")
    inactivo = _crear_miembro(db, cedula="700800900", email="inactivo@gymflow.test")
    inactivo.estado = EstadoUsuario.inactivo
    db.commit()

    assert _login(_client(), staff.email).status_code == 401
    assert _login(_client(), inactivo.email).status_code == 401


# --- Refresh con rotación (ventana deslizante de 7 días) ---


def test_refresh_rota_el_token_y_el_viejo_deja_de_servir(db, miembro):
    client = _client()
    login = _login(client, miembro.email)
    cookie_original = login.cookies[COOKIE]

    primer_refresh = client.post("/auth/portal/refresh")
    assert primer_refresh.status_code == 200
    assert decode_access_token(primer_refresh.json()["access_token"])["kind"] == "member"
    assert primer_refresh.cookies[COOKIE] != cookie_original

    # Reusar el refresh token ya rotado (robado/duplicado) → sesión inválida.
    reuso = _client().post("/auth/portal/refresh", cookies={COOKIE: cookie_original})
    assert reuso.status_code == 401


def test_refresh_sin_cookie_o_expirado_401(db, miembro):
    assert _client().post("/auth/portal/refresh").status_code == 401

    # Token cuya ventana de 7 días ya venció (spec: debe loguearse de nuevo).
    db.add(
        RefreshToken(
            usuario_id=miembro.id,
            token_hash=_hash_refresh_token("token-vencido"),
            expira_en=now() - timedelta(days=1),
        )
    )
    db.commit()
    resp = _client().post("/auth/portal/refresh", cookies={COOKIE: "token-vencido"})
    assert resp.status_code == 401


def test_refresh_renueva_la_ventana_de_inactividad(db, miembro):
    client = _client()
    _login(client, miembro.email)
    fila_original = db.scalars(select(RefreshToken)).one()
    db.execute(
        RefreshToken.__table__.update()
        .where(RefreshToken.id == fila_original.id)
        .values(expira_en=now() + timedelta(days=1))
    )
    db.commit()

    assert client.post("/auth/portal/refresh").status_code == 200

    db.expire_all()
    vigente = db.scalars(
        select(RefreshToken).where(RefreshToken.revocado_en.is_(None))
    ).one()
    assert vigente.expira_en > now() + timedelta(days=6)


def test_refresh_de_miembro_desactivado_401(db, miembro):
    client = _client()
    _login(client, miembro.email)
    miembro.estado = EstadoUsuario.inactivo
    db.commit()

    assert client.post("/auth/portal/refresh").status_code == 401


# --- Activación de cuenta (staff crea → miembro activa) ---


def test_activar_cuenta_ok_y_login_posterior(db, miembro_sin_password):
    resp = _client().post(
        "/auth/portal/activar",
        json={
            "cedula": miembro_sin_password.cedula,
            "email": miembro_sin_password.email,
            "password": "MiClaveNueva1",
        },
    )
    assert resp.status_code == 204

    db.expire_all()
    assert miembro_sin_password.password_hash is not None
    assert miembro_sin_password.password_hash != "MiClaveNueva1"  # RN-12: nunca texto plano

    login = _login(_client(), miembro_sin_password.email, "MiClaveNueva1")
    assert login.status_code == 200


def test_activar_falla_con_mensaje_generico(db, miembro, miembro_sin_password):
    client = _client()
    datos_no_coinciden = client.post(
        "/auth/portal/activar",
        json={"cedula": miembro_sin_password.cedula, "email": "otro@x.test", "password": "abc"},
    )
    ya_activada = client.post(
        "/auth/portal/activar",
        json={"cedula": miembro.cedula, "email": miembro.email, "password": "abc"},
    )
    cedula_inexistente = client.post(
        "/auth/portal/activar",
        json={"cedula": "999999999", "email": "x@x.test", "password": "abc"},
    )

    assert datos_no_coinciden.status_code == ya_activada.status_code == 400
    assert cedula_inexistente.status_code == 400
    assert datos_no_coinciden.json() == ya_activada.json() == cedula_inexistente.json()


def test_activar_rechaza_rol_no_miembro(db):
    staff = _crear_staff(db, RolUsuario.empleado, "empleado-activar@gymflow.test")
    staff.cedula = "111222333"
    staff.password_hash = None
    db.commit()

    resp = _client().post(
        "/auth/portal/activar",
        json={"cedula": "111222333", "email": staff.email, "password": "abc"},
    )
    assert resp.status_code == 400


# --- Logout ---


def test_logout_revoca_el_refresh_token(db, miembro):
    client = _client()
    _login(client, miembro.email)
    cookie = client.cookies[COOKIE]

    assert client.post("/auth/portal/logout").status_code == 204

    resp = _client().post("/auth/portal/refresh", cookies={COOKIE: cookie})
    assert resp.status_code == 401

"""
Tests HTTP de POST /auth/login y del guard de permisos aplicado a
checkin/router.py, contra los criterios de aceptación de
spec/features/003-autenticacion-segura/spec.md.
"""
from fastapi.testclient import TestClient

from auth.conftest import PASSWORD, otorgar_permiso
from core.security import create_access_token, decode_access_token
from main import app

client = TestClient(app)


def test_login_credenciales_validas_devuelve_200_y_token(db, empleado):
    resp = client.post("/auth/login", json={"email": empleado.email, "password": PASSWORD})

    assert resp.status_code == 200
    body = resp.json()
    assert body["access_token"]
    assert body["rol"] == "empleado"


def test_login_credenciales_invalidas_devuelve_401_mensaje_generico(db, empleado):
    resp_password = client.post(
        "/auth/login", json={"email": empleado.email, "password": "incorrecta"}
    )
    resp_email = client.post(
        "/auth/login", json={"email": "no-existe@gymflow.test", "password": PASSWORD}
    )

    assert resp_password.status_code == resp_email.status_code == 401
    assert resp_password.json() == resp_email.json()


def test_endpoint_protegido_sin_token_devuelve_401(db):
    resp = client.get("/checkin/dispositivos-bloqueados")
    assert resp.status_code == 401


def test_endpoint_protegido_sin_permiso_devuelve_403(db, empleado):
    token = create_access_token({"sub": str(empleado.id), "rol": "empleado"})
    resp = client.get(
        "/checkin/dispositivos-bloqueados", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 403


def test_endpoint_protegido_con_permiso_otorgado_devuelve_200_y_renueva_token(db, empleado):
    otorgar_permiso(db, empleado.id, "checkin.ver_dispositivos_bloqueados")
    # exp corto a propósito: garantiza que el token renovado (+30min por
    # default) quede estrictamente después, sin depender de que las dos
    # llamadas a create_access_token caigan en segundos distintos.
    token = create_access_token({"sub": str(empleado.id), "rol": "empleado"}, expires_minutes=1)

    resp = client.get(
        "/checkin/dispositivos-bloqueados", headers={"Authorization": f"Bearer {token}"}
    )

    assert resp.status_code == 200
    nuevo_token = resp.headers.get("x-new-token")
    assert nuevo_token
    original_exp = decode_access_token(token)["exp"]
    nuevo_exp = decode_access_token(nuevo_token)["exp"]
    assert nuevo_exp > original_exp


def test_desbloquear_dispositivo_exige_su_propio_permiso_no_el_de_ver(db, empleado):
    # Un empleado con SOLO el permiso de "ver" no puede "desbloquear" — prueba
    # que los dos permisos son independientes, no un rol genérico compartido.
    otorgar_permiso(db, empleado.id, "checkin.ver_dispositivos_bloqueados")
    token = create_access_token({"sub": str(empleado.id), "rol": "empleado"})

    resp = client.post(
        "/checkin/desbloquear/kiosko-test-auth", headers={"Authorization": f"Bearer {token}"}
    )

    assert resp.status_code == 403


def test_desbloquear_dispositivo_con_permiso_otorgado_devuelve_200(db, empleado):
    otorgar_permiso(db, empleado.id, "checkin.desbloquear_dispositivo")
    token = create_access_token({"sub": str(empleado.id), "rol": "empleado"})

    resp = client.post(
        "/checkin/desbloquear/kiosko-test-auth", headers={"Authorization": f"Bearer {token}"}
    )

    assert resp.status_code == 200


def test_administrador_tiene_permisos_implicitos_sin_otorgar_nada(db, administrador):
    token = create_access_token({"sub": str(administrador.id), "rol": "administrador"})

    resp = client.get(
        "/checkin/dispositivos-bloqueados", headers={"Authorization": f"Bearer {token}"}
    )

    assert resp.status_code == 200


def test_token_expirado_devuelve_401(db, empleado):
    token_vencido = create_access_token(
        {"sub": str(empleado.id), "rol": "empleado"}, expires_minutes=-1
    )
    resp = client.get(
        "/checkin/dispositivos-bloqueados", headers={"Authorization": f"Bearer {token_vencido}"}
    )
    assert resp.status_code == 401


def test_kiosko_checkin_funciona_sin_authorization_header(db):
    # Cédula con formato válido (5-15 dígitos) pero sin usuario registrado ->
    # 404 (UsuarioNoEncontradoError), no 401: el kiosko nunca exige JWT.
    resp = client.post(
        "/checkin", json={"cedula": "99999999"}, headers={"X-Device-Id": "kiosko-test-auth"}
    )
    assert resp.status_code == 404

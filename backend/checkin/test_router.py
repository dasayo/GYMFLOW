"""
Tests HTTP de checkin/router.py para 005-cortesia-primer-dia (endpoint
POST /checkin/cortesia). El registro de cortesía es un flujo de Staff, no del
kiosko: exige el permiso members.gestionar_usuarios (RBAC, mismo patrón que 004).
"""
from fastapi.testclient import TestClient

from auth.conftest import _crear_staff, otorgar_permiso
from core.security import create_access_token
from main import app
from models import CheckIn, RolUsuario, User

client = TestClient(app)


def _token_staff_con_gestionar(db) -> str:
    empleado = _crear_staff(db, RolUsuario.empleado, "empleado-005@gymflow.test")
    otorgar_permiso(db, empleado.id, "members.gestionar_usuarios")
    return create_access_token({"sub": str(empleado.id), "rol": "empleado"})


def _token_staff_sin_permiso(db) -> str:
    empleado = _crear_staff(db, RolUsuario.empleado, "empleado-005-sin@gymflow.test")
    return create_access_token({"sub": str(empleado.id), "rol": "empleado"})


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_cortesia_sin_token_401(db):
    resp = client.post("/checkin/cortesia", json={"cedula": "900222111", "nombre": "X"})
    assert resp.status_code == 401


def test_cortesia_sin_permiso_403(db):
    token = _token_staff_sin_permiso(db)
    resp = client.post(
        "/checkin/cortesia",
        json={"cedula": "900222111", "nombre": "X"},
        headers=_headers(token),
    )
    assert resp.status_code == 403


def test_cortesia_exitosa_200_crea_prospecto(db):
    token = _token_staff_con_gestionar(db)
    resp = client.post(
        "/checkin/cortesia",
        json={"cedula": "900222111", "nombre": "Prospecto Web"},
        headers=_headers(token),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["resultado"] == "exitoso"
    assert body["razon"] is None

    prospecto = db.query(User).filter(User.cedula == "900222111").one()
    assert prospecto.rol == RolUsuario.invitado
    assert prospecto.cortesia_usada is True
    assert db.query(CheckIn).filter(CheckIn.usuario_id == prospecto.id).count() == 1


def test_cortesia_segundo_intento_denegado(db):
    token = _token_staff_con_gestionar(db)
    payload = {"cedula": "900222333", "nombre": "Repite"}
    client.post("/checkin/cortesia", json=payload, headers=_headers(token))
    resp = client.post("/checkin/cortesia", json=payload, headers=_headers(token))

    assert resp.status_code == 200
    body = resp.json()
    assert body["resultado"] == "denegado"
    assert body["razon"] == "CORTESIA_YA_UTILIZADA"


def test_cortesia_cedula_invalida_422(db):
    token = _token_staff_con_gestionar(db)
    resp = client.post(
        "/checkin/cortesia",
        json={"cedula": "abc", "nombre": "X"},
        headers=_headers(token),
    )
    assert resp.status_code == 422


def test_cortesia_nombre_vacio_422(db):
    token = _token_staff_con_gestionar(db)
    resp = client.post(
        "/checkin/cortesia",
        json={"cedula": "900222444", "nombre": "  "},
        headers=_headers(token),
    )
    assert resp.status_code == 422


# --- HU-05: POST /checkin/guest (check-in de invitado, titular presente) ---


def _crear_titular_con_cupo(db, cedula="1000000009", cupo=2):
    """Titular con membresía activa y `cupo` cupos de invitado."""
    from datetime import timedelta

    from membership.service import hoy
    from models import EstadoMembresia, EstadoUsuario, Membership, MembershipType

    tipo = MembershipType(
        nombre="Mensual", precio_base=50000, visitas_totales=30,
        cupo_invitados=cupo, duracion_dias=30, activo=True,
    )
    db.add(tipo)
    db.flush()
    titular = User(
        cedula=cedula, nombre="Titular Test",
        rol=RolUsuario.miembro, estado=EstadoUsuario.activo,
    )
    db.add(titular)
    db.flush()
    db.add(Membership(
        miembro_id=titular.id, tipo_id=tipo.id, visitas_restantes=5,
        cupo_invitados_restantes=cupo, fecha_inicio=hoy(),
        fecha_vencimiento=hoy() + timedelta(days=30),
        estado=EstadoMembresia.activa, monto=tipo.precio_base,
    ))
    db.commit()
    return titular


def test_guest_checkin_exitoso_200(db):
    titular = _crear_titular_con_cupo(db, cupo=2)
    resp = client.post(
        "/checkin/guest",
        json={"cedula_titular": titular.cedula, "cedula_invitado": "700100200", "nombre_invitado": "Invitado HTTP"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["resultado"] == "exitoso"
    assert body["nombre"] == "Invitado HTTP"
    assert "1 invitaciones restantes" in body["mensaje"]


def test_guest_checkin_sin_cupo_denegado(db):
    titular = _crear_titular_con_cupo(db, cupo=0)
    resp = client.post(
        "/checkin/guest",
        json={"cedula_titular": titular.cedula, "cedula_invitado": "700100201", "nombre_invitado": "X"},
    )
    assert resp.status_code == 200
    assert resp.json()["razon"] == "SIN_CUPO_INVITADOS"


def test_guest_checkin_titular_e_invitado_iguales_422(db):
    resp = client.post(
        "/checkin/guest",
        json={"cedula_titular": "700100202", "cedula_invitado": "700100202", "nombre_invitado": "X"},
    )
    assert resp.status_code == 422


def test_guest_checkin_cedula_invalida_422(db):
    resp = client.post(
        "/checkin/guest",
        json={"cedula_titular": "1000000009", "cedula_invitado": "abc", "nombre_invitado": "X"},
    )
    assert resp.status_code == 422

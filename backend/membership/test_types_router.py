"""
Tests HTTP del CRUD de tipos de membresía (HU-08). Verifica RBAC (solo
Administrador, RF-09), el flujo feliz y los bloqueos RN-05 vía API.
"""
from decimal import Decimal

from fastapi.testclient import TestClient

from auth.conftest import _crear_staff
from core.security import create_access_token
from main import app
from membership.service import create_membership, create_type
from models import EstadoMembresia, EstadoUsuario, RolUsuario, User

client = TestClient(app)

_TIPO_VALIDO = {
    "nombre": "Trimestral", "precio_base": "120000", "visitas_totales": 90,
    "cupo_invitados": 2, "duracion_dias": 90, "activo": True,
}


def _token(user) -> dict:
    return {"Authorization": f"Bearer {create_access_token({'sub': str(user.id), 'rol': user.rol.value})}"}


def _crear_socio(db) -> User:
    user = User(
        cedula="2000000002", nombre="Socio Test", rol=RolUsuario.miembro,
        estado=EstadoUsuario.activo,
    )
    db.add(user)
    db.commit()
    return user


def test_post_tipo_sin_token_401(db):
    assert client.post("/membresias/tipos", json=_TIPO_VALIDO).status_code == 401


def test_post_tipo_empleado_403(db):
    empleado = _crear_staff(db, RolUsuario.empleado, "emp-tipos@gymflow.test")
    resp = client.post("/membresias/tipos", json=_TIPO_VALIDO, headers=_token(empleado))
    assert resp.status_code == 403


def test_post_tipo_admin_201(db):
    admin = _crear_staff(db, RolUsuario.administrador, "admin-tipos@gymflow.test")
    resp = client.post("/membresias/tipos", json=_TIPO_VALIDO, headers=_token(admin))
    assert resp.status_code == 201
    body = resp.json()
    assert body["nombre"] == "Trimestral"
    assert body["activo"] is True


def test_post_tipo_validacion_422(db):
    admin = _crear_staff(db, RolUsuario.administrador, "admin-val@gymflow.test")
    invalido = {**_TIPO_VALIDO, "duracion_dias": 0}  # gt=0
    resp = client.post("/membresias/tipos", json=invalido, headers=_token(admin))
    assert resp.status_code == 422


def test_get_tipos_admin_empleado_403(db):
    empleado = _crear_staff(db, RolUsuario.empleado, "emp-list@gymflow.test")
    assert client.get("/membresias/tipos/admin", headers=_token(empleado)).status_code == 403


def test_get_tipos_admin_incluye_inactivos(db):
    create_type("Activo", Decimal("1"), 1, 0, 1, True, db)
    create_type("Inactivo", Decimal("1"), 1, 0, 1, False, db)
    db.commit()
    admin = _crear_staff(db, RolUsuario.administrador, "admin-list@gymflow.test")

    resp = client.get("/membresias/tipos/admin", headers=_token(admin))

    assert resp.status_code == 200
    assert sorted(t["nombre"] for t in resp.json()) == ["Activo", "Inactivo"]


def test_put_tipo_desactivar_con_activa_409(db):
    tipo = create_type("Mensual", Decimal("50000"), 30, 1, 30, True, db)
    db.commit()
    socio = _crear_socio(db)
    create_membership(socio.id, tipo.id, Decimal("50000"), None, db)
    db.commit()
    admin = _crear_staff(db, RolUsuario.administrador, "admin-put@gymflow.test")

    resp = client.put(f"/membresias/tipos/{tipo.id}", json={"activo": False}, headers=_token(admin))

    assert resp.status_code == 409


def test_delete_tipo_con_historial_409(db):
    tipo = create_type("Mensual", Decimal("50000"), 30, 1, 30, True, db)
    db.commit()
    socio = _crear_socio(db)
    membership = create_membership(socio.id, tipo.id, Decimal("50000"), None, db)
    membership.estado = EstadoMembresia.vencida
    db.commit()
    admin = _crear_staff(db, RolUsuario.administrador, "admin-del@gymflow.test")

    resp = client.delete(f"/membresias/tipos/{tipo.id}", headers=_token(admin))

    assert resp.status_code == 409


def test_delete_tipo_sin_uso_204(db):
    tipo = create_type("Efímero", Decimal("1"), 1, 0, 1, True, db)
    db.commit()
    admin = _crear_staff(db, RolUsuario.administrador, "admin-del2@gymflow.test")

    resp = client.delete(f"/membresias/tipos/{tipo.id}", headers=_token(admin))

    assert resp.status_code == 204
    assert client.get("/membresias/tipos/admin", headers=_token(admin)).json() == []

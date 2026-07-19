"""
Tests del resumen de membresía (007, RF-04): GET /membresias/me/resumen y
get_membership_summary_detail — contra los criterios de aceptación de
spec/features/007-resumen-membresia/spec.md.
"""
from datetime import datetime, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import func, select

import membership.service as membership_service
from core.security import create_access_token
from main import app
from models import (
    CheckIn,
    EstadoMembresia,
    EstadoUsuario,
    Membership,
    MembershipType,
    RolUsuario,
    User,
)

client = TestClient(app)

HOY = membership_service.hoy()


def _crear_socio(db, cedula="123456789") -> User:
    user = User(cedula=cedula, nombre="Socio Resumen", rol=RolUsuario.miembro,
                estado=EstadoUsuario.activo)
    db.add(user)
    db.commit()
    return user


def _crear_tipo(db, nombre="Mensual") -> MembershipType:
    tipo = MembershipType(
        nombre=nombre, precio_base=Decimal("50000"), visitas_totales=30,
        cupo_invitados=2, duracion_dias=30, activo=True,
    )
    db.add(tipo)
    db.commit()
    return tipo


def _crear_membresia(db, user, tipo, vence_en_dias: int, visitas=12, cupos=2) -> Membership:
    membership = Membership(
        miembro_id=user.id,
        tipo_id=tipo.id,
        visitas_restantes=visitas,
        cupo_invitados_restantes=cupos,
        fecha_inicio=HOY + timedelta(days=vence_en_dias - 30),
        fecha_vencimiento=HOY + timedelta(days=vence_en_dias),
        estado=EstadoMembresia.activa,
        monto=Decimal("50000"),
    )
    db.add(membership)
    db.commit()
    return membership


def _token_miembro(user) -> str:
    return create_access_token({"sub": str(user.id), "rol": "miembro", "kind": "member"})


def _get_resumen(user):
    return client.get(
        "/membresias/me/resumen", headers={"Authorization": f"Bearer {_token_miembro(user)}"}
    )


# --- Criterio: miembro activo ve todos los campos (RF-04) ---


def test_resumen_miembro_activo_campos_completos(db):
    socio = _crear_socio(db)
    tipo = _crear_tipo(db)
    _crear_membresia(db, socio, tipo, vence_en_dias=20)

    resp = _get_resumen(socio)

    assert resp.status_code == 200
    assert resp.json() == {
        "estado": "activa",
        "tipo": "Mensual",
        "fecha_vencimiento": str(HOY + timedelta(days=20)),
        "visitas_restantes": 12,
        "cupo_invitados_restantes": 2,
        "dias_restantes": 20,
    }


# --- Criterio: dias_restantes calculado y umbral del aviso (≤10) ---


def test_dias_restantes_en_los_bordes_del_aviso(db):
    tipo = _crear_tipo(db)
    for dias, cedula in ((11, "111"), (10, "222"), (0, "333")):
        otro = _crear_socio(db, cedula=cedula)
        _crear_membresia(db, otro, tipo, vence_en_dias=dias)
        assert _get_resumen(otro).json()["dias_restantes"] == dias
        # El umbral (mostrar aviso solo si 0 <= dias <= 10) lo aplica el
        # Dashboard del portal sobre este valor exacto.


# --- Criterio: vencida / sin plan devuelven resumen coherente, no error ---


def test_resumen_membresia_vencida(db):
    socio = _crear_socio(db)
    tipo = _crear_tipo(db)
    _crear_membresia(db, socio, tipo, vence_en_dias=-3, visitas=5)

    resp = _get_resumen(socio)

    assert resp.status_code == 200
    body = resp.json()
    assert body["estado"] == "vencida"
    assert body["fecha_vencimiento"] == str(HOY - timedelta(days=3))
    assert body["dias_restantes"] is None


def test_resumen_sin_plan(db):
    socio = _crear_socio(db)

    resp = _get_resumen(socio)

    assert resp.status_code == 200
    body = resp.json()
    assert body["estado"] == "sin_plan"
    assert body["tipo"] is None
    assert body["dias_restantes"] is None


# --- Criterio: consulta de SOLO lectura (no descuenta ni registra CheckIn) ---


def test_resumen_no_descuenta_ni_registra_checkin(db):
    socio = _crear_socio(db)
    tipo = _crear_tipo(db)
    membresia = _crear_membresia(db, socio, tipo, vence_en_dias=20, visitas=12, cupos=2)

    assert _get_resumen(socio).status_code == 200

    db.expire_all()
    assert membresia.visitas_restantes == 12
    assert membresia.cupo_invitados_restantes == 2
    assert db.scalar(select(func.count()).select_from(CheckIn)) == 0


def test_constancia_semana_para_portal(db):
    socio = _crear_socio(db)
    tipo = _crear_tipo(db)
    _crear_membresia(db, socio, tipo, vence_en_dias=20)

    db.add_all(
        [
            CheckIn(
                usuario_id=socio.id,
                fecha_hora=datetime.now() - timedelta(days=1),
                resultado="exitoso",
                is_active=True,
            ),
            CheckIn(
                usuario_id=socio.id,
                fecha_hora=datetime.now(),
                resultado="exitoso",
                is_active=True,
            ),
            CheckIn(
                usuario_id=socio.id,
                fecha_hora=datetime.now() - timedelta(days=8),
                resultado="exitoso",
                is_active=True,
            ),
        ]
    )
    db.commit()

    resp = client.get(
        "/checkin/me/constancia",
        headers={"Authorization": f"Bearer {_token_miembro(socio)}"},
        params={"period": "semana"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["periodo"] == "semana"
    assert body["total"] == 2
    assert any(point["fecha"] == str(HOY) and point["asistencias"] == 1 for point in body["puntos"])
    assert any(
        point["fecha"] == str(HOY - timedelta(days=1)) and point["asistencias"] == 1
        for point in body["puntos"]
    )
    assert any(
        point["fecha"] == str(HOY - timedelta(days=6)) and point["asistencias"] == 0
        for point in body["puntos"]
    )


# --- Guard: solo el Miembro del portal, nunca staff ni anónimos ---


def test_resumen_sin_token_401(db):
    assert client.get("/membresias/me/resumen").status_code == 401


def test_resumen_con_jwt_de_staff_403(db):
    # Un JWT de staff (003) no lleva el claim kind=member: no sirve en el portal.
    token_staff = create_access_token({"sub": "1", "rol": "administrador"})
    resp = client.get(
        "/membresias/me/resumen", headers={"Authorization": f"Bearer {token_staff}"}
    )
    assert resp.status_code == 403

"""
Fixtures compartidas de los tests de auth. Como 004-gestion-usuarios (CRUD)
todavía no existe, los usuarios de staff y sus permisos se siembran directo
por SQLAlchemy — mismo patrón que checkin/test_service.py usa para socios.
"""
import pytest
from sqlalchemy import select

from core.security import hash_password
from models import EstadoUsuario, Permiso, RolUsuario, User, usuario_permisos

PASSWORD = "ClaveSegura123"


def _crear_staff(db, rol, email, estado=EstadoUsuario.activo):
    user = User(
        nombre="Staff Test",
        email=email,
        rol=rol,
        estado=estado,
        password_hash=hash_password(PASSWORD),
    )
    db.add(user)
    db.commit()
    return user


def otorgar_permiso(db, usuario_id: int, codigo: str) -> None:
    permiso_id = db.scalar(select(Permiso.id).where(Permiso.codigo == codigo))
    db.execute(usuario_permisos.insert().values(usuario_id=usuario_id, permiso_id=permiso_id))
    db.commit()


@pytest.fixture
def empleado(db):
    return _crear_staff(db, RolUsuario.empleado, "empleado@gymflow.test")


@pytest.fixture
def administrador(db):
    return _crear_staff(db, RolUsuario.administrador, "admin@gymflow.test")


@pytest.fixture
def empleado_inactivo(db):
    return _crear_staff(
        db, RolUsuario.empleado, "empleado.inactivo@gymflow.test", estado=EstadoUsuario.inactivo
    )

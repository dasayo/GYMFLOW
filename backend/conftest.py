"""
Fixtures compartidas de pytest. Requiere DATABASE_URL/JWT_SECRET ya presentes
en el entorno (igual que en .github/workflows/ci.yml) y el esquema migrado
(`alembic upgrade head`) antes de correr los tests.
"""
import pytest
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

from core.database import engine

_TABLAS_DE_TEST = (
    "checkins",
    "checkin_device_locks",
    "checkin_qr_nonces",
    "dispositivos_autorizados",
    "membresias",
    "refresh_tokens",
    "usuarios",
    "tipos_membresia",
    "invitados",
)


@pytest.fixture
def db():
    Session = sessionmaker(bind=engine)
    session = Session()
    for tabla in _TABLAS_DE_TEST:
        session.execute(text(f"TRUNCATE TABLE {tabla} RESTART IDENTITY CASCADE"))
    session.commit()
    yield session
    session.close()

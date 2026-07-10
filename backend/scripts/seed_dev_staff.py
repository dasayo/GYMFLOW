"""
Siembra usuarios de Staff de prueba en la base de datos local, para poder
probar el login/backoffice de spec/features/003-autenticacion-segura sin
esperar a 004-gestion-usuarios (que todavía no tiene CRUD). Solo para
desarrollo local — no correr contra una base de datos compartida/producción.

Uso (con la BD ya migrada, `pipenv run alembic upgrade head`):
    cd backend
    pipenv run python scripts/seed_dev_staff.py

Idempotente: si el correo ya existe, lo deja como está y sigue.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from core.database import engine
from core.security import hash_password
from models import EstadoUsuario, Permiso, RolUsuario, User, usuario_permisos

PASSWORD = "ClaveSegura123"

STAFF = [
    ("empleado@gymflow.test", RolUsuario.empleado),
    ("admin@gymflow.test", RolUsuario.administrador),
]

# Permisos individuales de ejemplo (ver spec/features/003-autenticacion-segura):
# se le otorgan solo al empleado, para poder probar la diferencia entre "rol"
# y "permiso" — el administrador no los necesita (los tiene implícitos).
PERMISOS_PARA_EMPLEADO = (
    "checkin.ver_dispositivos_bloqueados",
    "checkin.desbloquear_dispositivo",
)


def main() -> None:
    Session = sessionmaker(bind=engine)
    db = Session()

    creados = {}
    for email, rol in STAFF:
        existente = db.query(User).filter(User.email == email).first()
        if existente:
            print(f"ya existe, no se toca: {email}")
            creados[email] = existente
            continue
        user = User(
            nombre="Staff Demo",
            email=email,
            rol=rol,
            estado=EstadoUsuario.activo,
            password_hash=hash_password(PASSWORD),
        )
        db.add(user)
        db.commit()
        print(f"creado: {email} (rol={rol.value})")
        creados[email] = user

    empleado = creados["empleado@gymflow.test"]
    for codigo in PERMISOS_PARA_EMPLEADO:
        permiso_id = db.scalar(select(Permiso.id).where(Permiso.codigo == codigo))
        if permiso_id is None:
            print(f"aviso: no existe el permiso '{codigo}' (¿faltan migraciones?)")
            continue
        ya_otorgado = db.execute(
            select(usuario_permisos).where(
                usuario_permisos.c.usuario_id == empleado.id,
                usuario_permisos.c.permiso_id == permiso_id,
            )
        ).first()
        if not ya_otorgado:
            db.execute(
                usuario_permisos.insert().values(usuario_id=empleado.id, permiso_id=permiso_id)
            )
    db.commit()
    db.close()

    print()
    print("Password para ambos (solo desarrollo local):", PASSWORD)
    print("- empleado@gymflow.test  -> rol empleado, con permisos de checkin otorgados")
    print("- admin@gymflow.test     -> rol administrador (todos los permisos, implícito)")


if __name__ == "__main__":
    main()

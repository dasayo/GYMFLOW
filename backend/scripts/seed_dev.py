"""
Siembra los datos mínimos de DESARROLLO para que el stack sirva recién
levantado (`docker compose up`), sin pasos manuales:

- Staff de prueba (empleado + administrador) con sus permisos individuales.
- Un tipo de membresía ("Mensual") para poder asignar/renovar (004) — el CRUD
  de tipos es 009 y aún no existe, sin esto el backoffice no puede asignar nada.
- Una socia de demostración con membresía activa (probar kiosko/portal de una)
  y SIN contraseña: sirve también para demostrar la activación de cuenta (011).

El catálogo de PERMISOS no se siembra aquí: eso es código de developer y viaja
en las migraciones Alembic (003/004) — el admin solo otorga/quita códigos
existentes, nunca los crea.

Idempotente: lo que ya existe se deja como está. Solo para desarrollo local /
demo — docker-entrypoint.sh lo corre automáticamente salvo ENVIRONMENT=production.

Uso manual (con la BD ya migrada):
    cd backend
    pipenv run python scripts/seed_dev.py
"""
import sys
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from core.config import now
from core.database import engine
from core.security import hash_password
from models import (
    EstadoMembresia,
    EstadoUsuario,
    Membership,
    MembershipType,
    Permiso,
    RolUsuario,
    User,
    usuario_permisos,
)

PASSWORD = "ClaveSegura123"

STAFF = [
    ("empleado@gymflow.test", RolUsuario.empleado),
    ("admin@gymflow.test", RolUsuario.administrador),
]

# Permisos individuales de ejemplo (003/004): se otorgan solo al empleado para
# poder probar la diferencia entre "rol" y "permiso" — el administrador los
# tiene todos implícitos. Para probar el CASO SIN permisos, crear un segundo
# empleado desde el backoffice y no otorgarle nada.
PERMISOS_PARA_EMPLEADO = (
    "checkin.ver_dispositivos_bloqueados",
    "checkin.desbloquear_dispositivo",
    "members.gestionar_usuarios",
    "members.asignar_rol_empleado",
    "membership.renovar",
)

SOCIA_DEMO = {"cedula": "555444333", "nombre": "Laura Demo", "email": "laura@socia.test"}


def _seed_staff(db: Session) -> None:
    creados = {}
    for email, rol in STAFF:
        existente = db.query(User).filter(User.email == email).first()
        if existente:
            print(f"seed: ya existe, no se toca: {email}")
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
        print(f"seed: creado {email} (rol={rol.value})")
        creados[email] = user

    empleado = creados["empleado@gymflow.test"]
    for codigo in PERMISOS_PARA_EMPLEADO:
        permiso_id = db.scalar(select(Permiso.id).where(Permiso.codigo == codigo))
        if permiso_id is None:
            print(f"seed: aviso — no existe el permiso '{codigo}' (¿faltan migraciones?)")
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


def _seed_tipo_membresia(db: Session) -> MembershipType:
    tipo = db.query(MembershipType).filter(MembershipType.nombre == "Mensual").first()
    if tipo:
        print("seed: ya existe el tipo 'Mensual', no se toca")
        return tipo
    tipo = MembershipType(
        nombre="Mensual",
        precio_base=Decimal("50000"),
        visitas_totales=30,
        cupo_invitados=2,
        duracion_dias=30,
        activo=True,
    )
    db.add(tipo)
    db.commit()
    print("seed: creado tipo de membresía 'Mensual'")
    return tipo


def _seed_socia_demo(db: Session, tipo: MembershipType) -> None:
    socia = db.query(User).filter(User.cedula == SOCIA_DEMO["cedula"]).first()
    if socia is None:
        socia = User(
            cedula=SOCIA_DEMO["cedula"],
            nombre=SOCIA_DEMO["nombre"],
            email=SOCIA_DEMO["email"],
            rol=RolUsuario.miembro,
            estado=EstadoUsuario.activo,
            password_hash=None,  # sin activar: permite demostrar /portal/activar (011)
        )
        db.add(socia)
        db.commit()
        print(f"seed: creada socia demo {SOCIA_DEMO['email']} (cédula {SOCIA_DEMO['cedula']})")
    else:
        print("seed: ya existe la socia demo, no se toca")

    tiene_membresia = (
        db.query(Membership).filter(Membership.miembro_id == socia.id).first() is not None
    )
    if tiene_membresia:
        return
    hoy = now().date()
    db.add(
        Membership(
            miembro_id=socia.id,
            tipo_id=tipo.id,
            visitas_restantes=tipo.visitas_totales,
            cupo_invitados_restantes=tipo.cupo_invitados,
            fecha_inicio=hoy,
            fecha_vencimiento=hoy + timedelta(days=tipo.duracion_dias),
            estado=EstadoMembresia.activa,
            monto=tipo.precio_base,
            nota="seed de desarrollo",
        )
    )
    db.commit()
    print("seed: membresía Mensual activa asignada a la socia demo")


def main() -> None:
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        _seed_staff(db)
        tipo = _seed_tipo_membresia(db)
        _seed_socia_demo(db, tipo)
    finally:
        db.close()

    print()
    print("Cuentas de desarrollo (password staff:", PASSWORD + "):")
    print("- empleado@gymflow.test  -> backoffice, rol empleado con permisos de ejemplo")
    print("- admin@gymflow.test     -> backoffice, rol administrador")
    print("- laura@socia.test       -> socia demo (cédula 555444333), membresía activa,")
    print("                            cuenta del portal SIN activar (usar /portal/activar)")


if __name__ == "__main__":
    main()

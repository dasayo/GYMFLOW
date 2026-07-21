"""
Fixtures compartidas de los tests de checkin (012-checkin-qr-dinamico):
autorizar un `device_id` en la lista blanca sin pasar por HTTP.
"""
from core.config import now as _now
from models import DispositivoAutorizado, RolUsuario, User
from core.security import hash_password


def autorizar_dispositivo(db, device_id: str) -> None:
    admin = User(
        nombre="Admin Autoriza Dispositivos",
        email=f"admin-autoriza-{device_id}@gymflow.test",
        rol=RolUsuario.administrador,
        password_hash=hash_password("ClaveSegura123"),
    )
    db.add(admin)
    db.flush()
    db.add(
        DispositivoAutorizado(
            device_id=device_id, autorizado_en=_now(), autorizado_por_id=admin.id
        )
    )
    db.commit()

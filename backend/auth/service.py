"""
Servicio de auth.

Regla de módulos (no negociable, AGENTS.md): este service es el ÚNICO punto de
entrada que otros módulos pueden llamar para leer/mutar datos de auth.
Ningún otro módulo debe importar auth/repository.py directamente.

Para leer `usuarios` reutiliza members.service (auth no tiene repository
propio para esa tabla; solo lo tiene para `permisos`/`usuario_permisos`).
"""
import hashlib
import secrets
from datetime import timedelta

from sqlalchemy.orm import Session

import members.service as members_service
from auth.repository import AuthRepository, RefreshTokenRepository
from core.config import now, settings
from core.security import create_access_token, verify_password
from models import EstadoUsuario, Permiso, RefreshToken, RolUsuario, User

_ROLES_BACKOFFICE = (RolUsuario.empleado, RolUsuario.administrador)


class CredencialesInvalidasError(Exception):
    """Cubre: email inexistente, password incorrecta, rol no es Empleado/
    Administrador, o estado inactivo. Nunca se distingue el motivo en la
    respuesta (spec.md: 'sin revelar si el usuario existe')."""


class PermisoInexistenteError(Exception):
    """El código de permiso pedido no está en el catálogo (004)."""


class SesionInvalidaError(Exception):
    """011: refresh token inexistente, expirado, revocado, o cuyo usuario ya
    no es un Miembro activo. Nunca se distingue el motivo en la respuesta."""


class ActivacionInvalidaError(Exception):
    """011: cédula+correo no corresponden a un Miembro activo sin contraseña.
    Cubre también 'ya tiene contraseña' — no se revela qué condición falló."""


def login(email: str, password: str, db: Session) -> tuple[str, RolUsuario, set[str]]:
    user = members_service.get_user_by_email(email, db)

    credenciales_ok = (
        user is not None
        and user.password_hash is not None
        and user.rol in _ROLES_BACKOFFICE
        and user.estado == EstadoUsuario.activo
        and verify_password(password, user.password_hash)
    )
    if not credenciales_ok:
        raise CredencialesInvalidasError()

    token = create_access_token({"sub": str(user.id), "rol": user.rol.value})
    permisos = get_user_permissions(user.id, db)
    return token, user.rol, permisos


# --- Sesión del Miembro en el portal (011-portal-miembro-autenticacion) ---


def _hash_refresh_token(raw_token: str) -> str:
    """SHA-256 del token opaco: en DB nunca se guarda el token en claro, así
    un dump de la tabla no permite fabricar sesiones."""
    return hashlib.sha256(raw_token.encode()).hexdigest()


def _emitir_sesion_miembro(user: User, db: Session) -> tuple[str, str]:
    """Access token corto (claim `kind=member`, que un JWT de staff no lleva)
    + refresh token opaco nuevo con la ventana deslizante completa."""
    access_token = create_access_token(
        {"sub": str(user.id), "rol": user.rol.value, "kind": "member"},
        expires_minutes=settings.member_access_token_minutes,
    )
    raw_refresh = secrets.token_urlsafe(48)
    RefreshTokenRepository(db).create(
        RefreshToken(
            usuario_id=user.id,
            token_hash=_hash_refresh_token(raw_refresh),
            expira_en=now() + timedelta(days=settings.member_refresh_days),
        )
    )
    return access_token, raw_refresh


def _es_miembro_activo(user: User | None) -> bool:
    return (
        user is not None
        and user.rol == RolUsuario.miembro
        and user.estado == EstadoUsuario.activo
    )


def login_member(email: str, password: str, db: Session) -> tuple[str, str, User]:
    """Login del portal: solo rol `miembro` activo con contraseña ya activada.
    Mismo criterio anti-enumeración que el login de staff."""
    user = members_service.get_user_by_email(email, db)
    credenciales_ok = (
        _es_miembro_activo(user)
        and user.password_hash is not None
        and verify_password(password, user.password_hash)
    )
    if not credenciales_ok:
        raise CredencialesInvalidasError()

    access_token, raw_refresh = _emitir_sesion_miembro(user, db)
    db.commit()
    return access_token, raw_refresh, user


def refresh_member_session(raw_token: str, db: Session) -> tuple[str, str, User]:
    """Rotación (spec 011): el refresh usado se revoca y se emite uno nuevo
    con la ventana de inactividad renovada — un token robado deja de servir
    en cuanto se usa el legítimo. Revalida que el usuario siga siendo un
    Miembro activo (si el staff lo desactivó, la sesión larga muere aquí)."""
    repo = RefreshTokenRepository(db)
    ahora = now()
    fila = repo.get_vigente_by_hash(_hash_refresh_token(raw_token), ahora)
    if fila is None:
        raise SesionInvalidaError()

    try:
        user = members_service.get_user(fila.usuario_id, db)
    except members_service.UsuarioNoEncontradoError:
        user = None
    if not _es_miembro_activo(user):
        repo.revoke(fila, ahora)
        db.commit()
        raise SesionInvalidaError()

    repo.revoke(fila, ahora)
    access_token, raw_refresh = _emitir_sesion_miembro(user, db)
    db.commit()
    return access_token, raw_refresh, user


def activate_member_account(cedula: str, email: str, password: str, db: Session) -> None:
    """Activación de cuenta (dudas resueltas en spec 011): la cuenta la creó
    el staff (004); el Miembro define su contraseña la primera vez si cédula y
    correo coinciden con un Miembro activo SIN contraseña previa. El hash lo
    hace members.service (RN-12), dueño de la tabla `usuarios`."""
    user = members_service.get_user_by_cedula(cedula, db)
    puede_activar = (
        _es_miembro_activo(user)
        and user.email is not None
        and user.email.strip().lower() == email.strip().lower()
        and user.password_hash is None
    )
    if not puede_activar:
        raise ActivacionInvalidaError()
    members_service.update_user(user.id, db, password=password)


def logout_member(raw_token: str, db: Session) -> None:
    """Revoca el refresh token si sigue vigente; idempotente (un logout con
    token ya inválido no es un error)."""
    repo = RefreshTokenRepository(db)
    ahora = now()
    fila = repo.get_vigente_by_hash(_hash_refresh_token(raw_token), ahora)
    if fila is not None:
        repo.revoke(fila, ahora)
        db.commit()


def get_user_permissions(usuario_id: int, db: Session) -> set[str]:
    return AuthRepository(db).get_permission_codes(usuario_id)


def list_permissions(usuario_id: int, db: Session) -> list[Permiso]:
    members_service.get_user(usuario_id, db)  # 404 limpio si no existe
    return AuthRepository(db).list_granted(usuario_id)


def list_permissions_catalog(db: Session) -> list[Permiso]:
    """Todo el catálogo (004): para que un administrador vea qué códigos
    existen antes de otorgar uno, en vez de escribirlo a ciegas."""
    return AuthRepository(db).list_catalog()


def grant_permission(usuario_id: int, codigo: str, db: Session) -> None:
    members_service.get_user(usuario_id, db)
    permiso = AuthRepository(db).get_permiso_by_codigo(codigo)
    if permiso is None:
        raise PermisoInexistenteError()
    AuthRepository(db).grant(usuario_id, permiso.id)
    db.commit()


def revoke_permission(usuario_id: int, codigo: str, db: Session) -> None:
    members_service.get_user(usuario_id, db)
    permiso = AuthRepository(db).get_permiso_by_codigo(codigo)
    if permiso is None:
        raise PermisoInexistenteError()
    AuthRepository(db).revoke(usuario_id, permiso.id)
    db.commit()

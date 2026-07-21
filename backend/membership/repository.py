"""
Repository de membership — único punto de acceso a `membresias` y
`tipos_membresia` (convención del proyecto). Cubre HU-01, HU-06, HU-07 y
HU-08.
"""
from datetime import date

from sqlalchemy import func
from sqlalchemy.orm import Session

from models import Membership, MembershipType, EstadoMembresia


class MembershipRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_active_by_user(self, user_id: int, hoy: date) -> Membership | None:
        """La fila "vigente" es la que está en ventana de fechas
        (fecha_inicio <= hoy), no solo la que tiene estado=activa: una
        renovación anticipada (HU-07) puede dejar dos filas en estado=activa
        simultáneamente (la vieja, todavía vigente, y la nueva, con
        fecha_inicio en el futuro) — sin este filtro y el order_by,
        `.first()` elegiría una de las dos de forma no determinística."""
        return (
            self.db.query(Membership)
            .filter(
                Membership.miembro_id == user_id,
                Membership.estado == EstadoMembresia.activa,
                Membership.fecha_inicio <= hoy,
            )
            .order_by(Membership.fecha_inicio.desc(), Membership.id.desc())
            .first()
        )

    def get_latest_by_user(self, user_id: int) -> Membership | None:
        """La última fila creada para el usuario, sea cual sea su estado o
        fecha — usada por 004 para encontrar "la anterior" al renovar.
        Desempata por `id` cuando dos filas comparten `fecha_inicio` (ej. una
        renovación el mismo día que la anterior ya había vencido)."""
        return (
            self.db.query(Membership)
            .filter(Membership.miembro_id == user_id)
            .order_by(Membership.fecha_inicio.desc(), Membership.id.desc())
            .first()
        )

    def list_by_user(self, user_id: int) -> list[Membership]:
        return (
            self.db.query(Membership)
            .filter(Membership.miembro_id == user_id)
            .order_by(Membership.fecha_inicio.desc(), Membership.id.desc())
            .all()
        )

    def list_latest_by_user_ids(self, user_ids: list[int]) -> dict[int, Membership]:
        """HU-09: la Membership más reciente de cada usuario, en una sola query
        (evita N+1 al enriquecer el reporte con el tipo de plan). Mismo criterio
        de "última" que `get_latest_by_user` (fecha_inicio desc, id desc)."""
        if not user_ids:
            return {}
        filas = (
            self.db.query(Membership)
            .filter(Membership.miembro_id.in_(user_ids))
            .order_by(Membership.fecha_inicio.desc(), Membership.id.desc())
            .all()
        )
        latest: dict[int, Membership] = {}
        for fila in filas:
            latest.setdefault(fila.miembro_id, fila)
        return latest

    def create(self, membership: Membership) -> Membership:
        self.db.add(membership)
        self.db.flush()
        return membership

    def get_for_update(self, membership_id: int) -> Membership:
        """SELECT ... FOR UPDATE — serializa descuentos concurrentes (RN-10)."""
        return (
            self.db.query(Membership)
            .filter(Membership.id == membership_id)
            .with_for_update()
            .one()
        )


class MembershipTypeRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, tipo_id: int) -> MembershipType | None:
        return self.db.query(MembershipType).filter(MembershipType.id == tipo_id).first()

    def list_active(self) -> list[MembershipType]:
        """Solo los tipos `activo=true` — no tiene sentido ofrecer para
        asignar/renovar (HU-07) un tipo que ya fue desactivado (HU-08)."""
        return (
            self.db.query(MembershipType)
            .filter(MembershipType.activo.is_(True))
            .order_by(MembershipType.nombre)
            .all()
        )

    def list_all(self) -> list[MembershipType]:
        """Catálogo completo (activos e inactivos) para el CRUD del
        Administrador (HU-08). El listado de empleado usa `list_active`."""
        return self.db.query(MembershipType).order_by(MembershipType.nombre).all()

    def get_names_by_ids(self, tipo_ids: list[int]) -> dict[int, str]:
        """HU-09: nombres de tipos en lote para enriquecer el reporte."""
        if not tipo_ids:
            return {}
        filas = (
            self.db.query(MembershipType.id, MembershipType.nombre)
            .filter(MembershipType.id.in_(tipo_ids))
            .all()
        )
        return {tipo_id: nombre for tipo_id, nombre in filas}

    def create(self, tipo: MembershipType) -> MembershipType:
        self.db.add(tipo)
        self.db.flush()
        return tipo

    def delete(self, tipo: MembershipType) -> None:
        self.db.delete(tipo)
        self.db.flush()

    def count_active_memberships_by_type(self, tipo_id: int) -> int:
        """RN-05: cuántas `Membership` en estado `activa` referencian este tipo.
        Consulta intramódulo (`membership` posee ambas tablas)."""
        return (
            self.db.query(func.count(Membership.id))
            .filter(
                Membership.tipo_id == tipo_id,
                Membership.estado == EstadoMembresia.activa,
            )
            .scalar()
        )

    def count_any_memberships_by_type(self, tipo_id: int) -> int:
        """HU-08: cuántas `Membership` referencian este tipo, sin importar estado
        (activa o histórica). Un tipo con historial no se borra físicamente,
        solo se desactiva (preserva la trazabilidad de precios/planes)."""
        return (
            self.db.query(func.count(Membership.id))
            .filter(Membership.tipo_id == tipo_id)
            .scalar()
        )

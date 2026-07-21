"""
Repository de members — único punto de acceso a la tabla `usuarios`
(convención del proyecto). Cubre HU-01, HU-03, HU-04 y HU-07.
"""
from sqlalchemy import or_
from sqlalchemy.orm import Session

from models import User

# Caracteres con significado especial en un patrón LIKE/ILIKE. Si el staff
# escribe "_" o "%" en el buscador esperan buscar ese carácter literal, no
# el comodín de SQL (un "_" suelto haría match con todos los usuarios).
_COMODINES_LIKE = str.maketrans({"\\": r"\\", "%": r"\%", "_": r"\_"})


class MembersRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_cedula(self, cedula: str) -> User | None:
        return self.db.query(User).filter(User.cedula == cedula).first()

    def get_by_email(self, email: str) -> User | None:
        return self.db.query(User).filter(User.email == email).first()

    def get_by_id(self, user_id: int) -> User | None:
        return self.db.query(User).filter(User.id == user_id).first()

    def list_all(self) -> list[User]:
        return self.db.query(User).order_by(User.id).all()

    def search_by_name_or_doc(self, q: str, limit: int) -> list[User]:
        """Coincidencia parcial sobre nombre O cédula, en un solo campo
        (HU-03). Los usuarios anonimizados por RN-07 quedan fuera solos:
        con `nombre` y `cedula` en NULL, ILIKE nunca hace match."""
        patron = f"%{q.translate(_COMODINES_LIKE)}%"
        return (
            self.db.query(User)
            .filter(
                or_(
                    User.nombre.ilike(patron, escape="\\"),
                    User.cedula.ilike(patron, escape="\\"),
                )
            )
            .order_by(User.nombre, User.id)
            .limit(limit)
            .all()
        )

    def list_by_ids(self, user_ids: list[int]) -> list[User]:
        if not user_ids:
            return []
        return self.db.query(User).filter(User.id.in_(user_ids)).all()

    def create(self, user: User) -> User:
        self.db.add(user)
        self.db.flush()
        return user

    def update(self, user: User, **fields) -> User:
        for key, value in fields.items():
            setattr(user, key, value)
        self.db.flush()
        return user

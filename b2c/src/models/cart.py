import uuid

from sqlalchemy import CheckConstraint, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base, UUIDMixin, TimestampMixin


class Cart(UUIDMixin, TimestampMixin, Base):
    """Корзина

    ОднО из двух поелй задано:
    - `user_id` — для авторизованных (BUYER из JWT)
    - `session_id` — для гостей (X-Session-Id)

    В таблице соответственно либо user_id, либо session_id NOT NULL,
    но не оба сразу
    """

    __tablename__ = 'carts'
    __table_args__ = (
        CheckConstraint(
            '(user_id IS NOT NULL) OR (session_id IS NOT NULL)',
            name='cart_identity_present',
        ),
    )

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey('buyers.id'),
        index=True,
        unique=True,
        nullable=True,
    )
    session_id: Mapped[str | None] = mapped_column(
        String(64),
        index=True,
        unique=True,
        nullable=True,
    )
from sqlalchemy.orm import Mapped, mapped_column
from src.database import Base


class Seller(Base):
    __tablename__ = "sellers"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]

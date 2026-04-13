from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column
from src.database import Base

class SKUCharacteristic(Base):
    __tablename__ = "sku_characteristics"

    id: Mapped[int] = mapped_column(primary_key=True)
    sku_id: Mapped[int] = mapped_column(ForeignKey("skus.id"))
    name: Mapped[str] = mapped_column(String(100))
    value: Mapped[str] = mapped_column(String(500))
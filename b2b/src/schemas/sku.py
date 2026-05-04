from pydantic import BaseModel
from typing import List, Optional
from b2b.src.schemas.product import CharacteristicResponse
 
class SKUCreate(BaseModel):
    product_id: int
    name: str
    price: int
    characteristics: List[CharacteristicResponse] = []
 
class SKUUpdate(BaseModel):
    id: int
    name: Optional[str] = None
    price: Optional[int] = None
    active_quantity: Optional[int] = None
from pydantic import BaseModel, ConfigDict, Field
 
class CharacteristicValue(BaseModel):
    name: str = Field(..., examples=["Бренд"])
    value: str = Field(..., examples=["Apple"])
    model_config = ConfigDict(from_attributes=True)
 
class Image(BaseModel):
    url: str
    ordering: int = 0
    model_config = ConfigDict(from_attributes=True)
 
class CategoryRef(BaseModel):
    id: int
    name: str
    model_config = ConfigDict(from_attributes=True)
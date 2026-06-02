from pydantic import BaseModel, ConfigDict, Field
from uuid import UUID


class Characteristic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    name: str
    value: str


class CharacteristicResponse(Characteristic):
    id: UUID

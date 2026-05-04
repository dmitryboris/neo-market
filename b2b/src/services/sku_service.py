from sqlalchemy.ext.asyncio import AsyncSession
from b2b.src.models.sku import SKU, SKUCharacteristic
from b2b.src.schemas.sku import SKUCreate, SKUUpdate
 
async def create_sku(db: AsyncSession, data: SKUCreate) -> SKU:
    sku = SKU(
        product_id=data.product_id,
        name=data.name,
        price=data.price,
    )
    db.add(sku)
    await db.flush()
    for char in data.characteristics:
        db.add(SKUCharacteristic(sku_id=sku.id, name=char.name, value=char.value))
    await db.commit()
    await db.refresh(sku)
    return sku
 
async def update_sku(db: AsyncSession, sku_id: int, data: SKUUpdate) -> SKU | None:
    sku = await db.get(SKU, sku_id)
    if not sku:
        return None
    update_data = data.model_dump(exclude_unset=True, exclude={"id"})
    for key, value in update_data.items():
        setattr(sku, key, value)
    await db.commit()
    await db.refresh(sku)
    return sku
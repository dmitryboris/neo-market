from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from b2b.src.models.product import Product, ProductImage, ProductCharacteristic
from b2b.src.schemas.product import ProductCreate, ProductUpdate
 
async def create_product(db: AsyncSession, seller_id: int, data: ProductCreate) -> Product:
    product = Product(
        title=data.title,
        description=data.description,
        category_id=data.category_id,
        seller_id=seller_id,
    )
    db.add(product)
    await db.flush()
 
    for img_url in data.images:
        db.add(ProductImage(product_id=product.id, url=img_url, ordering=0))
    for char in data.characteristics:
        db.add(ProductCharacteristic(product_id=product.id, name=char.name, value=char.value))
 
    await db.commit()
    await db.refresh(product)
    return product
 
async def get_product(db: AsyncSession, product_id: int) -> Product | None:
    result = await db.execute(
        select(Product)
        .options(
            selectinload(Product.category),
            selectinload(Product.images),
            selectinload(Product.characteristics),
            selectinload(Product.skus).selectinload(SKU.characteristics),
        )
        .where(Product.id == product_id)
    )
    return result.scalar_one_or_none()
 
async def update_product(db: AsyncSession, product_id: int, data: ProductUpdate) -> Product | None:
    product = await get_product(db, product_id)
    if not product:
        return None
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(product, key, value)
    await db.commit()
    await db.refresh(product)
    return product
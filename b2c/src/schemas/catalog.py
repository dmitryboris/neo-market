from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class CatalogFilterSchema(BaseModel):
    model_config = ConfigDict(extra='forbid')

    category_id: UUID | None = None
    price_min: int | None = Field(default=None, ge=0, description='Минимальная цена в копейках')
    price_max: int | None = Field(default=None, ge=0, description='Максимальная цена в копейках')
    seller_id: UUID | None = None
    attributes: dict[str, str | list[str]] = Field(
        default_factory=dict,
        description='Динамические атрибуты, например color=red, size=[M, L]',
    )

    def is_empty(self) -> bool:
        """True, если ни один фильтр не задан"""
        return (
                self.category_id is None
                and self.price_min is None
                and self.price_max is None
                and self.seller_id is None
                and not self.attributes
        )


class CategoryRefSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    parent_id: UUID | None = None
    level: int = Field(ge=0)
    path: list[str] = Field(default_factory=list, description='breadcramps')


class ImageRefSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    url: str
    alt: str | None = None
    ordering: int = Field(ge=0)
    is_main: bool | None = None


class SellerRefSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID | None = None
    display_name: str | None = None


class CatalogProductCardSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    slug: str | None = None
    category: CategoryRefSchema | None = None
    min_price: int = Field(description='Минимальная цена среди доступных SKU, копейки')
    old_price: int | None = Field(default=None, description='Старая цена (для зачёркивания), копейки')
    has_stock: bool
    rating: float | None = Field(default=None, ge=0, le=5)
    reviews_count: int | None = Field(default=None, ge=0)
    images: list[ImageRefSchema] = Field(default_factory=list)
    seller: SellerRefSchema | None = None


class CatalogPaginatedResponseSchema(BaseModel):
    items: list[CatalogProductCardSchema] = Field(default_factory=list)
    total_count: int
    limit: int
    offset: int


class CatalogFacetValueSchema(BaseModel):
    value: str
    count: int


class CatalogFacetSchema(BaseModel):
    name: str
    values: list[CatalogFacetValueSchema] = Field(default_factory=list)


class CatalogFacetsResponseSchema(BaseModel):
    category_id: UUID | None = None
    facets: list[CatalogFacetSchema] = Field(default_factory=list)


class CatalogProductDetailImageSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra='ignore')

    id: UUID
    url: str
    ordering: int = 0


class CatalogProductDetailCharacteristicSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra='ignore')

    name: str
    value: str


class CatalogProductDetailSkuSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra='ignore')

    id: UUID
    name: str
    price: int = Field(description='Цена в копейках')
    discount: int = Field(default=0, description='Скидка в копейках (0 если нет)')
    image: str | None = None
    available_quantity: int = Field(default=0, description='Остаток за вычетом резерва')
    in_stock: bool = True
    characteristics: list[CatalogProductDetailCharacteristicSchema] = Field(default_factory=list)


class CatalogProductDetailResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra='ignore')

    id: UUID
    slug: str | None = None
    name: str
    description: str
    status: str | None = None
    min_price: int = Field(default=0, description='Минимальная цена среди SKU с остатком, копейки')
    has_stock: bool = False
    images: list[CatalogProductDetailImageSchema] = Field(default_factory=list)
    characteristics: list[CatalogProductDetailCharacteristicSchema] = Field(default_factory=list)
    skus: list[CatalogProductDetailSkuSchema] = Field(default_factory=list)


class CategoryResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    slug: str
    parent_id: UUID | None
    ordering: int
    created_at: datetime
    updated_at: datetime


class CategoryTreeNodeSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    slug: str
    parent_id: UUID | None
    ordering: int
    level: int
    path: list[str]
    children: list['CategoryTreeNodeSchema'] = Field(default_factory=list)


class CategoryTreeResponseSchema(BaseModel):
    items: list[CategoryTreeNodeSchema]


class CategoryBreadcrumbNodeSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    slug: str
    level: int
    is_current: bool


class BreadcrumbsResponseSchema(BaseModel):
    data: list[CategoryBreadcrumbNodeSchema]
    meta: dict[str, str]


# ----- Фильтры категории ???-----
class CategoryFilterItemSchema(BaseModel):
    slug: str
    name: str
    type: str
    value: list[str] | None = None
    min: int | None = None
    max: int | None = None


class CategoryFiltersResponseSchema(BaseModel):
    items: list[CategoryFilterItemSchema]

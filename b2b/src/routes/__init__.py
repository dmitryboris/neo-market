from .auth_router import auth_router
from .category_router import category_router
from .invoice_router import invoice_router
# from .upload_router import upload_router
from .seller_router import seller_router
from .product_router import product_router
from .sku_router import sku_router
from .public_router import public_router
from .moderation_router import moderation_router
from .inventory_router import inventory_router

routers = [
    auth_router,
    seller_router,
    category_router,
    invoice_router,
#    upload_router,
    product_router,
    sku_router,
    public_router,
    moderation_router,
    inventory_router,
]

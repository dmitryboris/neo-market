from .auth_router import auth_router
from .category_router import category_router
from .invoice_router import invoice_router
from .upload_router import upload_router
from .seller_router import seller_router
from .product_router import product_router

routers = [
    auth_router,
    seller_router,
    category_router,
    invoice_router,
    upload_router,
    product_router
]

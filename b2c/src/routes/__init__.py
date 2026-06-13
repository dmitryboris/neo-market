from .auth_router import auth_router
from .cart_router import cart_router
from .buyer_router import buyer_router
from .catalog_router import catalog_router
from .orders_router import orders_router

routers = [
    auth_router,
    buyer_router,
    catalog_router,
    cart_router,
    orders_router
]

from .auth_router import auth_router
from .buyer_router import buyer_router
from .catalog_router import catalog_router

routers = [
    auth_router,
    buyer_router,
    catalog_router,
]

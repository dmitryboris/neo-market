from .auth_router import auth_router
from .moderator_router import moderator_router
from .ticket_router import ticket_router

routers = [
    auth_router,
    moderator_router,
    ticket_router,
]
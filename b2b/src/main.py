from contextlib import asynccontextmanager
from fastapi import FastAPI
from alembic.config import Config
from alembic import command
import uvicorn

from src.routes.category_router import category_router
from src.routes.invoice_router import invoice_router
from src.routes.upload_router import upload_router
from src.routes.auth_router import auth_router
from src.routes.seller_router import seller_router
from src.routes.product_router import product_router

def run_migrations():
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")


@asynccontextmanager
async def lifespan(app: FastAPI):
    #run_migrations()
    yield


app = FastAPI(lifespan=lifespan)
app.include_router(category_router)
app.include_router(invoice_router)
app.include_router(upload_router)
app.include_router(auth_router)
app.include_router(seller_router)
app.include_router(product_router)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

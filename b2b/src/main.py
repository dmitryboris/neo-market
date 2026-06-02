from contextlib import asynccontextmanager
from fastapi import FastAPI
from alembic.config import Config
from alembic import command
import uvicorn

from src.routes import routers


def run_migrations():
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")


@asynccontextmanager
async def lifespan(app: FastAPI):
    run_migrations()
    yield


app = FastAPI(lifespan=lifespan)

for router in routers:
    app.include_router(router, prefix='/api/v1')

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

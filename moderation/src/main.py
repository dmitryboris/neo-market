from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.exceptions import HTTPException, RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from alembic.config import Config
from alembic import command
import uvicorn

from src.routes import routers
from shared.exception_handlers import (
    http_exception_handler, validation_exception_handler,
    domain_exception_handler, unhandled_exception_handler
)
from shared.exceptions import DomainException


def run_migrations():
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")


@asynccontextmanager
async def lifespan(app: FastAPI):
    run_migrations()
    yield


app = FastAPI(lifespan=lifespan)

app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(DomainException, domain_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

for router in routers:
    app.include_router(router, prefix='/api/v1')

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

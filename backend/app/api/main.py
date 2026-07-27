from fastapi import APIRouter

from app.api.routes import docs, items, login, private, users, utils
from app.core.config import settings
from app.modules.api import router as modules_router
from app.modules.iam.router import router as iam_router
from app.modules.inventory.router import router as inventory_router
from app.modules.scheduler.router import router as scheduler_router

api_router = APIRouter()
api_router.include_router(login.router)
api_router.include_router(users.router)
api_router.include_router(docs.router)
api_router.include_router(utils.router)
api_router.include_router(items.router)
api_router.include_router(inventory_router)
api_router.include_router(iam_router)
api_router.include_router(scheduler_router)
api_router.include_router(modules_router)


if settings.ENVIRONMENT == "local":
    api_router.include_router(private.router)

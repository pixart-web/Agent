from fastapi import APIRouter

from app.api.routes import agents, auth, commands, health, plans, supervisor, tasks

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router, prefix="/api/v1")
api_router.include_router(agents.router, prefix="/api/v1")
api_router.include_router(commands.router, prefix="/api/v1")
api_router.include_router(plans.router, prefix="/api/v1")
api_router.include_router(supervisor.router, prefix="/api/v1")
api_router.include_router(tasks.router, prefix="/api/v1")

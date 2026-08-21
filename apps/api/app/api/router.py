from fastapi import APIRouter

from app.api.routes import (
    agents,
    auth,
    commands,
    execution,
    health,
    integrations,
    plans,
    specialized_agents,
    supervisor,
    tasks,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router, prefix="/api/v1")
api_router.include_router(agents.router, prefix="/api/v1")
api_router.include_router(commands.router, prefix="/api/v1")
api_router.include_router(plans.router, prefix="/api/v1")
api_router.include_router(supervisor.router, prefix="/api/v1")
api_router.include_router(tasks.router, prefix="/api/v1")
api_router.include_router(execution.router, prefix="/api/v1")
api_router.include_router(specialized_agents.router, prefix="/api/v1")
api_router.include_router(integrations.router, prefix="/api/v1")

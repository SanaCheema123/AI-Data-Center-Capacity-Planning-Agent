from fastapi import APIRouter
from app.api.v1.routes import ai, alerts, auth, dashboard, data_centers, data_sources, forecasts, health, procurement, reports, scenarios, settings
from app.api.v1.routes.resource_forecasts import gpu_router, power_router, storage_router, network_router

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(data_centers.router, prefix="/data-centers", tags=["data-centers"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(forecasts.router, prefix="/forecasts", tags=["forecasts"])
api_router.include_router(gpu_router, prefix="/gpu", tags=["gpu"])
api_router.include_router(power_router, prefix="/power", tags=["power"])
api_router.include_router(storage_router, prefix="/storage", tags=["storage"])
api_router.include_router(network_router, prefix="/network", tags=["network"])
api_router.include_router(scenarios.router, prefix="/scenarios", tags=["scenarios"])
api_router.include_router(procurement.router, prefix="/procurement", tags=["procurement"])
api_router.include_router(alerts.router, prefix="/alerts", tags=["alerts"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
api_router.include_router(data_sources.router, prefix="/data-sources", tags=["data-sources"])
api_router.include_router(settings.router, prefix="/settings", tags=["settings"])
api_router.include_router(ai.router, prefix="/ai", tags=["ai"])

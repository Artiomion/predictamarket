from fastapi import APIRouter
from fastapi.responses import JSONResponse

from shared.health import check_health

router = APIRouter()


@router.get("/health")
async def health() -> JSONResponse:
    result = await check_health()
    result["service"] = "portfolio-service"
    code = 200 if result["status"] == "ok" else 503
    return JSONResponse(content=result, status_code=code)

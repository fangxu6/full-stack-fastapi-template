from fastapi import APIRouter

router = APIRouter(prefix="/modules", tags=["modules"])


@router.get("/health-check/")
def modules_health_check() -> dict[str, str]:
    return {"message": "Modules router ready"}

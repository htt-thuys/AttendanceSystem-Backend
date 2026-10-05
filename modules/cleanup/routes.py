from fastapi import APIRouter, Depends

from api.deps import require_roles
from modules.cleanup import service
from modules.admin.schemas import CleanupRunResponse

router = APIRouter()


@router.post("/cleanup/run", response_model=CleanupRunResponse)
async def run_cleanup_now(_current_user=Depends(require_roles("admin"))):
    return await service.run_manual_cleanup()

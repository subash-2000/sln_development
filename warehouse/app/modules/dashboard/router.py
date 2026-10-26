from fastapi import APIRouter, Depends

from app.core.database import get_db
from app.core.dependencies import get_current_tenant_context, require_permission, TenantContext
from app.core.response import StandardResponse, success_response
from app.modules.dashboard.schemas import DashboardSummary
from app.modules.dashboard.service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

def _service(db=Depends(get_db)):
    return DashboardService(db)

@router.get(
    "/summary",
    response_model=StandardResponse[DashboardSummary],
    dependencies=[Depends(require_permission("dashboard.view"))]
)
async def get_dashboard_summary(
    context: TenantContext = Depends(get_current_tenant_context),
    service: DashboardService = Depends(_service)
):
    """
    Get consolidated dashboard metrics for the current company.
    Includes inventory, operations, financials, and alerts.
    """
    company_id = context.company_id
    
    summary = await service.get_dashboard_summary(company_id=company_id)
    
    return success_response(
        data=summary,
        message="Dashboard summary retrieved successfully"
    )

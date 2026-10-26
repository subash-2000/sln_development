import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_permission
from app.core.pagination import PaginationParams, build_pagination_metadata
from app.core.response import StandardResponse, success_response
from app.models.user import User
from app.modules.audit.repository import AuditLogRepository
from app.modules.audit.schemas import AuditLogResponse

router = APIRouter(prefix="/audit-logs", tags=["Audit Trail"])


@router.get(
    "",
    response_model=StandardResponse[list[AuditLogResponse]],
    status_code=status.HTTP_200_OK,
    summary="Query System Audit Logs",
    description="Returns an auditable log of entity mutations, status changes, and administrative actions.",
)
async def list_audit_logs(
    pagination: PaginationParams = Depends(),
    module: str | None = Query(
        None, description="Filter by module (e.g. 'users', 'roles', 'inventory')"
    ),
    entity_name: str | None = Query(
        None, description="Filter by entity name (e.g. 'User', 'Role')"
    ),
    entity_id: str | None = Query(None, description="Filter by entity ID"),
    action: str | None = Query(None, description="Filter by action (CREATE, UPDATE, DELETE, etc.)"),
    user_id: uuid.UUID | None = Query(None, description="Filter by actor user ID"),
    company_id: uuid.UUID | None = Query(None, description="Filter by company scope"),
    current_user: User = Depends(require_permission("system.audit.read")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    repo = AuditLogRepository(db)
    logs, total = await repo.list_audit_logs(
        offset=pagination.offset,
        limit=pagination.limit,
        module=module,
        entity_name=entity_name,
        entity_id=entity_id,
        action=action,
        user_id=user_id,
        company_id=company_id,
    )
    meta = build_pagination_metadata(total, pagination)
    return success_response(
        data=[
            AuditLogResponse(
                id=log.id,
                timestamp=log.timestamp,
                user_id=log.user_id,
                company_id=log.company_id,
                branch_id=log.branch_id,
                module=log.module,
                entity_name=log.entity_name,
                entity_id=log.entity_id,
                action=log.action,
                old_values=log.old_values,
                new_values=log.new_values,
                ip_address=log.ip_address,
                request_id=log.request_id,
            ).model_dump()
            for log in logs
        ],
        message="Audit logs retrieved successfully",
        pagination=meta,
    )

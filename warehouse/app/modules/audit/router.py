import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_permission
from app.core.exceptions import NotFoundException
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
        data=[AuditLogResponse(**log).model_dump() for log in logs],
        message="Audit logs retrieved successfully",
        pagination=meta,
    )


@router.get(
    "/entity/{entity_name}/{entity_id}",
    response_model=StandardResponse[list[AuditLogResponse]],
    status_code=status.HTTP_200_OK,
    summary="Get Audit History for Entity",
    description="Returns chronological audit entries and field mutations for a specific record.",
)
async def get_entity_audit_trail(
    entity_name: str,
    entity_id: str,
    module: str | None = Query(None, description="Filter by module"),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(require_permission("system.audit.read")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    repo = AuditLogRepository(db)
    logs = await repo.get_entity_history(
        entity_name=entity_name,
        entity_id=entity_id,
        module=module,
        limit=limit,
    )
    return success_response(
        data=[AuditLogResponse(**log).model_dump() for log in logs],
        message=f"Audit history for {entity_name} retrieved successfully",
    )


@router.get(
    "/{log_id}",
    response_model=StandardResponse[AuditLogResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Audit Log Detail",
    description="Returns detailed single audit event including old and new value snapshots.",
)
async def get_audit_log(
    log_id: uuid.UUID,
    current_user: User = Depends(require_permission("system.audit.read")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    repo = AuditLogRepository(db)
    log = await repo.get_by_id(log_id)
    if not log:
        raise NotFoundException(
            f"Audit log entry with ID '{log_id}' not found",
            error_code="AUDIT_LOG_NOT_FOUND",
        )
    return success_response(
        data=AuditLogResponse(**log).model_dump(),
        message="Audit log retrieved successfully",
    )

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import correlation_id_ctx, logger, user_id_ctx
from app.models.audit import AuditLog


async def log_audit(
    db: AsyncSession,
    action: str,
    module: str,
    entity_name: str,
    entity_id: str,
    old_values: dict[str, Any] | None = None,
    new_values: dict[str, Any] | None = None,
    user_id: uuid.UUID | None = None,
    company_id: uuid.UUID | None = None,
    branch_id: uuid.UUID | None = None,
    ip_address: str | None = None,
    request_id: str | None = None,
) -> AuditLog:
    """Record an immutable audit trail entry for critical state changes and administrative events."""
    effective_request_id = request_id or correlation_id_ctx.get()

    resolved_user_id = user_id
    if not resolved_user_id:
        ctx_user_str = user_id_ctx.get()
        if ctx_user_str:
            import contextlib

            with contextlib.suppress(ValueError):
                resolved_user_id = uuid.UUID(ctx_user_str)

    audit_entry = AuditLog(
        id=uuid.uuid4(),
        timestamp=datetime.now(UTC),
        user_id=resolved_user_id,
        company_id=company_id,
        branch_id=branch_id,
        module=module,
        entity_name=entity_name,
        entity_id=str(entity_id),
        action=action,
        old_values=old_values,
        new_values=new_values,
        ip_address=ip_address,
        request_id=effective_request_id,
    )

    db.add(audit_entry)
    # Flushed into active transaction so it commits atomically with the business mutation
    await db.flush()
    logger.info(f"Audit log recorded: {action} on {entity_name}:{entity_id} in {module}")
    return audit_entry

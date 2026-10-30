import contextlib
import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel
from sqlalchemy import event, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.core.logging import correlation_id_ctx, logger, user_id_ctx
from app.models.audit import AuditLog
from app.models.base import BaseEntity


class AuditFieldsMixin(BaseModel):
    """Standardized audit fields mixin for responses across all modules."""

    created_at: datetime | None = None
    updated_at: datetime | None = None
    created_by_id: uuid.UUID | None = None
    updated_by_id: uuid.UUID | None = None
    created_by: str | None = None
    updated_by: str | None = None


async def resolve_user_names(
    db: AsyncSession, *user_ids: uuid.UUID | None
) -> dict[uuid.UUID, str]:
    """Efficiently resolve human-readable user names for a batch of user IDs."""
    from app.models.user import User

    valid_ids = {uid for uid in user_ids if uid is not None}
    if not valid_ids:
        return {}

    stmt = select(User.id, User.full_name, User.username).where(User.id.in_(valid_ids))
    res = await db.execute(stmt)
    return {row[0]: (row[1] or row[2]) for row in res.all()}


async def get_audit_names(
    db: AsyncSession,
    created_by_id: uuid.UUID | None,
    updated_by_id: uuid.UUID | None = None,
) -> tuple[str | None, str | None]:
    """Helper to retrieve creator and updater display names in one query."""
    names = await resolve_user_names(db, created_by_id, updated_by_id)
    creator_name = names.get(created_by_id) if created_by_id else None
    updater_name = names.get(updated_by_id) if updated_by_id else None
    return creator_name, updater_name


@event.listens_for(Session, "before_flush")
def audit_before_flush_listener(session: Session, flush_context: Any, instances: Any) -> None:
    """SQLAlchemy hook that automatically stamps created_by_id and updated_by_id on all BaseEntity instances."""
    user_id_str = user_id_ctx.get()
    user_uuid: uuid.UUID | None = None
    if user_id_str:
        with contextlib.suppress(ValueError):
            user_uuid = uuid.UUID(user_id_str)

    if not user_uuid:
        return

    # Newly inserted entities
    for obj in session.new:
        if isinstance(obj, BaseEntity):
            if obj.created_by_id is None:
                obj.created_by_id = user_uuid
            if obj.updated_by_id is None:
                obj.updated_by_id = user_uuid

    # Updated/dirty entities
    for obj in session.dirty:
        if isinstance(obj, BaseEntity):
            obj.updated_by_id = user_uuid


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

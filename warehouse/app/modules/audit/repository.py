import uuid

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog


class AuditLogRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_audit_logs(
        self,
        offset: int = 0,
        limit: int = 50,
        module: str | None = None,
        entity_name: str | None = None,
        entity_id: str | None = None,
        action: str | None = None,
        user_id: uuid.UUID | None = None,
        company_id: uuid.UUID | None = None,
    ) -> tuple[list[AuditLog], int]:
        query = select(AuditLog)
        count_query = select(func.count(AuditLog.id))

        filters = []
        if module:
            filters.append(AuditLog.module == module.strip().lower())
        if entity_name:
            filters.append(AuditLog.entity_name == entity_name.strip())
        if entity_id:
            filters.append(AuditLog.entity_id == entity_id.strip())
        if action:
            filters.append(AuditLog.action == action.strip().upper())
        if user_id:
            filters.append(AuditLog.user_id == user_id)
        if company_id:
            filters.append(AuditLog.company_id == company_id)

        if filters:
            query = query.where(and_(*filters))
            count_query = count_query.where(and_(*filters))

        total_res = await self.db.execute(count_query)
        total = total_res.scalar() or 0

        query = query.order_by(AuditLog.timestamp.desc()).offset(offset).limit(limit)
        res = await self.db.execute(query)
        logs = list(res.scalars().all())

        return logs, total

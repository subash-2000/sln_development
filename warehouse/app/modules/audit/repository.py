import uuid
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog
from app.models.user import User


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
    ) -> tuple[list[dict[str, Any]], int]:
        query = select(
            AuditLog,
            User.full_name.label("user_full_name"),
            User.username.label("user_username"),
            User.email.label("user_email"),
        ).outerjoin(User, AuditLog.user_id == User.id)

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
        rows = res.all()

        results = []
        for log, full_name, username, email in rows:
            user_display = full_name or username
            results.append({
                "id": log.id,
                "timestamp": log.timestamp,
                "user_id": log.user_id,
                "user_name": user_display,
                "user_email": email,
                "company_id": log.company_id,
                "branch_id": log.branch_id,
                "module": log.module,
                "entity_name": log.entity_name,
                "entity_id": log.entity_id,
                "action": log.action,
                "old_values": log.old_values,
                "new_values": log.new_values,
                "ip_address": log.ip_address,
                "request_id": log.request_id,
            })

        return results, total

    async def get_by_id(self, log_id: uuid.UUID) -> dict[str, Any] | None:
        query = (
            select(
                AuditLog,
                User.full_name.label("user_full_name"),
                User.username.label("user_username"),
                User.email.label("user_email"),
            )
            .outerjoin(User, AuditLog.user_id == User.id)
            .where(AuditLog.id == log_id)
        )
        res = await self.db.execute(query)
        row = res.first()
        if not row:
            return None
        log, full_name, username, email = row
        return {
            "id": log.id,
            "timestamp": log.timestamp,
            "user_id": log.user_id,
            "user_name": full_name or username,
            "user_email": email,
            "company_id": log.company_id,
            "branch_id": log.branch_id,
            "module": log.module,
            "entity_name": log.entity_name,
            "entity_id": log.entity_id,
            "action": log.action,
            "old_values": log.old_values,
            "new_values": log.new_values,
            "ip_address": log.ip_address,
            "request_id": log.request_id,
        }

    async def get_entity_history(
        self,
        entity_name: str,
        entity_id: str,
        module: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        query = (
            select(
                AuditLog,
                User.full_name.label("user_full_name"),
                User.username.label("user_username"),
                User.email.label("user_email"),
            )
            .outerjoin(User, AuditLog.user_id == User.id)
            .where(
                AuditLog.entity_name == entity_name.strip(),
                AuditLog.entity_id == str(entity_id).strip(),
            )
        )
        if module:
            query = query.where(AuditLog.module == module.strip().lower())
        query = query.order_by(AuditLog.timestamp.desc()).limit(limit)
        res = await self.db.execute(query)
        rows = res.all()
        return [
            {
                "id": log.id,
                "timestamp": log.timestamp,
                "user_id": log.user_id,
                "user_name": full_name or username,
                "user_email": email,
                "company_id": log.company_id,
                "branch_id": log.branch_id,
                "module": log.module,
                "entity_name": log.entity_name,
                "entity_id": log.entity_id,
                "action": log.action,
                "old_values": log.old_values,
                "new_values": log.new_values,
                "ip_address": log.ip_address,
                "request_id": log.request_id,
            }
            for log, full_name, username, email in rows
        ]

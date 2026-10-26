import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class AuditLogResponse(BaseModel):
    id: uuid.UUID
    timestamp: datetime
    user_id: uuid.UUID | None = None
    company_id: uuid.UUID | None = None
    branch_id: uuid.UUID | None = None
    module: str
    entity_name: str
    entity_id: str
    action: str
    old_values: dict[str, Any] | None = None
    new_values: dict[str, Any] | None = None
    ip_address: str | None = None
    request_id: str | None = None

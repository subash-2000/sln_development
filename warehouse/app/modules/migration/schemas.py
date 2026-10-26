from datetime import datetime
from typing import List, Optional, Any, Dict
from uuid import UUID
from pydantic import BaseModel

class ImportBatchBase(BaseModel):
    import_type: str
    filename: Optional[str] = None
    column_mapping: Optional[Dict[str, str]] = None

class ImportBatchCreate(ImportBatchBase):
    pass

class ImportLogResponse(BaseModel):
    row_number: Optional[int]
    record_identifier: Optional[str]
    status: str
    error_details: Optional[Any]

    class Config:
        from_attributes = True

class ImportBatchResponse(ImportBatchBase):
    id: UUID
    company_id: UUID
    status: str
    total_records: int
    success_count: int
    failed_count: int
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    error_message: Optional[str]
    
    class Config:
        from_attributes = True

class ImportBatchDetailResponse(ImportBatchResponse):
    logs: List[ImportLogResponse]

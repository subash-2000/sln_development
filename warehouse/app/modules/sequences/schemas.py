import uuid

from pydantic import BaseModel, Field


class SequenceCreateRequest(BaseModel):
    document_type: str = Field(
        ...,
        min_length=2,
        max_length=50,
        description="Document type identifier (e.g. 'INVOICE', 'DISPATCH')",
    )
    prefix: str = Field("", max_length=20, description="Document prefix string")
    suffix: str = Field("", max_length=20, description="Document suffix string")
    current_value: int = Field(0, ge=0, description="Starting sequence counter value")
    padding: int = Field(5, ge=1, le=12, description="Zero-padding length")
    year: int | None = Field(None, description="Optional year scope")
    month: int | None = Field(None, ge=1, le=12, description="Optional month scope")
    company_id: uuid.UUID | None = Field(None, description="Company tenant scope")
    branch_id: uuid.UUID | None = Field(None, description="Branch tenant scope")


class SequenceUpdateRequest(BaseModel):
    prefix: str | None = Field(None, max_length=20)
    suffix: str | None = Field(None, max_length=20)
    padding: int | None = Field(None, ge=1, le=12)
    is_active: bool | None = None


class SequenceResponse(BaseModel):
    id: uuid.UUID
    document_type: str
    prefix: str
    suffix: str
    current_value: int
    padding: int
    year: int | None = None
    month: int | None = None
    company_id: uuid.UUID | None = None
    branch_id: uuid.UUID | None = None
    is_active: bool

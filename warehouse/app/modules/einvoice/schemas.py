from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ConfigurationUpdate(BaseModel):
    enabled: bool = False
    ewaybill_enabled: bool = False
    auto_generate: bool = False
    environment: str = "sandbox"
    provider: str = "mygstcafe"
    gstin: str | None = None
    asp_gstin: str | None = None
    api_username: str | None = None
    api_password: str | None = None
    customer_id: str | None = None
    api_id: str | None = None
    api_secret: str | None = None
    client_id: str | None = None
    client_secret: str | None = None
    auth_token: str | None = None

    @field_validator("environment")
    @classmethod
    def environment_allowed(cls, value: str) -> str:
        if value not in {"sandbox", "production"}:
            raise ValueError("environment must be sandbox or production")
        return value

    @field_validator("provider")
    @classmethod
    def provider_allowed(cls, value: str) -> str:
        if value not in {"mygstcafe", "nic_direct"}:
            raise ValueError("provider must be mygstcafe or nic_direct")
        return value


class ConfigurationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID | None = None
    company_id: UUID
    enabled: bool = False
    ewaybill_enabled: bool = False
    auto_generate: bool = False
    environment: str = "sandbox"
    provider: str = "mygstcafe"
    gstin: str | None = None
    asp_gstin: str | None = None
    api_username: str | None = None
    has_api_password: bool = False
    customer_id: str | None = None
    api_id: str | None = None
    has_api_secret: bool = False
    client_id: str | None = None
    has_client_secret: bool = False
    has_auth_token: bool = False


class DocumentCreate(BaseModel):
    invoice_id: UUID | None = None
    dispatch_order_id: UUID | None = None
    document_type: str = "E_INVOICE"
    distance_km: int | None = Field(None, ge=0, le=4000)
    transporter_id: str | None = Field(None, max_length=30)
    transport_mode: str | None = "1"
    vehicle_number: str | None = Field(None, max_length=30)
    vehicle_type: str | None = "R"
    payload_override: dict | None = None


class CancellationRequest(BaseModel):
    reason: str = Field(..., min_length=1, max_length=10)
    remarks: str = Field(..., min_length=1, max_length=200)


class VehicleUpdateRequest(BaseModel):
    vehicle_number: str = Field(..., min_length=4, max_length=30)
    transport_mode: str = "1"
    vehicle_type: str = "R"
    reason_code: str = "1"
    reason_remarks: str = Field(default="Vehicle updated", max_length=200)


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    company_id: UUID
    invoice_id: UUID | None = None
    dispatch_order_id: UUID | None = None
    document_type: str
    document_number: str
    status: str
    irn: str | None = None
    acknowledgement_number: str | None = None
    acknowledgement_date: datetime | None = None
    signed_qr_code: str | None = None
    ewaybill_number: str | None = None
    ewaybill_date: datetime | None = None
    ewaybill_valid_until: datetime | None = None
    distance_km: int | None = None
    transporter_id: str | None = None
    transport_mode: str | None = None
    vehicle_number: str | None = None
    vehicle_type: str | None = None
    request_payload: dict | None = None
    response_payload: dict | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime


class ApiLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    document_id: UUID | None = None
    operation: str
    endpoint: str
    http_status: int | None = None
    success: bool
    duration_ms: int | None = None
    error_message: str | None = None
    created_at: datetime

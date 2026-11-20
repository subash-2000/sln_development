import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import TenantContext, get_current_tenant_context, require_permission
from app.core.exceptions import BadRequestException
from app.core.pagination import PaginationParams, build_pagination_metadata
from app.core.response import StandardResponse, success_response
from app.models.einvoice import EInvoiceApiLog
from app.models.user import User
from app.modules.einvoice.schemas import (
    ApiLogResponse, CancellationRequest, ConfigurationResponse, ConfigurationUpdate,
    DocumentCreate, DocumentResponse, VehicleUpdateRequest,
)
from app.modules.einvoice.service import EInvoiceService

router = APIRouter(prefix="/einvoice", tags=["E-Invoice & E-Way Bill"])


def company(context: TenantContext) -> uuid.UUID:
    if not context.company_id:
        raise BadRequestException("Company ID is required in tenant context")
    return context.company_id


@router.get("/configuration", response_model=StandardResponse[ConfigurationResponse])
async def get_configuration(context: TenantContext = Depends(get_current_tenant_context), _: User = Depends(require_permission("invoicing.read")), db: AsyncSession = Depends(get_db)):
    result = await EInvoiceService(db).get_configuration(company(context))
    return success_response(data=result.model_dump(mode="json"))


@router.put("/configuration", response_model=StandardResponse[ConfigurationResponse])
async def save_configuration(payload: ConfigurationUpdate, context: TenantContext = Depends(get_current_tenant_context), user: User = Depends(require_permission("invoicing.write")), db: AsyncSession = Depends(get_db)):
    result = await EInvoiceService(db).save_configuration(company(context), user.id, payload)
    return success_response(data=result.model_dump(mode="json"), message="E-invoice configuration saved")


@router.post("/documents", response_model=StandardResponse[DocumentResponse], status_code=status.HTTP_201_CREATED)
async def create_document(payload: DocumentCreate, context: TenantContext = Depends(get_current_tenant_context), user: User = Depends(require_permission("invoicing.write")), db: AsyncSession = Depends(get_db)):
    result = await EInvoiceService(db).create_document(company(context), user.id, payload)
    return success_response(data=DocumentResponse.model_validate(result).model_dump(mode="json"), message="Statutory document prepared")


@router.get("/documents", response_model=StandardResponse[list[DocumentResponse]])
async def list_documents(status_filter: str | None = Query(None, alias="status"), pagination: PaginationParams = Depends(), context: TenantContext = Depends(get_current_tenant_context), _: User = Depends(require_permission("invoicing.read")), db: AsyncSession = Depends(get_db)):
    rows, total = await EInvoiceService(db).list_documents(company(context), pagination.offset, pagination.limit, status_filter)
    return success_response(data=[DocumentResponse.model_validate(x).model_dump(mode="json") for x in rows], pagination=build_pagination_metadata(total, pagination))


@router.get("/documents/{document_id}", response_model=StandardResponse[DocumentResponse])
async def get_document(document_id: uuid.UUID, context: TenantContext = Depends(get_current_tenant_context), _: User = Depends(require_permission("invoicing.read")), db: AsyncSession = Depends(get_db)):
    result = await EInvoiceService(db).get_document(document_id, company(context))
    return success_response(data=DocumentResponse.model_validate(result).model_dump(mode="json"))


@router.post("/documents/{document_id}/generate-irn", response_model=StandardResponse[DocumentResponse])
async def generate_irn(document_id: uuid.UUID, context: TenantContext = Depends(get_current_tenant_context), _: User = Depends(require_permission("invoicing.post")), db: AsyncSession = Depends(get_db)):
    result = await EInvoiceService(db).execute(document_id, company(context), "generate_einvoice")
    return success_response(data=DocumentResponse.model_validate(result).model_dump(mode="json"), message="IRN generated")


@router.post("/documents/{document_id}/cancel-irn", response_model=StandardResponse[DocumentResponse])
async def cancel_irn(document_id: uuid.UUID, payload: CancellationRequest, context: TenantContext = Depends(get_current_tenant_context), _: User = Depends(require_permission("invoicing.post")), db: AsyncSession = Depends(get_db)):
    result = await EInvoiceService(db).execute(document_id, company(context), "cancel_einvoice", payload.model_dump())
    return success_response(data=DocumentResponse.model_validate(result).model_dump(mode="json"), message="IRN cancelled")


@router.post("/documents/{document_id}/generate-ewaybill", response_model=StandardResponse[DocumentResponse])
async def generate_ewaybill(document_id: uuid.UUID, context: TenantContext = Depends(get_current_tenant_context), _: User = Depends(require_permission("invoicing.post")), db: AsyncSession = Depends(get_db)):
    result = await EInvoiceService(db).execute(document_id, company(context), "generate_ewaybill")
    return success_response(data=DocumentResponse.model_validate(result).model_dump(mode="json"), message="E-way bill generated")


@router.post("/documents/{document_id}/cancel-ewaybill", response_model=StandardResponse[DocumentResponse])
async def cancel_ewaybill(document_id: uuid.UUID, payload: CancellationRequest, context: TenantContext = Depends(get_current_tenant_context), _: User = Depends(require_permission("invoicing.post")), db: AsyncSession = Depends(get_db)):
    result = await EInvoiceService(db).execute(document_id, company(context), "cancel_ewaybill", payload.model_dump())
    return success_response(data=DocumentResponse.model_validate(result).model_dump(mode="json"), message="E-way bill cancelled")


@router.post("/documents/{document_id}/update-vehicle", response_model=StandardResponse[DocumentResponse])
async def update_vehicle(document_id: uuid.UUID, payload: VehicleUpdateRequest, context: TenantContext = Depends(get_current_tenant_context), _: User = Depends(require_permission("invoicing.post")), db: AsyncSession = Depends(get_db)):
    result = await EInvoiceService(db).execute(document_id, company(context), "update_vehicle", payload.model_dump())
    return success_response(data=DocumentResponse.model_validate(result).model_dump(mode="json"), message="Vehicle updated")


@router.get("/logs", response_model=StandardResponse[list[ApiLogResponse]])
async def list_logs(pagination: PaginationParams = Depends(), context: TenantContext = Depends(get_current_tenant_context), _: User = Depends(require_permission("invoicing.read")), db: AsyncSession = Depends(get_db)):
    cid = company(context)
    total = (await db.execute(select(func.count()).select_from(EInvoiceApiLog).where(EInvoiceApiLog.company_id == cid))).scalar_one()
    rows = (await db.execute(select(EInvoiceApiLog).where(EInvoiceApiLog.company_id == cid).order_by(EInvoiceApiLog.created_at.desc()).offset(pagination.offset).limit(pagination.limit))).scalars().all()
    return success_response(data=[ApiLogResponse.model_validate(x).model_dump(mode="json") for x in rows], pagination=build_pagination_metadata(total, pagination))

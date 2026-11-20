import uuid
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from pathlib import Path
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.constants import RingsDocumentType
from app.core.database import get_db
from app.core.dependencies import TenantContext, get_current_tenant_context, require_permission
from app.core.exceptions import BadRequestException, ConflictException, NotFoundException, ValidationException
from app.core.pagination import PaginationParams, build_pagination_metadata
from app.core.response import StandardResponse, success_response
from app.models.customer import Customer
from app.models.rings import RingsDocument
from app.models.sales_tax_tracking import SalesTaxInvoiceTracking
from app.models.user import User
from app.core.config import settings

router = APIRouter(prefix="/sales-tax-invoices", tags=["Sales Tax Invoice Tracking"])

class TrackingCreate(BaseModel):
    customer_id: uuid.UUID
    delivery_challan_id: uuid.UUID
    invoice_number: str = Field(..., min_length=1, max_length=100)
    invoice_date: date
    invoice_amount: Decimal = Field(..., ge=0)
    tax_amount: Decimal = Field(Decimal("0"), ge=0)
    remarks: str | None = None

class TrackingResponse(TrackingCreate):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    customer_name: str | None = None
    delivery_challan_number: str | None = None
    attachment_path: str | None = None

def company(context: TenantContext):
    if not context.company_id: raise BadRequestException("Company ID is required")
    return context.company_id

async def validate(db, payload, company_id):
    customer = await db.scalar(select(Customer).where(Customer.id == payload.customer_id, Customer.company_id == company_id))
    if not customer: raise NotFoundException("Customer not found")
    challan = await db.scalar(select(RingsDocument).where(RingsDocument.id == payload.delivery_challan_id, RingsDocument.company_id == company_id, RingsDocument.document_type == RingsDocumentType.OUTWARD.value))
    if not challan: raise NotFoundException("Delivery Challan not found")
    if challan.customer_id != payload.customer_id: raise ValidationException("Delivery Challan does not belong to the selected customer")
    return challan

def serialize(row):
    data = TrackingResponse.model_validate(row).model_dump()
    data["customer_name"] = row.customer.name if row.customer else None
    data["delivery_challan_number"] = (
        row.delivery_challan.sln_challan_number or row.delivery_challan.document_number
        if row.delivery_challan else None
    )
    return TrackingResponse(**data)

@router.post("", response_model=StandardResponse[TrackingResponse], status_code=status.HTTP_201_CREATED)
async def create(payload: TrackingCreate, context: TenantContext = Depends(get_current_tenant_context), user: User = Depends(require_permission("invoice.create")), db: AsyncSession = Depends(get_db)):
    cid = company(context); await validate(db, payload, cid)
    duplicate = await db.scalar(select(SalesTaxInvoiceTracking.id).where(SalesTaxInvoiceTracking.company_id == cid, func.lower(SalesTaxInvoiceTracking.invoice_number) == payload.invoice_number.strip().lower()))
    if duplicate: raise ConflictException("Sales Tax Invoice number already exists")
    row = SalesTaxInvoiceTracking(company_id=cid, created_by_id=user.id, updated_by_id=user.id, **payload.model_dump()); db.add(row); await db.commit()
    row = await db.scalar(select(SalesTaxInvoiceTracking).options(selectinload(SalesTaxInvoiceTracking.customer), selectinload(SalesTaxInvoiceTracking.delivery_challan)).where(SalesTaxInvoiceTracking.id == row.id))
    return success_response(data=serialize(row).model_dump(mode="json"), message="Sales Tax Invoice tracked")

@router.get("", response_model=StandardResponse[list[TrackingResponse]])
async def list_entries(customer_id: uuid.UUID | None = None, search: str | None = None, page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200), context: TenantContext = Depends(get_current_tenant_context), _: User = Depends(require_permission("invoice.read")), db: AsyncSession = Depends(get_db)):
    filters = [SalesTaxInvoiceTracking.company_id == company(context), SalesTaxInvoiceTracking.is_active.is_(True)]
    if customer_id: filters.append(SalesTaxInvoiceTracking.customer_id == customer_id)
    if search: filters.append(SalesTaxInvoiceTracking.invoice_number.ilike(f"%{search}%"))
    total = await db.scalar(select(func.count()).select_from(SalesTaxInvoiceTracking).where(*filters))
    stmt = select(SalesTaxInvoiceTracking).options(selectinload(SalesTaxInvoiceTracking.customer), selectinload(SalesTaxInvoiceTracking.delivery_challan)).where(*filters).order_by(SalesTaxInvoiceTracking.invoice_date.desc()).offset((page-1)*page_size).limit(page_size)
    rows = list((await db.scalars(stmt)).all()); meta = build_pagination_metadata(int(total or 0), PaginationParams(page=page, page_size=page_size))
    return success_response(data=[serialize(r).model_dump(mode="json") for r in rows], pagination=meta)

@router.post("/{tracking_id}/attachment", response_model=StandardResponse[TrackingResponse])
async def upload_attachment(tracking_id: uuid.UUID, file: UploadFile = File(...), context: TenantContext = Depends(get_current_tenant_context), user: User = Depends(require_permission("invoice.create")), db: AsyncSession = Depends(get_db)):
    cid = company(context)
    row = await db.scalar(select(SalesTaxInvoiceTracking).options(selectinload(SalesTaxInvoiceTracking.customer), selectinload(SalesTaxInvoiceTracking.delivery_challan)).where(SalesTaxInvoiceTracking.id == tracking_id, SalesTaxInvoiceTracking.company_id == cid))
    if not row: raise NotFoundException("Sales Tax Invoice tracking entry not found")
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in {".pdf", ".png", ".jpg", ".jpeg"}: raise BadRequestException("Only PDF, PNG and JPEG attachments are supported")
    content = await file.read()
    if len(content) > 10 * 1024 * 1024: raise BadRequestException("Attachment is too large (maximum 10 MB)")
    directory = Path(settings.UPLOAD_DIR).resolve() / "sales-tax-invoices" / str(cid)
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / f"{row.id}{suffix}"
    target.write_bytes(content)
    row.attachment_path = str(target); row.updated_by_id = user.id
    await db.commit()
    return success_response(data=serialize(row).model_dump(mode="json"), message="Attachment uploaded")

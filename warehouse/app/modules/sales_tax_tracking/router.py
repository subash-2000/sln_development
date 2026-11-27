import uuid
from datetime import date
from decimal import Decimal
from pathlib import Path

from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.constants import RingsDocumentStatus, RingsDocumentType
from app.core.database import get_db
from app.core.dependencies import TenantContext, get_current_tenant_context, require_permission
from app.core.exceptions import BadRequestException, ConflictException, NotFoundException, ValidationException
from app.core.pagination import PaginationParams, build_pagination_metadata
from app.core.response import StandardResponse, success_response
from app.models.rings import RingsDocument
from app.models.sales_tax_tracking import SalesTaxInvoiceTracking
from app.models.user import User

router = APIRouter(prefix="/sales-tax-invoices", tags=["Supplier Tax Invoice Tracking"])

class InvoiceDetails(BaseModel):
    packing_weight: Decimal | None = Field(None, ge=0, max_digits=14, decimal_places=3)
    gross_weight: Decimal | None = Field(None, ge=0, max_digits=14, decimal_places=3)
    eway_bill_number: str | None = Field(None, max_length=100)
    ackn_copies_status: str | None = Field(None, max_length=100)
    remarks: str | None = None


class TrackingCreate(InvoiceDetails):
    delivery_challan_id: uuid.UUID
    invoice_number: str = Field(..., min_length=1, max_length=100)
    invoice_date: date
    invoice_amount: Decimal = Field(..., ge=0)
    tax_amount: Decimal = Field(Decimal("0"), ge=0)
    remarks: str | None = None

class TrackingResponse(InvoiceDetails):
    id: uuid.UUID | None = None
    delivery_challan_id: uuid.UUID
    delivery_challan_number: str
    dispatch_number: str
    dispatch_date: date | None = None
    supplier_id: uuid.UUID | None = None
    supplier_name: str | None = None
    customer_name: str | None = None
    vehicle_number: str | None = None
    invoice_number: str | None = None
    invoice_date: date | None = None
    invoice_amount: Decimal | None = None
    tax_amount: Decimal | None = None
    remarks: str | None = None
    attachment_path: str | None = None
    tracking_status: str

def company(context: TenantContext):
    if not context.company_id:
        raise BadRequestException("Company ID is required")
    return context.company_id

def serialize(dispatch: RingsDocument, tracking: SalesTaxInvoiceTracking | None):
    dispatch_date = dispatch.sln_challan_date or dispatch.supplier_customer_invoice_date
    if not dispatch_date and dispatch.updated_at:
        dispatch_date = dispatch.updated_at.date()
    return TrackingResponse(
        id=tracking.id if tracking else None,
        delivery_challan_id=dispatch.id,
        delivery_challan_number=dispatch.sln_challan_number or dispatch.document_number,
        dispatch_number=dispatch.document_number,
        dispatch_date=dispatch_date,
        supplier_id=dispatch.vendor_id,
        supplier_name=dispatch.vendor.name if dispatch.vendor else None,
        customer_name=dispatch.customer.name if dispatch.customer else None,
        vehicle_number=dispatch.vehicle_number,
        invoice_number=tracking.invoice_number if tracking else None,
        invoice_date=tracking.invoice_date if tracking else None,
        invoice_amount=tracking.invoice_amount if tracking else None,
        tax_amount=tracking.tax_amount if tracking else None,
        remarks=tracking.remarks if tracking else None,
        packing_weight=tracking.packing_weight if tracking else None,
        gross_weight=tracking.gross_weight if tracking else None,
        eway_bill_number=tracking.eway_bill_number if tracking else None,
        ackn_copies_status=tracking.ackn_copies_status if tracking else None,
        attachment_path=tracking.attachment_path if tracking else None,
        tracking_status="RECEIVED" if tracking else "PENDING",
    )

async def get_dispatch(db: AsyncSession, dispatch_id: uuid.UUID, company_id: uuid.UUID):
    dispatch = await db.scalar(select(RingsDocument).options(selectinload(RingsDocument.vendor), selectinload(RingsDocument.customer)).where(
        RingsDocument.id == dispatch_id,
        RingsDocument.company_id == company_id,
        RingsDocument.document_type == RingsDocumentType.OUTWARD.value,
        RingsDocument.status == RingsDocumentStatus.POSTED.value,
    ))
    if not dispatch:
        raise NotFoundException("Posted dispatch / Delivery Challan not found")
    if not dispatch.vendor_id:
        raise ValidationException("The dispatch does not have a supplier")
    return dispatch

@router.post("", response_model=StandardResponse[TrackingResponse], status_code=status.HTTP_201_CREATED)
async def create(payload: TrackingCreate, context: TenantContext = Depends(get_current_tenant_context), user: User = Depends(require_permission("invoice.create")), db: AsyncSession = Depends(get_db)):
    cid = company(context)
    dispatch = await get_dispatch(db, payload.delivery_challan_id, cid)
    if await db.scalar(select(SalesTaxInvoiceTracking.id).where(SalesTaxInvoiceTracking.company_id == cid, SalesTaxInvoiceTracking.delivery_challan_id == dispatch.id, SalesTaxInvoiceTracking.is_active.is_(True))):
        raise ConflictException("A supplier tax invoice is already stored for this dispatch")
    if await db.scalar(select(SalesTaxInvoiceTracking.id).where(SalesTaxInvoiceTracking.company_id == cid, func.lower(SalesTaxInvoiceTracking.invoice_number) == payload.invoice_number.strip().lower(), SalesTaxInvoiceTracking.is_active.is_(True))):
        raise ConflictException("Supplier tax invoice number already exists")
    row = SalesTaxInvoiceTracking(
        company_id=cid, vendor_id=dispatch.vendor_id, customer_id=dispatch.customer_id,
        delivery_challan_id=dispatch.id, invoice_number=payload.invoice_number.strip(),
        invoice_date=payload.invoice_date, invoice_amount=payload.invoice_amount,
        tax_amount=payload.tax_amount, remarks=payload.remarks,
        packing_weight=payload.packing_weight,
        gross_weight=payload.gross_weight,
        eway_bill_number=payload.eway_bill_number,
        ackn_copies_status=payload.ackn_copies_status,
        created_by_id=user.id, updated_by_id=user.id,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return success_response(data=serialize(dispatch, row).model_dump(mode="json"), message="Supplier tax invoice stored against dispatch")

@router.get("", response_model=StandardResponse[list[TrackingResponse]])
async def list_entries(supplier_id: uuid.UUID | None = None, search: str | None = None, tracking_status: str | None = None, page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200), context: TenantContext = Depends(get_current_tenant_context), _: User = Depends(require_permission("invoice.read")), db: AsyncSession = Depends(get_db)):
    cid = company(context)
    join_on = and_(SalesTaxInvoiceTracking.delivery_challan_id == RingsDocument.id, SalesTaxInvoiceTracking.is_active.is_(True))
    filters = [RingsDocument.company_id == cid, RingsDocument.document_type == RingsDocumentType.OUTWARD.value, RingsDocument.status == RingsDocumentStatus.POSTED.value]
    if supplier_id:
        filters.append(RingsDocument.vendor_id == supplier_id)
    if tracking_status == "PENDING":
        filters.append(SalesTaxInvoiceTracking.id.is_(None))
    elif tracking_status == "RECEIVED":
        filters.append(SalesTaxInvoiceTracking.id.is_not(None))
    if search:
        pattern = f"%{search}%"
        filters.append(or_(RingsDocument.document_number.ilike(pattern), RingsDocument.sln_challan_number.ilike(pattern), SalesTaxInvoiceTracking.invoice_number.ilike(pattern)))
    total = await db.scalar(select(func.count()).select_from(RingsDocument).outerjoin(SalesTaxInvoiceTracking, join_on).where(*filters))
    stmt = select(RingsDocument, SalesTaxInvoiceTracking).outerjoin(SalesTaxInvoiceTracking, join_on).options(selectinload(RingsDocument.vendor), selectinload(RingsDocument.customer)).where(*filters).order_by(RingsDocument.updated_at.desc()).offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(stmt)).all()
    meta = build_pagination_metadata(int(total or 0), PaginationParams(page=page, page_size=page_size))
    return success_response(data=[serialize(dispatch, tracking).model_dump(mode="json") for dispatch, tracking in rows], pagination=meta)

@router.patch("/{tracking_id}/details", response_model=StandardResponse[TrackingResponse])
async def update_details(tracking_id: uuid.UUID, payload: InvoiceDetails, context: TenantContext = Depends(get_current_tenant_context), user: User = Depends(require_permission("invoice.create")), db: AsyncSession = Depends(get_db)):
    cid = company(context)
    row = await db.scalar(select(SalesTaxInvoiceTracking).where(
        SalesTaxInvoiceTracking.id == tracking_id,
        SalesTaxInvoiceTracking.company_id == cid,
        SalesTaxInvoiceTracking.is_active.is_(True),
    ))
    if not row:
        raise NotFoundException("Supplier tax invoice tracking entry not found")
    dispatch = await get_dispatch(db, row.delivery_challan_id, cid)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    row.updated_by_id = user.id
    await db.commit()
    return success_response(data=serialize(dispatch, row).model_dump(mode="json"))


@router.post("/{tracking_id}/attachment", response_model=StandardResponse[TrackingResponse])
async def upload_attachment(tracking_id: uuid.UUID, file: UploadFile = File(...), context: TenantContext = Depends(get_current_tenant_context), user: User = Depends(require_permission("invoice.create")), db: AsyncSession = Depends(get_db)):
    cid = company(context)
    row = await db.scalar(select(SalesTaxInvoiceTracking).where(SalesTaxInvoiceTracking.id == tracking_id, SalesTaxInvoiceTracking.company_id == cid, SalesTaxInvoiceTracking.is_active.is_(True)))
    if not row:
        raise NotFoundException("Supplier tax invoice tracking entry not found")
    dispatch = await get_dispatch(db, row.delivery_challan_id, cid)
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in {".pdf", ".png", ".jpg", ".jpeg"}:
        raise BadRequestException("Only PDF, PNG and JPEG attachments are supported")
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise BadRequestException("Attachment is too large (maximum 10 MB)")
    directory = Path(settings.UPLOAD_DIR).resolve() / "sales-tax-invoices" / str(cid)
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / f"{row.id}{suffix}"
    target.write_bytes(content)
    row.attachment_path = str(target)
    row.updated_by_id = user.id
    await db.commit()
    return success_response(data=serialize(dispatch, row).model_dump(mode="json"), message="Supplier tax invoice attachment stored")

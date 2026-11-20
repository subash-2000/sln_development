import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import TenantContext, get_current_tenant_context, require_permission
from app.core.exceptions import BadRequestException
from app.core.pagination import PaginationParams, build_pagination_metadata
from app.core.response import StandardResponse, success_response
from app.models.user import User
from app.modules.credit_debit.schemas import CancelRequest, NoteCreate, NoteResponse, NoteSummary, NoteUpdate
from app.modules.credit_debit.service import CreditDebitService

router = APIRouter(prefix="/credit-debit-notes", tags=["Customer Credit & Debit Notes"])

def company(context: TenantContext) -> uuid.UUID:
    if not context.company_id: raise BadRequestException("Company ID is required")
    return context.company_id

@router.post("", response_model=StandardResponse[NoteResponse], status_code=status.HTTP_201_CREATED)
async def create_note(payload: NoteCreate, context: TenantContext = Depends(get_current_tenant_context), user: User = Depends(require_permission("invoice.create")), db: AsyncSession = Depends(get_db)):
    result = await CreditDebitService(db).create(payload, company(context), user.id)
    return success_response(data=result.model_dump(mode="json"), message="Draft note created")

@router.get("", response_model=StandardResponse[list[NoteResponse]])
async def list_notes(customer_id: uuid.UUID | None = None, vendor_id: uuid.UUID | None = None, note_type: str | None = None, note_status: str | None = Query(None, alias="status"), search: str | None = None, date_from: date | None = None, date_to: date | None = None, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=200), context: TenantContext = Depends(get_current_tenant_context), _: User = Depends(require_permission("invoice.read")), db: AsyncSession = Depends(get_db)):
    rows, total = await CreditDebitService(db).list(company(context), customer_id, vendor_id, note_type, note_status, search, date_from, date_to, page, page_size)
    meta = build_pagination_metadata(total, PaginationParams(page=page, page_size=page_size))
    return success_response(data=[r.model_dump(mode="json") for r in rows], pagination=meta)

@router.get("/summary", response_model=StandardResponse[NoteSummary])
async def note_summary(customer_id: uuid.UUID | None = None, vendor_id: uuid.UUID | None = None, context: TenantContext = Depends(get_current_tenant_context), _: User = Depends(require_permission("invoice.read")), db: AsyncSession = Depends(get_db)):
    result = await CreditDebitService(db).summary(company(context), customer_id, vendor_id)
    return success_response(data=result.model_dump(mode="json"))

@router.put("/{note_id}", response_model=StandardResponse[NoteResponse])
async def update_note(note_id: uuid.UUID, payload: NoteUpdate, context: TenantContext = Depends(get_current_tenant_context), user: User = Depends(require_permission("invoice.create")), db: AsyncSession = Depends(get_db)):
    result = await CreditDebitService(db).update(note_id, payload, company(context), user.id)
    return success_response(data=result.model_dump(mode="json"), message="Draft note updated")

@router.post("/{note_id}/confirm", response_model=StandardResponse[NoteResponse])
async def confirm_note(note_id: uuid.UUID, context: TenantContext = Depends(get_current_tenant_context), user: User = Depends(require_permission("invoice.post")), db: AsyncSession = Depends(get_db)):
    result = await CreditDebitService(db).confirm(note_id, company(context), user.id)
    return success_response(data=result.model_dump(mode="json"), message="Note confirmed")

@router.post("/{note_id}/cancel", response_model=StandardResponse[NoteResponse])
async def cancel_note(note_id: uuid.UUID, payload: CancelRequest, context: TenantContext = Depends(get_current_tenant_context), user: User = Depends(require_permission("invoice.cancel")), db: AsyncSession = Depends(get_db)):
    result = await CreditDebitService(db).cancel(note_id, payload.reason, company(context), user.id)
    return success_response(data=result.model_dump(mode="json"), message="Note cancelled")

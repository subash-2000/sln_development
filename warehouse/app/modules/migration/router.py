from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, UploadFile, Query, HTTPException
from fastapi.responses import StreamingResponse

from app.core.database import get_db
from app.core.dependencies import get_current_tenant_context, require_permission, TenantContext
from app.core.response import StandardResponse, success_response
from app.core.export import ExportService
from app.modules.migration.schemas import ImportBatchCreate, ImportBatchResponse, ImportBatchDetailResponse
from app.modules.migration.service import MigrationService
from sqlalchemy import select
from app.modules.migration.models import ImportBatch

router = APIRouter(prefix="/migration", tags=["Data Migration"])

def _service(db=Depends(get_db)):
    return MigrationService(db)

@router.post(
    "/import",
    response_model=StandardResponse[ImportBatchResponse],
    dependencies=[Depends(require_permission("migration.import"))]
)
async def create_import_batch(
    import_type: str,
    file: UploadFile = File(...),
    column_mapping: str | None = Form(None),
    context: TenantContext = Depends(get_current_tenant_context),
    service: MigrationService = Depends(_service)
):
    """
    Upload an Excel/CSV file to import masters.
    Supported types: PRODUCT, VENDOR, CUSTOMER, TRANSPORTER.
    """
    from app.modules.migration.excel_support import parse_mapping

    company_id = context.company_id
    batch_data = ImportBatchCreate(
        import_type=import_type.upper(),
        filename=file.filename,
        column_mapping=parse_mapping(column_mapping) or None,
    )
    batch = await service.create_batch(company_id=company_id, data=batch_data)
    file_content = await file.read()
    await service.process_import(batch.id, file_content)
    refreshed = await service.db.get(ImportBatch, batch.id)
    return success_response(
        data=ImportBatchResponse.from_orm(refreshed or batch),
        message="Import completed",
    )

@router.get(
    "/export",
    dependencies=[Depends(require_permission("migration.import"))]
)
async def export_data(
    export_type: str,
    format: str = Query("excel", pattern="^(excel|csv)$"),
    context: TenantContext = Depends(get_current_tenant_context),
    db=Depends(get_db)
):
    """
    Generic export endpoint for different modules.
    """
    company_id = context.company_id
    
    data = []
    if export_type == "PRODUCT":
        from app.models.product import Product
        stmt = select(Product).where(Product.company_id == company_id)
        res = await db.execute(stmt)
        products = res.scalars().all()
        data = [{"SKU": p.sku, "Name": p.name, "Description": p.description, "Status": p.status} for p in products]
    elif export_type == "VENDOR":
        from app.models.vendor import Vendor
        stmt = select(Vendor).where(Vendor.company_id == company_id)
        res = await db.execute(stmt)
        vendors = res.scalars().all()
        data = [{"Code": v.code, "Name": v.name, "Status": v.status} for v in vendors]
    elif export_type == "CUSTOMER":
        from app.models.customer import Customer
        stmt = select(Customer).where(Customer.company_id == company_id)
        res = await db.execute(stmt)
        customers = res.scalars().all()
        data = [{"Code": c.code, "Name": c.name, "GSTIN": c.gstin, "Status": c.status} for c in customers]
    elif export_type == "TRANSPORTER":
        from app.models.transport import Transporter
        stmt = select(Transporter).where(Transporter.company_id == company_id)
        res = await db.execute(stmt)
        transporters = res.scalars().all()
        data = [{"Code": t.code, "Name": t.name, "GSTIN": t.gstin, "Status": t.status} for t in transporters]
    elif export_type == "USER":
        from app.models.user import User
        # Note: In a real system, we'd only export users related to the company
        # For this foundation, we'll fetch users that have a role in this company
        from app.models.rbac import UserRole
        stmt = select(User).join(UserRole).where(UserRole.company_id == company_id)
        res = await db.execute(stmt)
        users = res.scalars().all()
        data = [{"Username": u.username, "Email": u.email, "FullName": u.full_name, "Status": u.status} for u in users]
    
    if format == "csv":
        return ExportService.to_csv(data, filename=export_type.lower())
    return ExportService.to_excel(data, filename=export_type.lower())

@router.get(
    "/template",
    dependencies=[Depends(require_permission("migration.import"))],
)
async def download_import_template(import_type: str = Query("PRODUCT")):
    from app.modules.migration.excel_support import template_bytes

    kind = import_type.upper()
    payload = template_bytes(kind)
    return StreamingResponse(
        iter([payload]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={kind.lower()}_import_template.xlsx"},
    )


@router.get(
    "/batches",
    response_model=StandardResponse[List[ImportBatchResponse]],
    dependencies=[Depends(require_permission("migration.import"))]
)
async def list_import_batches(
    context: TenantContext = Depends(get_current_tenant_context),
    db=Depends(get_db)
):
    """List all import batches for the current company."""
    stmt = select(ImportBatch).where(ImportBatch.company_id == context.company_id).order_by(ImportBatch.created_at.desc())
    result = await db.execute(stmt)
    batches = result.scalars().all()
    
    return success_response(
        data=[ImportBatchResponse.from_orm(b) for b in batches],
        message="Import batches retrieved successfully"
    )

@router.get(
    "/batches/{batch_id}",
    response_model=StandardResponse[ImportBatchDetailResponse],
    dependencies=[Depends(require_permission("migration.import"))]
)
async def get_import_batch_detail(
    batch_id: UUID,
    context: TenantContext = Depends(get_current_tenant_context),
    db=Depends(get_db)
):
    """Get detailed status and logs for a specific import batch."""
    stmt = select(ImportBatch).where(
        ImportBatch.id == batch_id, 
        ImportBatch.company_id == context.company_id
    )
    result = await db.execute(stmt)
    batch = result.scalar_one_or_none()
    
    if not batch:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Batch not found")
        
    return success_response(
        data=ImportBatchDetailResponse.from_orm(batch),
        message="Batch details retrieved successfully"
    )

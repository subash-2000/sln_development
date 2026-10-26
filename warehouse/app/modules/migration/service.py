import uuid
import io
import pandas as pd
from datetime import datetime, UTC
from decimal import Decimal
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.modules.migration.models import ImportBatch, ImportLog
from app.modules.migration.schemas import ImportBatchCreate
from app.models.product import Product, ProductCategory, UOM, UomCategory
from app.models.vendor import Vendor
from app.core.exceptions import AppException

class MigrationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_batch(self, company_id: uuid.UUID, data: ImportBatchCreate) -> ImportBatch:
        batch = ImportBatch(
            company_id=company_id,
            import_type=data.import_type,
            filename=data.filename,
            column_mapping=data.column_mapping,
            status="PENDING"
        )
        self.db.add(batch)
        await self.db.commit()
        await self.db.refresh(batch)
        return batch

    async def process_import(self, batch_id: uuid.UUID, file_content: bytes):
        """Main entry point for processing an import file."""
        batch_stmt = select(ImportBatch).where(ImportBatch.id == batch_id)
        result = await self.db.execute(batch_stmt)
        batch = result.scalar_one_or_none()
        
        if not batch:
            return

        batch.status = "PROCESSING"
        batch.started_at = datetime.now(UTC)

        try:
            from app.modules.migration.excel_support import pick_sheet_frames, parse_mapping
            from app.modules.migration.importers import HANDLERS

            if batch.filename and str(batch.filename).lower().endswith(".csv"):
                df = pd.read_csv(io.BytesIO(file_content))
            else:
                df = pick_sheet_frames(file_content, batch.filename, batch.import_type)

            batch.total_records = len(df)

            handler = HANDLERS.get((batch.import_type or "").upper())
            if handler:
                mapping = parse_mapping(batch.column_mapping)
                outcome = await handler(self.db, batch.company_id, df, mapping)
                batch.success_count = outcome.success
                batch.failed_count = outcome.failed
                from app.modules.migration.models import ImportLog

                for err in outcome.errors[:200]:
                    self.db.add(
                        ImportLog(
                            batch_id=batch.id,
                            row_number=err["row"],
                            record_identifier=err["id"],
                            status="ERROR",
                            error_details={"message": err["message"]},
                        )
                    )
            elif batch.import_type == "USER":
                await self._import_users_mapped(batch, df)
            else:
                raise AppException(f"Unsupported import type: {batch.import_type}")

            batch.status = "COMPLETED"
            batch.completed_at = datetime.now(UTC)
        except Exception as e:
            batch.status = "FAILED"
            batch.error_message = str(e)
            batch.completed_at = datetime.now(UTC)
        
        await self.db.commit()

    async def _import_products_mapped(self, batch: ImportBatch, df: pd.DataFrame):
        mapping = batch.column_mapping or {}
        # Reverse mapping for easier lookup: system_field -> file_column
        # Or just use the mapping directly if it's file_column -> system_field
        
        success_count = 0
        failed_count = 0

        # Pre-fetch context
        uom_cat_stmt = select(UomCategory).where(UomCategory.name == "Unit")
        uom_cat = (await self.db.execute(uom_cat_stmt)).scalar_one_or_none()
        if not uom_cat:
            uom_cat = UomCategory(name="Unit")
            self.db.add(uom_cat)
            await self.db.flush()

        uom_stmt = select(UOM).where(UOM.code == "PCS")
        uom = (await self.db.execute(uom_stmt)).scalar_one_or_none()
        if not uom:
            uom = UOM(category_id=uom_cat.id, code="PCS", name="Pieces", factor=Decimal("1.0"), uom_type="REFERENCE")
            self.db.add(uom)
            await self.db.flush()

        # Batch size for commit
        BATCH_SIZE = 100
        items_to_add = []

        for index, row in df.iterrows():
            row_num = index + 2
            
            # Map fields
            data = {}
            for file_col, sys_field in mapping.items():
                if sys_field:
                    val = row.get(file_col)
                    if pd.isna(val):
                        val = None
                    data[sys_field] = val

            sku = str(data.get("sku") or row.get("SKU") or row.get("sku") or "").strip()
            if sku.lower() == "nan":
                sku = ""
            name = str(data.get("name") or row.get("Name") or row.get("name") or sku).strip()
            if name.lower() == "nan":
                name = sku
            desc = str(data.get("description") or row.get("Description") or row.get("description") or "").strip()
            if desc.lower() == "nan":
                desc = ""

            try:
                if not sku:
                    raise ValueError("SKU is required")

                # Note: For "very very fast", we should ideally pre-load all SKUs into a set
                # instead of querying one by one.
                existing_stmt = select(Product.id).where(Product.company_id == batch.company_id, Product.sku == sku)
                res = await self.db.execute(existing_stmt)
                if res.scalar_one_or_none():
                    # Instead of failing, we could upsert. Odoo supports both.
                    # For now, let's keep it simple but efficient.
                    raise ValueError(f"Product with SKU {sku} already exists")

                product = Product(
                    company_id=batch.company_id,
                    sku=sku,
                    name=name,
                    description=desc,
                    uom_id=uom.id,
                    status="ACTIVE"
                )
                
                items_to_add.append(product)
                success_count += 1
                
                if len(items_to_add) >= BATCH_SIZE:
                    self.db.add_all(items_to_add)
                    await self.db.flush()
                    items_to_add = []
                    
            except Exception as e:
                failed_count += 1
                log = ImportLog(
                    batch_id=batch.id,
                    row_number=row_num,
                    record_identifier=sku,
                    status="ERROR",
                    error_details={"message": str(e)}
                )
                self.db.add(log)

        if items_to_add:
            self.db.add_all(items_to_add)
        
        batch.success_count = success_count
        batch.failed_count = failed_count

    async def _import_vendors_mapped(self, batch: ImportBatch, df: pd.DataFrame):
        mapping = batch.column_mapping or {}
        success_count = 0
        failed_count = 0
        BATCH_SIZE = 100
        items_to_add = []

        for index, row in df.iterrows():
            row_num = index + 2
            data = {}
            for file_col, sys_field in mapping.items():
                if sys_field:
                    val = row.get(file_col)
                    if pd.isna(val):
                        val = None
                    data[sys_field] = val

            code = str(data.get("code") or row.get("Code") or row.get("code") or "").strip()
            if code.lower() == "nan":
                code = ""
            name = str(data.get("name") or row.get("Name") or row.get("name") or code).strip()
            if name.lower() == "nan":
                name = code
            
            try:
                if not code:
                    raise ValueError("Vendor Code is required")

                existing_stmt = select(Vendor.id).where(Vendor.company_id == batch.company_id, Vendor.code == code)
                res = await self.db.execute(existing_stmt)
                if res.scalar_one_or_none():
                    raise ValueError(f"Vendor with code {code} already exists")

                vendor = Vendor(
                    company_id=batch.company_id,
                    code=code,
                    name=name,
                    status="ACTIVE"
                )
                
                items_to_add.append(vendor)
                success_count += 1
                
                if len(items_to_add) >= BATCH_SIZE:
                    self.db.add_all(items_to_add)
                    await self.db.flush()
                    items_to_add = []

            except Exception as e:
                failed_count += 1
                log = ImportLog(
                    batch_id=batch.id,
                    row_number=row_num,
                    record_identifier=code,
                    status="ERROR",
                    error_details={"message": str(e)}
                )
                self.db.add(log)

        if items_to_add:
            self.db.add_all(items_to_add)

        batch.success_count = success_count
        batch.failed_count = failed_count

    async def _import_customers_mapped(self, batch: ImportBatch, df: pd.DataFrame):
        from app.models.customer import Customer
        mapping = batch.column_mapping or {}
        success_count = 0
        failed_count = 0
        BATCH_SIZE = 100
        items_to_add = []

        for index, row in df.iterrows():
            row_num = index + 2
            data = {}
            for file_col, sys_field in mapping.items():
                if sys_field:
                    val = row.get(file_col)
                    if pd.isna(val):
                        val = None
                    data[sys_field] = val

            code = str(data.get("code") or "").strip()
            
            try:
                if not code:
                    raise ValueError("Customer Code is required")

                existing_stmt = select(Customer.id).where(Customer.company_id == batch.company_id, Customer.code == code)
                res = await self.db.execute(existing_stmt)
                if res.scalar_one_or_none():
                    raise ValueError(f"Customer with code {code} already exists")

                customer = Customer(
                    company_id=batch.company_id,
                    code=code,
                    name=str(data.get("name") or code),
                    gstin=str(data.get("gstin") or ""),
                    status="ACTIVE"
                )
                
                items_to_add.append(customer)
                success_count += 1
                
                if len(items_to_add) >= BATCH_SIZE:
                    self.db.add_all(items_to_add)
                    await self.db.flush()
                    items_to_add = []

            except Exception as e:
                failed_count += 1
                log = ImportLog(
                    batch_id=batch.id,
                    row_number=row_num,
                    record_identifier=code,
                    status="ERROR",
                    error_details={"message": str(e)}
                )
                self.db.add(log)

        if items_to_add:
            self.db.add_all(items_to_add)

        batch.success_count = success_count
        batch.failed_count = failed_count

    async def _import_users_mapped(self, batch: ImportBatch, df: pd.DataFrame):
        from app.models.user import User
        from app.core.security import hash_password
        mapping = batch.column_mapping or {}
        success_count = 0
        failed_count = 0
        BATCH_SIZE = 100
        items_to_add = []

        for index, row in df.iterrows():
            row_num = index + 2
            data = {}
            for file_col, sys_field in mapping.items():
                if sys_field:
                    val = row.get(file_col)
                    if pd.isna(val):
                        val = None
                    data[sys_field] = val

            username = str(data.get("username") or "").strip()
            email = str(data.get("email") or "").strip()
            
            try:
                if not username:
                    raise ValueError("Username is required")
                if not email:
                    raise ValueError("Email is required")

                existing_stmt = select(User.id).where((User.username == username) | (User.email == email))
                res = await self.db.execute(existing_stmt)
                if res.scalar_one_or_none():
                    raise ValueError(f"User with username {username} or email {email} already exists")

                user = User(
                    username=username,
                    email=email,
                    full_name=str(data.get("full_name") or username),
                    password_hash=hash_password("Welcome123!"), # Default password for imported users
                    status="ACTIVE",
                    is_superuser=False
                )
                
                items_to_add.append(user)
                success_count += 1
                
                if len(items_to_add) >= BATCH_SIZE:
                    self.db.add_all(items_to_add)
                    await self.db.flush()
                    items_to_add = []

            except Exception as e:
                failed_count += 1
                log = ImportLog(
                    batch_id=batch.id,
                    row_number=row_num,
                    record_identifier=username,
                    status="ERROR",
                    error_details={"message": str(e)}
                )
                self.db.add(log)

        if items_to_add:
            self.db.add_all(items_to_add)

        batch.success_count = success_count
        batch.failed_count = failed_count

    async def _import_products(self, batch: ImportBatch, df: pd.DataFrame):
        success_count = 0
        failed_count = 0

        # Pre-fetch or ensure a default UOM and Category for the company
        # (This is a simplified strategy for the foundation)
        uom_cat_stmt = select(UomCategory).where(UomCategory.name == "Unit")
        uom_cat = (await self.db.execute(uom_cat_stmt)).scalar_one_or_none()
        if not uom_cat:
            uom_cat = UomCategory(name="Unit")
            self.db.add(uom_cat)
            await self.db.flush()

        uom_stmt = select(UOM).where(UOM.code == "PCS")
        uom = (await self.db.execute(uom_stmt)).scalar_one_or_none()
        if not uom:
            uom = UOM(category_id=uom_cat.id, code="PCS", name="Pieces", factor=Decimal("1.0"), uom_type="REFERENCE")
            self.db.add(uom)
            await self.db.flush()

        for index, row in df.iterrows():
            row_num = index + 2
            sku = str(row.get("SKU", "")).strip()
            if sku.lower() == "nan":
                sku = ""
            
            try:
                if not sku:
                    raise ValueError("SKU is required")

                existing_stmt = select(Product).where(Product.company_id == batch.company_id, Product.sku == sku)
                res = await self.db.execute(existing_stmt)
                if res.scalar_one_or_none():
                    raise ValueError(f"Product with SKU {sku} already exists")

                product = Product(
                    company_id=batch.company_id,
                    sku=sku,
                    name=str(row.get("Name", sku)),
                    description=str(row.get("Description", "")),
                    uom_id=uom.id, # Using default UOM
                    status="ACTIVE"
                )
                
                self.db.add(product)
                success_count += 1
            except Exception as e:
                failed_count += 1
                log = ImportLog(
                    batch_id=batch.id,
                    row_number=row_num,
                    record_identifier=sku,
                    status="ERROR",
                    error_details={"message": str(e)}
                )
                self.db.add(log)

        batch.success_count = success_count
        batch.failed_count = failed_count

    async def _import_vendors(self, batch: ImportBatch, df: pd.DataFrame):
        success_count = 0
        failed_count = 0

        for index, row in df.iterrows():
            row_num = index + 2
            code = str(row.get("Code", "")).strip()
            if code.lower() == "nan":
                code = ""
            
            try:
                if not code:
                    raise ValueError("Vendor Code is required")

                existing_stmt = select(Vendor).where(Vendor.company_id == batch.company_id, Vendor.code == code)
                res = await self.db.execute(existing_stmt)
                if res.scalar_one_or_none():
                    raise ValueError(f"Vendor with code {code} already exists")

                vendor = Vendor(
                    company_id=batch.company_id,
                    code=code,
                    name=str(row.get("Name", code)),
                    status="ACTIVE"
                )
                
                self.db.add(vendor)
                success_count += 1
            except Exception as e:
                failed_count += 1
                log = ImportLog(
                    batch_id=batch.id,
                    row_number=row_num,
                    record_identifier=code,
                    status="ERROR",
                    error_details={"message": str(e)}
                )
                self.db.add(log)

        batch.success_count = success_count
        batch.failed_count = failed_count

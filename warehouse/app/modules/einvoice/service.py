import time
import uuid
from datetime import UTC, datetime
from decimal import Decimal

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import BadRequestException, NotFoundException
from app.models.company import Company
from app.models.einvoice import EInvoiceApiLog, EInvoiceConfiguration, EInvoiceDocument
from app.models.invoicing import Invoice
from app.models.logistics import DispatchOrder
from app.modules.einvoice.schemas import ConfigurationResponse, ConfigurationUpdate, DocumentCreate


class EInvoiceService:
    MYGST_BASE = {
        "sandbox": "https://testapi.mygstcafe.com/eicore/v1.03",
        "production": "https://api.mygstcafe.com/eicore/v1.03",
    }
    NIC_BASE = {
        "sandbox": "https://einv1api.gstsandbox.nic.in",
        "production": "https://einvoice1.gst.gov.in",
    }
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_configuration(self, company_id: uuid.UUID) -> ConfigurationResponse:
        cfg = await self._configuration(company_id, required=False)
        if not cfg:
            return ConfigurationResponse(company_id=company_id)
        return self._safe_configuration(cfg)

    async def save_configuration(
        self, company_id: uuid.UUID, user_id: uuid.UUID, data: ConfigurationUpdate
    ) -> ConfigurationResponse:
        cfg = await self._configuration(company_id, required=False)
        if not cfg:
            cfg = EInvoiceConfiguration(company_id=company_id, created_by_id=user_id)
            self.db.add(cfg)
        values = data.model_dump(exclude_unset=True)
        secret_fields = {"api_password", "api_secret", "client_secret", "auth_token"}
        for key, value in values.items():
            if key in secret_fields and (value is None or value == ""):
                continue
            setattr(cfg, key, value.strip() if isinstance(value, str) else value)
        cfg.updated_by_id = user_id
        await self.db.commit()
        await self.db.refresh(cfg)
        return self._safe_configuration(cfg)

    async def create_document(
        self, company_id: uuid.UUID, user_id: uuid.UUID, data: DocumentCreate
    ) -> EInvoiceDocument:
        if bool(data.invoice_id) == bool(data.dispatch_order_id):
            raise BadRequestException("Select exactly one invoice or dispatch order")
        if data.invoice_id:
            stmt = (
                select(Invoice)
                .where(Invoice.id == data.invoice_id, Invoice.company_id == company_id)
                .options(selectinload(Invoice.lines), selectinload(Invoice.customer), selectinload(Invoice.warehouse))
            )
            source = (await self.db.execute(stmt)).scalar_one_or_none()
            if not source:
                raise NotFoundException("Invoice not found")
            number = source.invoice_number
            payload = await self._invoice_payload(source, company_id)
        else:
            stmt = (
                select(DispatchOrder)
                .where(DispatchOrder.id == data.dispatch_order_id, DispatchOrder.company_id == company_id)
                .options(selectinload(DispatchOrder.lines), selectinload(DispatchOrder.customer), selectinload(DispatchOrder.warehouse))
            )
            source = (await self.db.execute(stmt)).scalar_one_or_none()
            if not source:
                raise NotFoundException("Dispatch order not found")
            number = source.dispatch_number
            payload = await self._dispatch_payload(source, company_id)
        if data.payload_override:
            payload.update(data.payload_override)
        document = EInvoiceDocument(
            company_id=company_id, invoice_id=data.invoice_id,
            dispatch_order_id=data.dispatch_order_id, document_type=data.document_type,
            document_number=number, request_payload=payload, distance_km=data.distance_km,
            transporter_id=data.transporter_id, transport_mode=data.transport_mode,
            vehicle_number=(data.vehicle_number or "").replace(" ", "").upper() or None,
            vehicle_type=data.vehicle_type, created_by_id=user_id, updated_by_id=user_id,
        )
        self.db.add(document)
        await self.db.commit()
        await self.db.refresh(document)
        return document

    async def list_documents(self, company_id: uuid.UUID, offset: int, limit: int, status: str | None):
        filters = [EInvoiceDocument.company_id == company_id]
        if status:
            filters.append(EInvoiceDocument.status == status)
        total = (await self.db.execute(select(func.count()).select_from(EInvoiceDocument).where(*filters))).scalar_one()
        rows = (await self.db.execute(select(EInvoiceDocument).where(*filters).order_by(EInvoiceDocument.created_at.desc()).offset(offset).limit(limit))).scalars().all()
        return list(rows), total

    async def get_document(self, document_id: uuid.UUID, company_id: uuid.UUID):
        doc = (await self.db.execute(select(EInvoiceDocument).where(EInvoiceDocument.id == document_id, EInvoiceDocument.company_id == company_id))).scalar_one_or_none()
        if not doc:
            raise NotFoundException("E-invoice document not found")
        return doc

    async def execute(self, document_id: uuid.UUID, company_id: uuid.UUID, operation: str, extra: dict | None = None):
        doc = await self.get_document(document_id, company_id)
        cfg = await self._configuration(company_id)
        if not cfg.enabled:
            raise BadRequestException("E-invoice integration is disabled")
        if operation in {"generate_ewaybill", "cancel_ewaybill", "update_vehicle"} and not cfg.ewaybill_enabled:
            raise BadRequestException("E-way bill integration is disabled")
        payload = dict(doc.request_payload or {})
        if operation == "cancel_einvoice":
            payload = {"Irn": doc.irn, "CnlRsn": extra["reason"], "CnlRem": extra["remarks"]}
        elif operation == "generate_ewaybill" and doc.irn:
            payload = {"Irn": doc.irn, "Distance": doc.distance_km or 0, "TransId": doc.transporter_id or "", "TransMode": doc.transport_mode or "1", "VehNo": doc.vehicle_number or "", "VehType": doc.vehicle_type or "R"}
        elif operation == "generate_ewaybill":
            payload.update({"transDistance": str(doc.distance_km or 0), "transporterId": doc.transporter_id or "", "transMode": doc.transport_mode or "1", "vehicleNo": doc.vehicle_number or "", "vehicleType": doc.vehicle_type or "R"})
        elif operation == "cancel_ewaybill":
            payload = {"ewbNo": int(doc.ewaybill_number or 0), "cancelRsnCode": int(extra["reason"]), "cancelRmrk": extra["remarks"]}
        elif operation == "update_vehicle":
            payload = {"ewbNo": int(doc.ewaybill_number or 0), "vehicleNo": extra["vehicle_number"], "fromPlace": "", "fromState": 0, "reasonCode": extra["reason_code"], "reasonRem": extra["reason_remarks"], "transDocNo": "", "transDocDate": "", "transMode": extra["transport_mode"], "vehicleType": extra["vehicle_type"]}
        response = await self._request(cfg, doc, operation, payload)
        self._apply_response(doc, operation, response, extra)
        await self.db.commit()
        await self.db.refresh(doc)
        return doc

    async def _request(self, cfg, doc, operation, payload):
        if cfg.provider == "mygstcafe":
            direct_ewaybill = operation in {"cancel_ewaybill", "update_vehicle"} or (operation == "generate_ewaybill" and not doc.irn)
            base = "https://ewayapi.mygstcafe.com/managed/v1.03" if direct_ewaybill else self.MYGST_BASE[cfg.environment]
            path = {"generate_einvoice": "/Invoice", "cancel_einvoice": "/cancel", "generate_ewaybill": "/GenerateEwayBill" if direct_ewaybill else "/einvewb/ewaybill", "cancel_ewaybill": "/CancelEwayBill", "update_vehicle": "/UpdateVehicleNumber"}[operation]
        else:
            base = self.NIC_BASE[cfg.environment]
            path = {"generate_einvoice": "/eivital/v1.04/Invoice", "cancel_einvoice": "/eivital/v1.04/Cancel", "generate_ewaybill": "/eivital/v1.04/ewaybill" if doc.irn else "/ewayapi", "cancel_ewaybill": "/ewayapi/canewb", "update_vehicle": "/ewayapi/updateVehicle"}[operation]
        endpoint = base + path
        headers = {"Content-Type": "application/json"}
        if cfg.provider == "mygstcafe":
            headers.update({"GSTIN": cfg.asp_gstin or cfg.gstin or "", "Username": cfg.api_username or "", "Password": cfg.api_password or "", "CustomerId": cfg.customer_id or "", "APIId": cfg.api_id or "", "APISecret": cfg.api_secret or "", "Source": "API"})
        else:
            headers.update({"gstin": cfg.gstin or "", "user_name": cfg.api_username or "", "client_id": cfg.client_id or "", "client_secret": cfg.client_secret or "", "auth-token": cfg.auth_token or ""})
        started = time.perf_counter()
        log = EInvoiceApiLog(company_id=doc.company_id, document_id=doc.id, operation=operation, endpoint=endpoint, request_payload=payload)
        self.db.add(log)
        try:
            async with httpx.AsyncClient(timeout=45) as client:
                result = await client.post(endpoint, json=payload, headers=headers)
            body = result.json()
            log.http_status, log.response_payload = result.status_code, body
            log.success = result.is_success and str(body.get("status_cd", body.get("Status", "1"))) not in {"0", "Error"}
            if not log.success:
                error = body.get("error") or body.get("ErrorDetails") or body.get("message") or "Government API request failed"
                raise BadRequestException(str(error), error_code="EINVOICE_API_ERROR")
            return body.get("response_data") or body.get("data") or body.get("Data") or body
        except (httpx.HTTPError, ValueError) as exc:
            log.error_message = str(exc)
            doc.status, doc.error_message = "FAILED", str(exc)
            raise BadRequestException(f"E-invoice API unavailable: {exc}", error_code="EINVOICE_API_UNAVAILABLE") from exc
        finally:
            log.duration_ms = round((time.perf_counter() - started) * 1000)
            await self.db.flush()

    def _apply_response(self, doc, operation, response, extra):
        doc.response_payload, doc.error_message = response, None
        if operation == "generate_einvoice":
            doc.irn = str(response.get("Irn") or response.get("irn") or "") or None
            doc.acknowledgement_number = str(response.get("AckNo") or response.get("ack_no") or "") or None
            doc.signed_invoice = response.get("SignedInvoice")
            doc.signed_qr_code = response.get("SignedQRCode") or response.get("SignedQrCode")
            doc.status = "IRN_GENERATED"
        elif operation == "cancel_einvoice":
            doc.status, doc.cancelled_at = "IRN_CANCELLED", datetime.now(UTC)
            doc.cancellation_reason, doc.cancellation_remarks = extra["reason"], extra["remarks"]
        elif operation == "generate_ewaybill":
            doc.ewaybill_number = str(response.get("EwbNo") or response.get("ewayBillNo") or "") or None
            doc.status = "EWAYBILL_GENERATED"
        elif operation == "cancel_ewaybill":
            doc.status, doc.cancelled_at = "EWAYBILL_CANCELLED", datetime.now(UTC)
        elif operation == "update_vehicle":
            doc.vehicle_number, doc.status = extra["vehicle_number"].replace(" ", "").upper(), "EWAYBILL_GENERATED"

    async def _configuration(self, company_id, required=True):
        cfg = (await self.db.execute(select(EInvoiceConfiguration).where(EInvoiceConfiguration.company_id == company_id))).scalar_one_or_none()
        if required and not cfg:
            raise BadRequestException("Configure the E-Invoice API before continuing")
        return cfg

    @staticmethod
    def _safe_configuration(cfg):
        return ConfigurationResponse(id=cfg.id, company_id=cfg.company_id, enabled=cfg.enabled, ewaybill_enabled=cfg.ewaybill_enabled, auto_generate=cfg.auto_generate, environment=cfg.environment, provider=cfg.provider, gstin=cfg.gstin, asp_gstin=cfg.asp_gstin, api_username=cfg.api_username, has_api_password=bool(cfg.api_password), customer_id=cfg.customer_id, api_id=cfg.api_id, has_api_secret=bool(cfg.api_secret), client_id=cfg.client_id, has_client_secret=bool(cfg.client_secret), has_auth_token=bool(cfg.auth_token))

    async def _invoice_payload(self, invoice, company_id):
        company = (await self.db.execute(select(Company).where(Company.id == company_id))).scalar_one()
        customer = invoice.customer
        items = []
        for number, line in enumerate(invoice.lines, 1):
            rate, amount = Decimal(line.tax_rate), Decimal(line.amount)
            items.append({"SlNo": str(number), "PrdDesc": (line.description or line.service_type)[:300], "IsServc": "Y", "HsnCd": line.sac_code or "", "Qty": float(line.quantity), "Unit": "OTH", "UnitPrice": float(line.unit_price), "TotAmt": float(amount), "AssAmt": float(amount), "GstRt": float(rate), "CgstAmt": float(line.tax_amount / 2) if not invoice.is_interstate else 0, "SgstAmt": float(line.tax_amount / 2) if not invoice.is_interstate else 0, "IgstAmt": float(line.tax_amount) if invoice.is_interstate else 0, "TotItemVal": float(line.total_amount)})
        return {"Version": "1.1", "TranDtls": {"TaxSch": "GST", "SupTyp": "B2B", "RegRev": "N", "IgstOnIntra": "N"}, "DocDtls": {"Typ": "INV", "No": invoice.invoice_number[:16], "Dt": invoice.invoice_date.strftime("%d/%m/%Y")}, "SellerDtls": {"Gstin": company.gstin or "", "LglNm": company.legal_name or company.name, "Addr1": company.address or "", "Loc": "", "Pin": 0, "Stcd": company.state_code or (company.gstin or "00")[:2]}, "BuyerDtls": {"Gstin": customer.gstin if customer and customer.gstin else "URP", "LglNm": customer.legal_name or customer.name if customer else "", "Pos": (customer.gstin or "00")[:2] if customer else "00", "Addr1": customer.billing_address or "" if customer else "", "Loc": "", "Pin": 0, "Stcd": (customer.gstin or "00")[:2] if customer else "00"}, "ItemList": items, "ValDtls": {"AssVal": float(invoice.subtotal_amount), "CgstVal": float(invoice.cgst_amount), "SgstVal": float(invoice.sgst_amount), "IgstVal": float(invoice.igst_amount), "TotInvVal": float(invoice.total_amount)}}

    async def _dispatch_payload(self, order, company_id):
        company = (await self.db.execute(select(Company).where(Company.id == company_id))).scalar_one()
        customer, warehouse = order.customer, order.warehouse
        items = [{"productName": line.product.name[:100], "productDesc": line.product.name[:100], "hsnCode": int(line.product.hsn_code or 0), "quantity": float(line.dispatched_qty or line.ordered_qty), "qtyUnit": (line.uom.code or "OTH")[:3].upper(), "taxableAmount": 0, "cgstRate": 0, "sgstRate": 0, "igstRate": 0, "cessRate": 0} for line in order.lines]
        return {"supplyType": "O", "subSupplyType": "1", "docType": "CHL", "docNo": order.dispatch_number[:16], "docDate": order.dispatch_date.strftime("%d/%m/%Y"), "fromGstin": company.gstin or "", "fromTrdName": company.name, "fromAddr1": warehouse.address_line1 or company.address or "", "fromPlace": warehouse.city or "", "fromPincode": int(warehouse.postal_code or 999999), "fromStateCode": int(company.state_code or (company.gstin or "00")[:2]), "actFromStateCode": int(company.state_code or (company.gstin or "00")[:2]), "toGstin": customer.gstin if customer and customer.gstin else "URP", "toTrdName": customer.name if customer else "", "toAddr1": customer.shipping_address or customer.billing_address or "" if customer else "", "toPlace": "", "toPincode": 999999, "toStateCode": int((customer.gstin or "00")[:2]) if customer else 0, "actToStateCode": int((customer.gstin or "00")[:2]) if customer else 0, "itemList": items, "totInvValue": 0, "transMode": "1", "transDistance": 0, "vehicleNo": (order.vehicle_number or "").replace(" ", "").upper(), "vehicleType": "R"}

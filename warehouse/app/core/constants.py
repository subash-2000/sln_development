from enum import Enum


class Environment(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    TESTING = "testing"
    PRODUCTION = "production"


class EntityStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    ARCHIVED = "ARCHIVED"


class ProductPackageTrackingType(str, Enum):
    """Packaging identifier on product master (dropdown: pallet or cotton box)."""

    PALLET_NUMBER = "PALLET_NUMBER"
    COTTON_BOX = "COTTON_BOX"


class UserStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    SUSPENDED = "SUSPENDED"


class AuditAction(str, Enum):
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    APPROVE = "APPROVE"
    POST = "POST"
    CANCEL = "CANCEL"
    REJECT = "REJECT"


class BranchType(str, Enum):
    MAIN = "MAIN"
    REGIONAL = "REGIONAL"
    WAREHOUSE = "WAREHOUSE"
    VIRTUAL = "VIRTUAL"


class TokenType(str, Enum):
    ACCESS = "access"
    REFRESH = "refresh"


class WarehouseType(str, Enum):
    OWNED = "OWNED"
    LEASED = "LEASED"
    BONDED = "BONDED"
    THIRD_PARTY = "THIRD_PARTY"
    VENDOR = "VENDOR"
    VIRTUAL = "VIRTUAL"


class LocationType(str, Enum):
    INTERNAL = "INTERNAL"
    RECEIVING = "RECEIVING"
    DISPATCH = "DISPATCH"
    TRANSIT = "TRANSIT"
    SUPPLIER = "SUPPLIER"
    CUSTOMER = "CUSTOMER"
    JOB_WORK = "JOB_WORK"
    SCRAP = "SCRAP"
    QUARANTINE = "QUARANTINE"
    RETURN = "RETURN"
    VIEW = "VIEW"


class StorageType(str, Enum):
    FLOOR = "FLOOR"
    RACK = "RACK"
    SHELF = "SHELF"
    BIN = "BIN"
    PALLET_BAY = "PALLET_BAY"
    COLD_ROOM = "COLD_ROOM"
    VIRTUAL = "VIRTUAL"


class TransactionType(str, Enum):
    RECEIPT = "RECEIPT"
    DELIVERY = "DELIVERY"
    TRANSFER = "TRANSFER"
    ADJUSTMENT = "ADJUSTMENT"
    RESERVATION = "RESERVATION"
    RESERVATION_RELEASE = "RESERVATION_RELEASE"
    SCRAP = "SCRAP"
    QUARANTINE_HOLD = "QUARANTINE_HOLD"
    QUARANTINE_RELEASE = "QUARANTINE_RELEASE"


class TransactionStatus(str, Enum):
    DRAFT = "DRAFT"
    CONFIRMED = "CONFIRMED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class MoveState(str, Enum):
    DRAFT = "DRAFT"
    ASSIGNED = "ASSIGNED"
    DONE = "DONE"
    CANCELLED = "CANCELLED"


class ConsignmentStatus(str, Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    EXPIRED = "EXPIRED"
    TERMINATED = "TERMINATED"


class AgreementBillingCycle(str, Enum):
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"
    QUARTERLY = "QUARTERLY"


class TitleTransferStatus(str, Enum):
    DRAFT = "DRAFT"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class JobWorkOrderStatus(str, Enum):
    DRAFT = "DRAFT"
    MATERIAL_ISSUED = "MATERIAL_ISSUED"
    IN_PROCESS = "IN_PROCESS"
    GOODS_RECEIVED = "GOODS_RECEIVED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class JobWorkOrderType(str, Enum):
    PROCESSING = "PROCESSING"
    CONVERSION = "CONVERSION"
    ASSEMBLY = "ASSEMBLY"
    FABRICATION = "FABRICATION"
    REPAIR = "REPAIR"


class DispatchStatus(str, Enum):
    DRAFT = "DRAFT"
    PACKED = "PACKED"
    DISPATCHED = "DISPATCHED"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"


class DispatchOrderType(str, Enum):
    CUSTOMER_SALE = "CUSTOMER_SALE"
    BRANCH_TRANSFER = "BRANCH_TRANSFER"
    VENDOR_RETURN = "VENDOR_RETURN"
    JOB_WORK_ISSUE = "JOB_WORK_ISSUE"


class CarrierType(str, Enum):
    SELF = "SELF"
    CUSTOMER_PICKUP = "CUSTOMER_PICKUP"
    TRANSPORTER = "TRANSPORTER"
    COURIER = "COURIER"


class GatePassType(str, Enum):
    OUTWARD = "OUTWARD"
    INWARD = "INWARD"
    RETURNABLE = "RETURNABLE"
    NON_RETURNABLE = "NON_RETURNABLE"


class GatePassStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    IN_TRANSIT = "IN_TRANSIT"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class BillingPeriodStatus(str, Enum):
    OPEN = "OPEN"
    CALCULATING = "CALCULATING"
    CALCULATED = "CALCULATED"
    INVOICED = "INVOICED"
    CLOSED = "CLOSED"


class BillingDocumentStatus(str, Enum):
    DRAFT = "DRAFT"
    CONFIRMED = "CONFIRMED"
    INVOICED = "INVOICED"
    CANCELLED = "CANCELLED"


class ServiceType(str, Enum):
    STORAGE = "STORAGE"
    HANDLING_IN = "HANDLING_IN"
    HANDLING_OUT = "HANDLING_OUT"
    VALUE_ADDED_SERVICE = "VALUE_ADDED_SERVICE"
    INSURANCE = "INSURANCE"
    OTHER = "OTHER"


class CalculationBasis(str, Enum):
    PER_BAG_PER_DAY = "PER_BAG_PER_DAY"
    PER_MT_PER_DAY = "PER_MT_PER_DAY"
    PER_SQFT_PER_MONTH = "PER_SQFT_PER_MONTH"
    PER_TRANSACTION = "PER_TRANSACTION"
    FIXED = "FIXED"


class InvoiceStatus(str, Enum):
    DRAFT = "DRAFT"
    POSTED = "POSTED"
    PARTIALLY_PAID = "PARTIALLY_PAID"
    PAID = "PAID"
    CANCELLED = "CANCELLED"


class PaymentMode(str, Enum):
    BANK_TRANSFER = "BANK_TRANSFER"
    CHEQUE = "CHEQUE"
    UPI = "UPI"
    CASH = "CASH"
    CREDIT_NOTE = "CREDIT_NOTE"
    OTHER = "OTHER"


class ReturnType(str, Enum):
    CUSTOMER_RETURN = "CUSTOMER_RETURN"
    VENDOR_RETURN = "VENDOR_RETURN"


class ReturnStatus(str, Enum):
    DRAFT = "DRAFT"
    RECEIVED = "RECEIVED"
    INSPECTED = "INSPECTED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class ReturnDisposition(str, Enum):
    RESTOCK = "RESTOCK"
    QUARANTINE = "QUARANTINE"
    SCRAP = "SCRAP"
    RETURN_TO_VENDOR = "RETURN_TO_VENDOR"


class StockTakeType(str, Enum):
    FULL_COUNT = "FULL_COUNT"
    CYCLE_COUNT = "CYCLE_COUNT"
    SPOT_CHECK = "SPOT_CHECK"


class StockTakeStatus(str, Enum):
    DRAFT = "DRAFT"
    FROZEN = "FROZEN"
    COUNTING = "COUNTING"
    RECOUNT = "RECOUNT"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    POSTED = "POSTED"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


class CountVarianceAction(str, Enum):
    ACCEPT = "ACCEPT"
    RECOUNT = "RECOUNT"
    OVERRIDE = "OVERRIDE"


class InvoiceWorkflow(str, Enum):
    """Supplier invoice responsibility for rings / SKF warehouse operations."""

    STANDARD = "STANDARD"
    JOB_WORK = "JOB_WORK"
    DIRECT_INVOICE = "DIRECT_INVOICE"
    BOTH = "BOTH"


class RingsDocumentType(str, Enum):
    INWARD = "INWARD"
    PICK = "PICK"
    OUTWARD = "OUTWARD"


class RingsDocumentStatus(str, Enum):
    DRAFT = "DRAFT"
    POSTED = "POSTED"
    CANCELLED = "CANCELLED"

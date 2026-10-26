import uuid
from datetime import UTC, datetime
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import BaseEntity

class ImportBatch(BaseEntity):
    """Tracking document for a bulk data import session."""
    __tablename__ = "import_batches"

    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True)
    import_type = Column(String(50), nullable=False, index=True)  # "PRODUCT", "VENDOR", "OPENING_STOCK"
    status = Column(String(50), default="PENDING", nullable=False) # "PENDING", "PROCESSING", "COMPLETED", "FAILED"
    column_mapping = Column(JSON, nullable=True)
    
    filename = Column(String(255), nullable=True)
    total_records = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)
    
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(String, nullable=True)
    
    company = relationship("Company", lazy="selectin")
    logs = relationship("ImportLog", back_populates="batch", cascade="all, delete-orphan", lazy="selectin")

class ImportLog(BaseEntity):
    """Detailed logs for individual row failures during import."""
    __tablename__ = "import_logs"

    batch_id = Column(UUID(as_uuid=True), ForeignKey("import_batches.id"), nullable=False, index=True)
    row_number = Column(Integer, nullable=True)
    record_identifier = Column(String(255), nullable=True) # e.g. SKU or Vendor Code
    status = Column(String(20), nullable=False) # "SUCCESS", "ERROR"
    error_details = Column(JSON, nullable=True)
    
    batch = relationship("ImportBatch", back_populates="logs")

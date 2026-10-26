import uuid

from sqlalchemy import BigInteger, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseEntity


class Sequence(BaseEntity):
    """Centralized concurrency-safe document sequence numbering generator."""

    __tablename__ = "sequences"
    __table_args__ = (
        UniqueConstraint(
            "document_type",
            "company_id",
            "branch_id",
            "year",
            "month",
            name="uq_sequence_document_scope",
        ),
    )

    document_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    prefix: Mapped[str] = mapped_column(
        String(20),
        default="",
        nullable=False,
    )

    suffix: Mapped[str] = mapped_column(
        String(20),
        default="",
        nullable=False,
    )

    current_value: Mapped[int] = mapped_column(
        BigInteger,
        default=0,
        nullable=False,
    )

    padding: Mapped[int] = mapped_column(
        Integer,
        default=5,
        nullable=False,
    )

    year: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    month: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    company_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    branch_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("branches.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

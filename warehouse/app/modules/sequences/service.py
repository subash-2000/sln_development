import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import get_audit_names, log_audit
from app.core.exceptions import ConflictException, NotFoundException
from app.models.sequence import Sequence
from app.modules.sequences.repository import SequenceRepository
from app.modules.sequences.schemas import (
    SequenceCreateRequest,
    SequenceResponse,
    SequenceUpdateRequest,
)


class SequenceAdminService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = SequenceRepository(db)

    async def list_sequences(self, company_id: uuid.UUID | None = None) -> list[SequenceResponse]:
        sequences = await self.repo.list_all(company_id=company_id)
        return [self._to_response(s) for s in sequences]

    async def get_sequence(self, seq_id: uuid.UUID) -> SequenceResponse:
        seq = await self.repo.get_by_id(seq_id)
        if not seq:
            raise NotFoundException(
                f"Sequence with ID '{seq_id}' not found", error_code="SEQUENCE_NOT_FOUND"
            )
        created_by_name, updated_by_name = await get_audit_names(
            self.db, seq.created_by_id, seq.updated_by_id
        )
        return self._to_response(seq, created_by=created_by_name, updated_by=updated_by_name)

    async def create_sequence(self, req: SequenceCreateRequest) -> SequenceResponse:
        clean_doc_type = req.document_type.strip().upper()
        existing = await self.repo.get_by_scope(
            clean_doc_type, req.company_id, req.branch_id, req.year, req.month
        )
        if existing:
            raise ConflictException(
                f"Sequence for document '{clean_doc_type}' already configured for this scope",
                error_code="SEQUENCE_SCOPE_EXISTS",
            )

        seq = Sequence(
            document_type=clean_doc_type,
            prefix=req.prefix.strip(),
            suffix=req.suffix.strip(),
            current_value=req.current_value,
            padding=req.padding,
            year=req.year,
            month=req.month,
            company_id=req.company_id,
            branch_id=req.branch_id,
            is_active=True,
        )
        created = await self.repo.create(seq)

        await log_audit(
            db=self.db,
            action="CREATE",
            module="sequences",
            entity_name="Sequence",
            entity_id=str(created.id),
            company_id=req.company_id,
            branch_id=req.branch_id,
            new_values={
                "document_type": clean_doc_type,
                "prefix": req.prefix,
                "padding": req.padding,
            },
        )
        await self.db.commit()

        return self._to_response(created)

    async def update_sequence(
        self, seq_id: uuid.UUID, req: SequenceUpdateRequest
    ) -> SequenceResponse:
        seq = await self.repo.get_by_id(seq_id)
        if not seq:
            raise NotFoundException(
                f"Sequence with ID '{seq_id}' not found", error_code="SEQUENCE_NOT_FOUND"
            )

        old_values = {
            "prefix": seq.prefix,
            "suffix": seq.suffix,
            "padding": seq.padding,
            "is_active": seq.is_active,
        }

        if req.prefix is not None:
            seq.prefix = req.prefix.strip()
        if req.suffix is not None:
            seq.suffix = req.suffix.strip()
        if req.padding is not None:
            seq.padding = req.padding
        if req.is_active is not None:
            seq.is_active = req.is_active

        await log_audit(
            db=self.db,
            action="UPDATE",
            module="sequences",
            entity_name="Sequence",
            entity_id=str(seq.id),
            company_id=seq.company_id,
            branch_id=seq.branch_id,
            old_values=old_values,
            new_values={
                "prefix": seq.prefix,
                "suffix": seq.suffix,
                "padding": seq.padding,
                "is_active": seq.is_active,
            },
        )
        await self.db.commit()

        return self._to_response(seq)

    def _to_response(
        self,
        seq: Sequence,
        created_by: str | None = None,
        updated_by: str | None = None,
    ) -> SequenceResponse:
        return SequenceResponse(
            id=seq.id,
            document_type=seq.document_type,
            prefix=seq.prefix,
            suffix=seq.suffix,
            current_value=seq.current_value,
            padding=seq.padding,
            year=seq.year,
            month=seq.month,
            company_id=seq.company_id,
            branch_id=seq.branch_id,
            is_active=seq.is_active,
            created_at=seq.created_at,
            updated_at=seq.updated_at,
            created_by_id=seq.created_by_id,
            updated_by_id=seq.updated_by_id,
            created_by=created_by,
            updated_by=updated_by,
        )

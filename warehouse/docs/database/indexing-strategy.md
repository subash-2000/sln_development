# Database Indexing Strategy

## 1. Indexing Principles

1. **Foreign Key Indexing**: All foreign key columns (`company_id`, `branch_id`, `user_id`, `role_id`, `permission_id`) are indexed to eliminate table scans during joins and cascade actions.
2. **Business Lookup Uniqueness**: Unique business identifiers (`companies.code`, `branches.code` within company, `users.username`, `users.email`, `roles.code`, `permissions.code`) are indexed as unique constraints.
3. **Audit Trail Indexes**:
   - `ix_audit_logs_company_timestamp`: B-tree composite index on `(company_id, timestamp DESC)` for fast tenant audit history filtering.
   - `ix_audit_logs_module_entity`: B-tree composite index on `(module, entity_name, entity_id)` for quick entity mutation tracing.
   - `ix_audit_logs_request_id`: Index on `request_id` to correlate backend operations with incoming client request identifiers.
4. **Sequence Generator Indexing**:
   - `uq_sequence_document_scope`: Unique composite constraint on `(document_type, company_id, branch_id, year, month)` allowing row-level locking via `SELECT ... FOR UPDATE`.

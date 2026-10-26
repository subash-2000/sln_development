# Business Rules Clarification Register

This register documents requirements, ambiguities, impacts, and confirmation status per Section 61 and 74.

| Item | Requirement Area | Status | Clarification / Confirmed Rule |
| :--- | :--- | :--- | :--- |
| **BR-01** | Multi-Company Isolation | **CONFIRMED** | Never trust client headers or body company IDs. Authorization is server-side via `UserCompanyBranch` records or `is_superuser`. |
| **BR-02** | Branch Scoping | **CONFIRMED** | Branch code uniqueness is strictly scoped within `company_id`. Company A can have Branch X and Company B can have Branch X. |
| **BR-03** | Password Storage | **CONFIRMED** | Argon2id with 64 MB memory cost is enforced. Plaintext passwords strictly prohibited. |
| **BR-04** | Sequence Generation | **CONFIRMED** | Row-level locking via `SELECT ... FOR UPDATE` ensures duplicate-free sequence counters. |
| **BR-05** | QR Code Functionality | **CLARIFICATION REQUIRED** | Retained subject to business workflow confirmation before module implementation. |
| **BR-06** | E-Sugam Integration | **CONFIRMED** | Maintained as an informational reference field initially; no direct external API integration until approved. |

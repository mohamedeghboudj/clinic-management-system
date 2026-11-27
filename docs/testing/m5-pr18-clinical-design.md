# Independent M5 design assessment — Clinical Care Design (PR / Branch docs/w1-clinical-design)

**Date:** 2 November 2026. **Tester:** @ayyoubbouchama (M5).
**Author:** @MohamedAmine-dash (M4). **Reviewers:** @mohamedeghboudj (M1), @ahmed-ammiche (M2).
**Submitted design scope:** `docs/design/clinical.md` against the Week 1 member guide.

**Outcome: design changes required before final acceptance.** This is a manual contract
and failure-scenario assessment. Deferred clinical models (`MedicalRecord`, `Allergy`, `TreatmentPlan`, `AttachmentMetadata`, `ProcedureType`, `Surgery`, `LabOrder`, etc.) and future use cases (`FinalizeConsultation`, `IssuePrescription`) are specified as design-only documentation; there are no executable unit tests proving database or cloud storage behavior today.

## Coverage of the assigned design scope

The document supplies fields/signatures, relationships, states or immutability,
errors, transaction/security intent, and examples for all deferred clinical entries and use cases.
The named future issue identifiers (`#CLIN-01` through `#CLIN-07`) provide clear backlog tracking.

| Entry | Acceptance scenarios to retain for future implementation |
| --- | --- |
| MedicalRecord | Paginated query projection for clinical history entries without loading full patient lifetime history into memory. |
| Allergy | Active, resolved, and terminal `ENTERED_IN_ERROR` states preserving audit trail over physical deletion. |
| TreatmentPlan | Active status tracking with structured goals and start/end date validation (`ended_on >= started_on`). |
| AttachmentMetadata | Cryptographic SHA-256 tamper checks, 50MB file size limits, virus scan status quarantine (`PENDING` -> `CLEAN`/`INFECTED`), and cloud object storage keys. |
| ProcedureType | Standardized surgical/minor clinical procedures linked directly to `ServiceCatalogItem` for billing integration. |
| Surgery & Team | Multi-disciplinary team roles (`LEAD_SURGEON`, etc.) and unified M3 doctor/room/equipment resource reservations. |
| Lab Orders & Results | Requisitions, sample collection, numeric/textual results with reference ranges, and separate clinician validation. |

The use cases `FinalizeConsultation` and `IssuePrescription` correctly enforce transaction boundaries, version checks, and atomic outbox event staging inside a Unit of Work.

## Required design considerations & future integration items

Before design acceptance, specify these future integration cases for Sprint 2/3:
1. **Concurrency & Resource Locking in Surgery Scheduling:** When claiming M3 doctor, room, and equipment reservations alongside surgical state transitions, ensure deadlock prevention protocols across distributed service boundaries.
2. **Cloud Storage Presigned URL Expiry:** Specify maximum validity timeouts for presigned S3/Supabase storage download URLs generated for `AttachmentMetadata` to prevent unauthorized persistent access.
3. **Lab Result Amendment Traceability:** Ensure that amended lab results preserve original raw values and validation signatures through immutable audit trails matching `ClinicalAmendment`.
4. **Tenant Isolation Verification:** Confirm that all clinical queries and pagination filters enforce strict `clinic_id` scoping at the SQL persistence layer.

## Other completion and handoff actions

- Maintain clean separation between clinical narrative notes and billing/history projections (`ClinicalEntrySummary`).
- Keep deferred models as documentation; do not create placeholder Python classes in Week 1.
- M4 updates the specification and issue links; M5 reassesses the scenarios upon Sprint 2 implementation.
